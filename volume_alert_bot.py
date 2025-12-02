import asyncio
import logging
import os
import sys
import time
from datetime import datetime
from dotenv import load_dotenv

from config import VolumeAlertConfig
from binance_fetcher import BinanceDataFetcher
from volume_detector import VolumeDetector
from telegram_client import TelegramClient

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(VolumeAlertConfig.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class VolumeAlertBot:
    """Main volume alert bot orchestrator"""
    
    def __init__(self):
        """Initialize bot components"""
        logger.info("Initializing Volume Alert Bot...")
        
        # Check environment
        self.telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.telegram_topic_id = os.getenv("TELEGRAM_TOPIC_ID")  # Optional topic ID
        
        if not self.telegram_token or not self.telegram_chat_id:
            logger.error("Missing Telegram credentials in .env file")
            logger.error("Please set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")
            sys.exit(1)
        
        # Initialize components
        self.fetcher = BinanceDataFetcher()
        self.detector = VolumeDetector()
        self.telegram = TelegramClient(
            self.telegram_token,
            self.telegram_chat_id,
            topic_id=int(self.telegram_topic_id) if self.telegram_topic_id else None
        )
        
        # Configuration
        self.symbols = VolumeAlertConfig.SYMBOLS
        self.timeframes = VolumeAlertConfig.TIMEFRAMES
        self.check_interval = VolumeAlertConfig.CHECK_INTERVAL
        self.max_alerts_per_symbol = VolumeAlertConfig.MAX_ALERTS_PER_SYMBOL
        
        # Alert tracking per symbol per timeframe per day
        # Format: {
        #   "BTCUSDT": {
        #     "1h": {
        #       "count": 2, 
        #       "last_reset": "2025-11-30",
        #       "last_alerted_open_time": 1700000400,
        #       "last_alert_timestamp": 1700000000,  # Unix timestamp of last alert
        #       "cooldown_seconds": 10800  # 3 hours for 1h, 86400 for 24h
        #     },
        #     "24h": {
        #       "count": 1, 
        #       "last_reset": "2025-11-30",
        #       "last_alerted_open_time": 1700000400,
        #       "last_alert_timestamp": 1700000000,
        #       "cooldown_seconds": 86400  # 1 day for 24h
        #     }
        #   }
        # }
        self.alert_tracking = {
            symbol: {
                timeframe: {
                    "count": 0,
                    "last_reset": self._get_period_key(timeframe),
                    "last_alerted_open_time": None,  # BUG FIX #1: Track open_time to prevent same-candle duplicates
                    "last_alert_timestamp": 0,  # IMPROVEMENT: Track when alert was sent for cooldown
                    "cooldown_seconds": 10800 if timeframe == "1h" else 86400  # 3h for 1h, 24h for 24h
                }
                for timeframe in self.timeframes.keys()
            }
            for symbol in self.symbols
        }
        
        # Load persisted alert tracking
        self._load_alert_tracking()
        
        # Alert queue system: Track last alert timestamp to enforce 10-min gap
        self.last_alert_timestamp = 0
        self.alert_queue_gap = VolumeAlertConfig.ALERT_QUEUE_GAP_SECONDS  # 600 seconds (10 minutes)
        
        # Pending alerts queue: Store alerts that should be sent after gap period
        # Format: [(timestamp, alert_dict), ...]
        self.pending_alerts = []
        
        # Command handling
        self.last_update_id = 0
        self.bot_running = True
        self.owner_chat_id = int(os.getenv("TELEGRAM_OWNER_CHAT_ID", "395803228"))
        
        # Telegram API retry tracking
        self.telegram_retry_count = 0
        self.max_consecutive_retries = 5
        
        # Create data directory
        os.makedirs(VolumeAlertConfig.DATA_DIR, exist_ok=True)
        
        logger.info(f"Bot initialized. Monitoring {self.symbols} on {list(self.timeframes.keys())}")
    
    async def run(self):
        """Main monitoring loop with command handling"""
        logger.info("Starting volume alert monitoring...")
        
        # DON'T clear the queue - it causes connection conflicts
        # Just start fresh with no offset
        self.last_update_id = -1  # Start from -1 so first offset will be 0
        self.bot_running = True
        
        # Run monitoring and command listening concurrently
        try:
            await asyncio.gather(
                self.monitoring_loop(),
                self.command_listener_loop(),
                self.alert_queue_processor(),
                return_exceptions=True
            )
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
            raise
    
    async def _clear_telegram_queue(self):
        """Clear old messages from Telegram queue on startup
        
        This discards any updates that Telegram has cached, so we only process
        new messages from this point forward.
        """
        import requests
        try:
            await asyncio.sleep(0.5)  # Small delay to ensure initialization
            url = f"https://api.telegram.org/bot{self.telegram_token}/getUpdates"
            
            # Get current updates to see what's in the queue (NO timeout parameter - no long polling)
            response = requests.get(url, timeout=3)
            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    updates = data.get('result', [])
                    if updates:
                        # Log how many we're discarding
                        logger.info(f"🧹 Found {len(updates)} pending messages in queue, discarding them")
                    else:
                        logger.info("🧹 Queue is clean, no pending messages")
            
            logger.info("🧹 Queue cleared, ready for new messages")
            
        except Exception as e:
            logger.warning(f"Queue clearing: {e}")
    
    async def monitoring_loop(self):
        """Volume monitoring loop"""
        logger.info("📊 Monitoring loop started")
        while self.bot_running:
            try:
                logger.debug("Checking all volumes...")
                await self.check_all_volumes()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(5)
    
    async def command_listener_loop(self):
        """Listen for /start and /stop commands with improved error handling"""
        consecutive_errors = 0
        max_consecutive_errors = 10
        
        while True:
            try:
                updates = await self.fetch_updates()
                
                if updates:
                    consecutive_errors = 0  # Reset on success
                    for update in updates:
                        try:
                            await self.handle_update(update)
                            self.last_update_id = update.get('update_id', self.last_update_id)
                        except Exception as e:
                            logger.error(f"Error handling update: {e}")
                
                await asyncio.sleep(1)
                
            except Exception as e:
                consecutive_errors += 1
                wait_time = min(2 ** consecutive_errors, 30)  # Exponential backoff, max 30s
                
                if consecutive_errors <= max_consecutive_errors:
                    logger.warning(f"Command listener error: {e} (attempt {consecutive_errors}/{max_consecutive_errors})")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Command listener: Too many consecutive errors. Pausing for {wait_time}s")
                    consecutive_errors = 0  # Reset counter after long pause
                    await asyncio.sleep(wait_time)
    
    async def alert_queue_processor(self):
        """Process pending alerts from queue
        
        Enforces 10-minute gap between alerts:
        - If last alert was sent < 10 min ago, queue the new alert
        - Check queue every 10 seconds for alerts ready to send
        """
        while True:
            try:
                current_time = time.time()
                
                # Check if any pending alerts are ready to send (gap elapsed)
                if self.pending_alerts:
                    # BUG FIX #2: Updated to handle new queue format with open_time
                    alert_timestamp, alert, symbol, timeframe, max_alerts, open_time = self.pending_alerts[0]
                    time_since_last = current_time - self.last_alert_timestamp
                    
                    # If 10 minutes have passed since last alert, send the next one
                    if time_since_last >= self.alert_queue_gap:
                        self.pending_alerts.pop(0)  # Remove from queue
                        
                        # BUG FIX #5: Check if count strictly exceeds max (not equals)
                        # This allows count to equal max (e.g., 3 == 3), fixing the off-by-one error
                        if self.alert_tracking[symbol][timeframe]["count"] > max_alerts:
                            logger.warning(f"⚠️ Alert for {symbol} {timeframe} skipped - max alerts reached")
                            continue
                        
                        # Format and send the alert
                        direction_emoji = "📈" if alert['volume_change_pct'] > 0 else "📉"
                        direction_text = "INCREASE" if alert['volume_change_pct'] > 0 else "DECREASE"
                        
                        message = (
                            f"🚨 {alert['symbol']} VOLUME ALERT {direction_emoji}\n\n"
                            f"⏱️ Timeframe: {alert['timeframe']}\n"
                            f"💹 Current Price: ${alert['current_price']:,.2f}\n"
                            f"📊 Volume Change: {alert['volume_change_pct']:+.2f}%\n\n"
                            f"⚠️ Volume Spike Detected"
                        )
                        
                        await self.telegram.send_alert_message(message)
                        self.last_alert_timestamp = current_time
                        
                        # BUG FIX #5: Update tracking - count already incremented when queued
                        # Also update last_alert_timestamp for cooldown enforcement
                        self.alert_tracking[symbol][timeframe]["last_alerted_open_time"] = open_time
                        self.alert_tracking[symbol][timeframe]["last_alert_timestamp"] = current_time
                        self._save_alert_tracking()
                        
                        logger.info(f"📤 Queued alert sent for {symbol} {timeframe}: {alert['volume_change_pct']:+.2f}% "
                                   f"({self.alert_tracking[symbol][timeframe]['count']}/{max_alerts}, queue size: {len(self.pending_alerts)})")
                
                await asyncio.sleep(10)  # Check queue every 10 seconds
            except Exception as e:
                logger.error(f"Error in alert queue processor: {e}")
                await asyncio.sleep(10)
    
    async def fetch_updates(self):
        """Fetch updates from Telegram API with improved retry logic"""
        import requests
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/getUpdates"
            
            # Simple polling without extra parameters that might cause issues
            response = requests.get(
                url,
                params={
                    "offset": self.last_update_id + 1
                },
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    self.telegram_retry_count = 0  # Reset on success
                    updates = data.get('result', [])
                    
                    # Handle case where offset is invalid (409 scenario)
                    if not updates and self.last_update_id > 0:
                        # Offset was too high, reset to get latest
                        logger.warning(f"Offset {self.last_update_id + 1} seems invalid, resetting to get latest updates")
                        self.last_update_id = -1
                    
                    return updates
            elif response.status_code == 409:
                # 409 Conflict: Another bot instance is running with same token
                # Reset offset and wait
                self.telegram_retry_count += 1
                self.last_update_id = -1  # Reset to fresh state
                wait_time = min(5 * self.telegram_retry_count, 30)
                logger.warning(f"Telegram API 409 Conflict (attempt {self.telegram_retry_count}) - resetting offset, waiting {wait_time}s")
                await asyncio.sleep(wait_time)
                return []
            
            logger.warning(f"Telegram API returned status {response.status_code}")
            return []
            
        except requests.exceptions.Timeout:
            self.telegram_retry_count += 1
            wait_time = min(2 ** self.telegram_retry_count, 30)
            
            if self.telegram_retry_count <= self.max_consecutive_retries:
                logger.warning(f"Telegram API timeout (attempt {self.telegram_retry_count}/{self.max_consecutive_retries}), "
                              f"will retry in {wait_time}s")
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"Telegram API: Max retries exceeded. Resetting offset.")
                self.telegram_retry_count = 0
                self.last_update_id = -1
            return []
                
        except Exception as e:
            logger.error(f"Error fetching updates: {e}")
            return []
    
    async def handle_update(self, update):
        """Handle incoming Telegram update"""
        try:
            update_id = update.get('update_id')
            self.last_update_id = max(self.last_update_id, update_id)
            
            if 'message' not in update:
                return
            
            message = update['message']
            chat_id = message['chat']['id']
            chat_type = message['chat'].get('type', 'unknown')
            user_id = message['from'].get('id')
            text = message.get('text', '')
            user_name = message['from'].get('first_name', 'User')
            
            # Log all messages to help identify chat IDs
            logger.info(f"📨 Message from {user_name} (ID: {user_id}) in chat {chat_id} (type: {chat_type}): {text[:50]}")
            
            # Owner's Chat ID
            owner_chat_id = int(os.getenv('TELEGRAM_OWNER_CHAT_ID', '395803228'))
            is_owner = (user_id == owner_chat_id)
            
            logger.debug(f"[OWNER CHECK] user_id={user_id}, owner_chat_id={owner_chat_id}, is_owner={is_owner}")
            
            # Handle private messages (DMs) - Send welcome message
            if chat_type == 'private':
                from command_handler import CommandHandler
                welcome_msg = CommandHandler.get_welcome_message()
                await self.send_message(chat_id, welcome_msg)
                logger.info(f"✅ Sent welcome message to user {user_id} ({user_name})")
                return
            
            # Handle group commands only
            if chat_type in ['group', 'supergroup']:
                # /start @Mudrex_Volume_bot - activate bot
                if text.startswith('/start') and '@Mudrex_Volume_bot' in text:
                    if is_owner:
                        self.bot_running = True
                        reply = f"✅ Bot activated by {user_name}\n\n📊 Volume alerts are now ACTIVE\n⏱️ Checking every 5 minutes"
                        await self.send_message(chat_id, reply)
                        logger.info(f"✅ Bot ACTIVATED by owner {user_id} in group {chat_id}")
                    else:
                        reply = "🚫 Only the bot owner can activate the bot."
                        await self.send_message(chat_id, reply)
                        logger.warning(f"⚠️ Unauthorized /start by user {user_id}")
                
                # /stop @Mudrex_Volume_bot - deactivate bot
                elif text.startswith('/stop') and '@Mudrex_Volume_bot' in text:
                    if is_owner:
                        self.bot_running = False
                        reply = f"🛑 Bot stopped by {user_name}\n\n⏸️ Volume alerts are now PAUSED"
                        await self.send_message(chat_id, reply)
                        logger.info(f"🛑 Bot STOPPED by owner {user_id} in group {chat_id}")
                    else:
                        reply = "🚫 Only the bot owner can stop the bot."
                        await self.send_message(chat_id, reply)
                        logger.warning(f"⚠️ Unauthorized /stop by user {user_id}")
                
                # /status @Mudrex_Volume_bot - show bot status
                elif text.startswith('/status') and '@Mudrex_Volume_bot' in text:
                    from command_handler import CommandHandler
                    await CommandHandler.handle_status(self, chat_id, self.bot_running)
                    logger.info(f"✅ Status sent to {user_id} in group {chat_id}")
        
        except Exception as e:
            logger.error(f"Error handling update: {e}")
    
    async def send_message(self, chat_id, text):
        """Send message to Telegram"""
        import requests
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            response = requests.post(
                url,
                json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
                timeout=10
            )
            if response.status_code == 200:
                logger.info(f"✅ Message sent to {chat_id}")
                return True
            else:
                logger.error(f"Failed to send message: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False
    
    async def check_all_volumes(self):
        """Check volume for all symbols and timeframes INDEPENDENTLY
        
        Strategy:
        1. Check each timeframe independently (not dual requirement)
        2. 1h: ±50% threshold, max 3 alerts per day per asset
        3. 24h: ±75% threshold, max 1 alert per day per asset
        4. Once alert triggers for a period, lock until next period
        """
        # Only run if bot is active
        if not self.bot_running:
            logger.debug("⏸️ Bot is paused, skipping volume check")
            return
        
        logger.debug(f"🔍 Checking volumes for {len(self.symbols)} symbols...")
        
        # Reset daily counts if needed (check period boundaries)
        self._reset_daily_counts()
        
        tasks = []
        
        # Check each symbol on each timeframe INDEPENDENTLY
        for symbol in self.symbols:
            for timeframe in self.timeframes.keys():
                tasks.append(self.check_symbol_timeframe(symbol, timeframe))
        
        # Run all checks concurrently
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    def _get_period_key(self, timeframe: str) -> str:
        """Get the current period key for a timeframe
        
        BUG FIX #4: Changed both 1h and 24h to reset daily (YYYY-MM-DD)
        This ensures max 3 alerts per DAY for 1h timeframe, not per hour
        Previous behavior allowed 72 alerts/day (3 per hour), now limited to 3/day
        """
        now = datetime.now()
        # Both 1h and 24h now reset daily at UTC midnight for consistency
        return now.strftime("%Y-%m-%d")
    
    def _reset_daily_counts(self):
        """Reset alert counters when period boundaries are crossed"""
        for symbol in self.symbols:
            for timeframe in self.timeframes.keys():
                current_period = self._get_period_key(timeframe)
                last_period = self.alert_tracking[symbol][timeframe]["last_reset"]
                
                # If period changed, reset counter (BUG FIX #1: removed locked flag)
                if current_period != last_period:
                    self.alert_tracking[symbol][timeframe]["count"] = 0
                    # BUG FIX #1: Don't reset open_time tracking - keep historical data
                    # self.alert_tracking[symbol][timeframe]["last_alerted_open_time"] = None
                    self.alert_tracking[symbol][timeframe]["last_reset"] = current_period
                    logger.debug(f"🔄 Reset counters for {symbol} {timeframe} (new period: {current_period})")
    
    async def check_symbol_timeframe(self, symbol: str, timeframe: str):
        """Check a single symbol on a single timeframe INDEPENDENTLY
        
        Rules:
        - 1h: ≥75% threshold, max 3 alerts per day
        - 24h: ≥75% threshold, max 1 alert per day
        - One alert per unique candle (tracked by open_time)
        """
        try:
            # Get the max alerts for this timeframe
            max_alerts = 3 if timeframe == "1h" else 1
            
            # Get current and previous candle volumes
            result = self.fetcher.get_current_and_previous(symbol, timeframe)
            if not result:
                logger.debug(f"⚠️ {symbol} {timeframe}: No data from Binance")
                return
            
            previous_candle, current_candle = result
            
            # BUG FIX #1: Check if this candle already triggered an alert
            tracking = self.alert_tracking[symbol][timeframe]
            current_open_time = current_candle.get("open_time")
            
            # DEBUG: Log the dedup check details
            logger.debug(f"[DEDUP] {symbol} {timeframe}: current_open_time={current_open_time}, "
                        f"last_alerted_open_time={tracking['last_alerted_open_time']}")
            
            if current_open_time == tracking["last_alerted_open_time"]:
                logger.debug(f"✓ {symbol} {timeframe}: Already alerted for this candle (open_time={current_open_time})")
                return
            
            # IMPROVEMENT: Check if alert is in cooldown period
            # For 1h: 3-hour cooldown (only allow 1 alert per 3 hours)
            # For 24h: No time cooldown - just one alert per candle (handled by last_alerted_open_time above)
            if timeframe == "1h":
                current_time = time.time()
                time_since_last_alert = current_time - tracking.get("last_alert_timestamp", 0)
                cooldown_seconds = tracking.get("cooldown_seconds", 10800)  # 3 hours
                
                if time_since_last_alert < cooldown_seconds:
                    cooldown_remaining = cooldown_seconds - time_since_last_alert
                    cooldown_hours = cooldown_remaining / 3600
                    logger.debug(f"⏳ {symbol} {timeframe}: In cooldown period ({cooldown_hours:.1f}h remaining). "
                               f"Will skip until next alert window.")
                    return
            
            # Get the threshold for this timeframe
            threshold = VolumeAlertConfig.VOLUME_THRESHOLDS.get(timeframe, 75)
            
            # Calculate volume change
            prev_volume = previous_candle.get("volume", 0)
            curr_volume = current_candle.get("volume", 0)
            
            if prev_volume == 0:
                return
            
            volume_change_pct = ((curr_volume - prev_volume) / prev_volume) * 100
            
            # Check if threshold is met (only positive changes)
            if volume_change_pct >= threshold:
                # Threshold met! Check if we can send alert
                if tracking["count"] < max_alerts:
                    # Send the alert
                    alert = {
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "volume_change_pct": volume_change_pct,
                        "current_price": current_candle.get("close", 0),
                        "timestamp": datetime.now().isoformat(),
                        "open_time": current_open_time  # BUG FIX #1: Add open_time to alert
                    }
                    
                    # Queue or send the alert
                    await self._queue_or_send_alert(alert, symbol, timeframe, max_alerts, current_open_time)
                else:
                    logger.info(f"⚠️ {symbol} {timeframe}: Max alerts ({max_alerts}) reached for period")
            else:
                # BUG FIX #6: Log when decrease is detected and ignored
                if volume_change_pct < 0:
                    logger.debug(f"📉 {symbol} {timeframe}: Volume DECREASE {volume_change_pct:+.1f}% (ignored)")
                else:
                    logger.debug(f"⏭️ {symbol} {timeframe}: {volume_change_pct:+.1f}% (need ≥{threshold:.0f}%)")
        
        except Exception as e:
            logger.error(f"Error checking {symbol} {timeframe}: {e}")
    
    async def _queue_or_send_alert(self, alert: dict, symbol: str, timeframe: str, max_alerts: int, open_time: int):
        """Queue alert if within 10-min gap, otherwise send immediately
        
        BUG FIX #2: Removed locked flag - use count checking only
        IMPROVEMENT: Track last_alert_timestamp for cooldown enforcement
        """
        current_time = time.time()
        time_since_last = current_time - self.last_alert_timestamp
        
        # If last alert was < 10 min ago, queue this alert
        if time_since_last < self.alert_queue_gap and self.last_alert_timestamp > 0:
            # Queue includes: (timestamp, alert_dict, symbol, timeframe, max_alerts, open_time)
            self.pending_alerts.append((current_time, alert, symbol, timeframe, max_alerts, open_time))
            wait_time = self.alert_queue_gap - time_since_last
            
            # BUG FIX #2: Increment count but DON'T set locked=True
            self.alert_tracking[symbol][timeframe]["count"] += 1
            self.alert_tracking[symbol][timeframe]["last_alerted_open_time"] = open_time
            # IMPROVEMENT: Record the timestamp for cooldown tracking
            self.alert_tracking[symbol][timeframe]["last_alert_timestamp"] = current_time
            self._save_alert_tracking()
            
            logger.info(f"📥 Alert QUEUED for {symbol} {timeframe}: {alert['volume_change_pct']:+.2f}% "
                       f"(will send in {wait_time:.0f}s, queue size: {len(self.pending_alerts)})")
        else:
            # Send immediately
            await self.send_alert_formatted(alert)
            self.last_alert_timestamp = current_time
            
            # BUG FIX #2: Mark as alerted without locked flag
            self.alert_tracking[symbol][timeframe]["count"] += 1
            self.alert_tracking[symbol][timeframe]["last_alerted_open_time"] = open_time
            # IMPROVEMENT: Record the timestamp for cooldown tracking
            self.alert_tracking[symbol][timeframe]["last_alert_timestamp"] = current_time
            self._save_alert_tracking()
            
            logger.info(f"📤 Alert sent for {symbol} {timeframe}: {alert['volume_change_pct']:+.2f}% "
                       f"({self.alert_tracking[symbol][timeframe]['count']}/{max_alerts})")
    
    async def send_alert_formatted(self, alert: dict):
        """Send formatted alert to Telegram"""
        try:
            # Determine emoji based on direction
            direction_emoji = "📈" if alert['volume_change_pct'] > 0 else "📉"
            direction_text = "INCREASE" if alert['volume_change_pct'] > 0 else "DECREASE"
            
            message = (
                f"🚨 {alert['symbol']} VOLUME ALERT {direction_emoji}\n\n"
                f"⏱️ Timeframe: {alert['timeframe']}\n"
                f"💹 Current Price: ${alert['current_price']:,.2f}\n"
                f"📊 Volume Change: {alert['volume_change_pct']:+.2f}%\n\n"
                f"⚠️ Volume Spike Detected"
            )
            
            await self.telegram.send_alert_message(message)
            logger.info(f"✅ Alert sent for {alert['symbol']} {alert['timeframe']}")
            return True
        except Exception as e:
            logger.error(f"Error sending alert: {e}")
            return False
    
    def test_telegram(self):
        """Test Telegram connectivity"""
        logger.info("Testing Telegram connection...")
        try:
            # Just verify credentials exist, don't make API call
            if not self.telegram_token or not self.telegram_chat_id:
                logger.error("Missing Telegram credentials")
                return False
            logger.info(f"✅ Telegram bot configured: Chat ID {self.telegram_chat_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Telegram test failed: {e}")
            return False
    
    def _load_alert_tracking(self):
        """Load persisted alert tracking from file"""
        import json
        import os
        tracking_file = "data/alert_tracking.json"
        try:
            if os.path.exists(tracking_file):
                with open(tracking_file, 'r') as f:
                    saved_tracking = json.load(f)
                    logger.debug(f"📂 Loaded saved tracking: {json.dumps(saved_tracking, indent=2)}")
                    
                    # Merge saved tracking with current (to preserve new symbols/timeframes)
                    for symbol in self.alert_tracking:
                        if symbol in saved_tracking:
                            for timeframe in self.alert_tracking[symbol]:
                                if timeframe in saved_tracking[symbol]:
                                    # Check if period is still today
                                    current_period = self._get_period_key(timeframe)
                                    saved_period = saved_tracking[symbol][timeframe].get("last_reset")
                                    
                                    if current_period == saved_period:
                                        # Same period - load the tracking but preserve new fields
                                        saved_data = saved_tracking[symbol][timeframe]
                                        # Update only the old fields, keep the new ones from initialization
                                        self.alert_tracking[symbol][timeframe]["count"] = saved_data.get("count", 0)
                                        self.alert_tracking[symbol][timeframe]["last_alerted_open_time"] = saved_data.get("last_alerted_open_time")
                                        self.alert_tracking[symbol][timeframe]["last_reset"] = saved_data.get("last_reset", current_period)
                                        # Preserve new fields from initialization if not in saved data
                                        if "last_alert_timestamp" in saved_data:
                                            self.alert_tracking[symbol][timeframe]["last_alert_timestamp"] = saved_data["last_alert_timestamp"]
                                        # cooldown_seconds stays from initialization
                                        logger.debug(f"✓ Loaded tracking for {symbol} {timeframe}: "
                                                   f"count={self.alert_tracking[symbol][timeframe]['count']}, "
                                                   f"last_alerted_open_time={self.alert_tracking[symbol][timeframe]['last_alerted_open_time']}")
                logger.info("✅ Alert tracking loaded from disk")
        except Exception as e:
            logger.warning(f"Could not load alert tracking: {e}")
    
    def _save_alert_tracking(self):
        """Save alert tracking to file for persistence"""
        import json
        import os
        tracking_file = "data/alert_tracking.json"
        try:
            os.makedirs("data", exist_ok=True)
            with open(tracking_file, 'w') as f:
                json.dump(self.alert_tracking, f, indent=2)
            logger.debug("✓ Alert tracking saved to disk")
        except Exception as e:
            logger.warning(f"Could not save alert tracking: {e}")

async def main():
    """Entry point"""
    logger.info("\n" + "="*60)
    logger.info("🚀 VOLUME ALERT BOT STARTING")
    logger.info("="*60 + "\n")
    
    try:
        logger.info("Initializing bot...")
        bot = VolumeAlertBot()
        
        # Test Telegram connection
        logger.info("Testing Telegram connection...")
        if not bot.test_telegram():
            logger.error("Cannot connect to Telegram. Exiting.")
            sys.exit(1)
        
        logger.info(f"✅ Bot ready")
        logger.info(f"📊 Monitoring: {', '.join(bot.symbols)}")
        logger.info(f"⏱️ Timeframes: {', '.join(bot.timeframes.keys())}")
        logger.info(f"📊 Volume thresholds: 1h=75%, 24h=75% (only increases)")
        logger.info(f"⏳ Check interval: {bot.check_interval}s (5 minutes)")
        logger.info(f"🚫 Max alerts per symbol: {bot.max_alerts_per_symbol}")
        logger.info(f"💬 Telegram Chat ID: {bot.telegram_chat_id}")
        logger.info(f"🔔 Strategy: Send alert when volume increase meets threshold")
        logger.info(f"🚫 Max {bot.max_alerts_per_symbol} alerts per symbol per cycle")
        
        # Run monitoring loop
        await bot.run()
    
    except KeyboardInterrupt:
        logger.info("✅ Bot stopped gracefully")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
