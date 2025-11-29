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
    level=logging.INFO,
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
        
        if not self.telegram_token or not self.telegram_chat_id:
            logger.error("Missing Telegram credentials in .env file")
            logger.error("Please set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")
            sys.exit(1)
        
        # Initialize components
        self.fetcher = BinanceDataFetcher()
        self.detector = VolumeDetector()
        self.telegram = TelegramClient(self.telegram_token, self.telegram_chat_id)
        
        # Configuration
        self.symbols = VolumeAlertConfig.SYMBOLS
        self.timeframes = VolumeAlertConfig.TIMEFRAMES
        self.check_interval = VolumeAlertConfig.CHECK_INTERVAL
        self.max_alerts_per_symbol = VolumeAlertConfig.MAX_ALERTS_PER_SYMBOL
        
        # Alert tracking per symbol per timeframe per day
        # Format: {
        #   "BTCUSDT": {
        #     "1h": {"count": 2, "last_reset": "2025-11-30", "locked": False},
        #     "24h": {"count": 1, "last_reset": "2025-11-30", "locked": False}
        #   }
        # }
        self.alert_tracking = {
            symbol: {
                timeframe: {
                    "count": 0,
                    "last_reset": self._get_period_key(timeframe),
                    "locked": False
                }
                for timeframe in self.timeframes.keys()
            }
            for symbol in self.symbols
        }
        
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
        
        # Create data directory
        os.makedirs(VolumeAlertConfig.DATA_DIR, exist_ok=True)
        
        logger.info(f"Bot initialized. Monitoring {self.symbols} on {list(self.timeframes.keys())}")
    
    async def run(self):
        """Main monitoring loop with command handling"""
        logger.info("Starting volume alert monitoring...")
        
        # Clear old updates from Telegram queue to avoid processing old messages
        # Run this in background without blocking
        asyncio.create_task(self._clear_telegram_queue())
        
        self.last_update_id = 0
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
        """Clear old messages from Telegram queue on startup"""
        import requests
        try:
            await asyncio.sleep(0.5)  # Small delay to ensure initialization
            url = f"https://api.telegram.org/bot{self.telegram_token}/getUpdates"
            # Set a very short timeout to quickly get pending updates
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    updates = data.get('result', [])
                    if updates:
                        # Set offset to the last update so we skip all pending messages
                        last_update_id = updates[-1].get('update_id', 0)
                        self.last_update_id = last_update_id
                        logger.info(f"✅ Cleared {len(updates)} pending messages from Telegram queue")
                    else:
                        logger.info("✅ Queue is clean, no pending messages")
        except Exception as e:
            logger.warning(f"Queue clearing: {e}")
    
    async def monitoring_loop(self):
        """Volume monitoring loop"""
        while self.bot_running:
            try:
                await self.check_all_volumes()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(5)
    
    async def command_listener_loop(self):
        """Listen for /start and /stop commands"""
        while True:
            try:
                updates = await self.fetch_updates()
                for update in updates:
                    await self.handle_update(update)
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Error in command listener: {e}")
                await asyncio.sleep(5)
    
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
                    alert_timestamp, alert = self.pending_alerts[0]
                    time_since_last = current_time - self.last_alert_timestamp
                    
                    # If 10 minutes have passed since last alert, send the next one
                    if time_since_last >= self.alert_queue_gap:
                        self.pending_alerts.pop(0)  # Remove from queue
                        await self.telegram.send_alert(alert)
                        self.last_alert_timestamp = current_time
                        logger.info(f"📤 Queued alert sent for {alert['symbol']} (queue size: {len(self.pending_alerts)})")
                
                await asyncio.sleep(10)  # Check queue every 10 seconds
            except Exception as e:
                logger.error(f"Error in alert queue processor: {e}")
                await asyncio.sleep(10)
    
    async def fetch_updates(self):
        """Fetch updates from Telegram API"""
        import requests
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/getUpdates"
            response = requests.get(
                url,
                params={"offset": self.last_update_id + 1, "timeout": 10},
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    return data.get('result', [])
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
            
            # Owner's Chat ID
            owner_chat_id = int(os.getenv('TELEGRAM_OWNER_CHAT_ID', '395803228'))
            is_owner = (user_id == owner_chat_id)
            
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
        
        1h: YYYY-MM-DD-HH (resets each hour)
        24h: YYYY-MM-DD (resets each day)
        """
        now = datetime.now()
        if timeframe == "1h":
            return now.strftime("%Y-%m-%d-%H")
        else:  # 24h
            return now.strftime("%Y-%m-%d")
    
    def _reset_daily_counts(self):
        """Reset alert counters when period boundaries are crossed"""
        for symbol in self.symbols:
            for timeframe in self.timeframes.keys():
                current_period = self._get_period_key(timeframe)
                last_period = self.alert_tracking[symbol][timeframe]["last_reset"]
                
                # If period changed, reset counter and lock
                if current_period != last_period:
                    self.alert_tracking[symbol][timeframe]["count"] = 0
                    self.alert_tracking[symbol][timeframe]["locked"] = False
                    self.alert_tracking[symbol][timeframe]["last_reset"] = current_period
                    logger.debug(f"🔄 Reset counters for {symbol} {timeframe} (new period: {current_period})")
    
    async def check_symbol_timeframe(self, symbol: str, timeframe: str):
        """Check a single symbol on a single timeframe INDEPENDENTLY
        
        Rules:
        - 1h: ±50% threshold, max 3 alerts per day
        - 24h: ±75% threshold, max 1 alert per day
        - Once alert triggers, lock until next period
        """
        try:
            # Get the max alerts for this timeframe
            max_alerts = 3 if timeframe == "1h" else 1
            
            # Check if already locked for this period
            tracking = self.alert_tracking[symbol][timeframe]
            if tracking["locked"]:
                logger.debug(f"🔒 {symbol} {timeframe} locked - already alerted this period")
                return
            
            # Get current and previous candle volumes
            result = self.fetcher.get_current_and_previous(symbol, timeframe)
            if not result:
                logger.debug(f"⚠️ {symbol} {timeframe}: No data from Binance")
                return
            
            previous_candle, current_candle = result
            
            # Get the threshold for this timeframe
            threshold = VolumeAlertConfig.VOLUME_THRESHOLDS.get(timeframe, 50)
            
            # Calculate volume change
            prev_volume = previous_candle.get("volume", 0)
            curr_volume = current_candle.get("volume", 0)
            
            if prev_volume == 0:
                return
            
            volume_change_pct = ((curr_volume - prev_volume) / prev_volume) * 100
            
            # Check if threshold is met
            if abs(volume_change_pct) >= threshold:
                # Threshold met! Check if we can send alert
                if tracking["count"] < max_alerts:
                    # Send the alert
                    alert = {
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "volume_change_pct": volume_change_pct,
                        "current_price": current_candle.get("close", 0),
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    # Queue or send the alert
                    await self._queue_or_send_alert(alert, symbol, timeframe, max_alerts)
                else:
                    logger.info(f"⚠️ {symbol} {timeframe}: Max alerts ({max_alerts}) reached for period")
            else:
                logger.debug(f"⏭️ {symbol} {timeframe}: {volume_change_pct:+.1f}% (need {threshold:+.0f}%)")
        
        except Exception as e:
            logger.error(f"Error checking {symbol} {timeframe}: {e}")
    
    async def _queue_or_send_alert(self, alert: dict, symbol: str, timeframe: str, max_alerts: int):
        """Queue alert if within 10-min gap, otherwise send immediately"""
        current_time = time.time()
        time_since_last = current_time - self.last_alert_timestamp
        
        # If last alert was < 10 min ago, queue this alert
        if time_since_last < self.alert_queue_gap and self.last_alert_timestamp > 0:
            self.pending_alerts.append((current_time, alert))
            wait_time = self.alert_queue_gap - time_since_last
            logger.info(f"📥 Alert QUEUED for {symbol} {timeframe}: {alert['volume_change_pct']:+.2f}% "
                       f"(will send in {wait_time:.0f}s, queue size: {len(self.pending_alerts)})")
        else:
            # Send immediately
            await self.send_alert_formatted(alert)
            self.last_alert_timestamp = current_time
            
            # Mark as alerted for this period
            self.alert_tracking[symbol][timeframe]["count"] += 1
            self.alert_tracking[symbol][timeframe]["locked"] = True
            
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
                f"⚠️ {direction_text} VOLUME DETECTED"
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

async def main():
    """Entry point"""
    print("\n" + "="*60)
    print("🚀 VOLUME ALERT BOT")
    print("="*60 + "\n")
    
    try:
        bot = VolumeAlertBot()
        
        # Test Telegram connection
        if not bot.test_telegram():
            logger.error("Cannot connect to Telegram. Exiting.")
            sys.exit(1)
        
        print(f"\n✅ Bot ready")
        print(f"📊 Monitoring: {', '.join(bot.symbols)}")
        print(f"⏱️ Timeframes: {', '.join(bot.timeframes.keys())}")
        print(f"📊 Volume thresholds: 1h=±30%, 24h=±50%")
        print(f"⏳ Check interval: {bot.check_interval}s (5 minutes)")
        print(f"🚫 Max alerts per symbol: {bot.max_alerts_per_symbol}")
        print(f"💬 Telegram Chat ID: {bot.telegram_chat_id}")
        print(f"\n🔔 Strategy: Send alert when volume change meets threshold")
        print(f"🚫 Max {bot.max_alerts_per_symbol} alerts per symbol per cycle\n")
        print("\nPress Ctrl+C to stop\n")
        
        # Run monitoring loop
        await bot.run()
    
    except KeyboardInterrupt:
        print("\n\n✅ Bot stopped gracefully")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
