import asyncio
import logging
import os
import sys
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
        
        # Track alerts sent per symbol (resets every cycle)
        # Format: {"BTCUSDT": 2, "ETHUSDT": 1, "SOLUSDT": 0}
        self.alerts_sent_this_cycle = {symbol: 0 for symbol in self.symbols}
        
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
        """Check volume for all symbols and timeframes
        
        Strategy:
        1. Reset per-symbol alert counter at start of each 5-min cycle
        2. Check all 9 combinations (3 symbols × 3 timeframes)
        3. Send alert IMMEDIATELY if volume change > 30%
        4. Cap alerts per symbol at 3 per cycle
        """
        # Only run if bot is active
        if not self.bot_running:
            logger.debug("⏸️ Bot is paused, skipping volume check")
            return
        
        # Reset alert counters for this cycle
        self.alerts_sent_this_cycle = {symbol: 0 for symbol in self.symbols}
        
        tasks = []
        
        for symbol in self.symbols:
            for timeframe_name, timeframe_minutes in self.timeframes.items():
                # Convert to Binance interval format
                binance_interval = VolumeAlertConfig.get_binance_interval(timeframe_minutes)
                tasks.append(
                    self.check_symbol_volume(symbol, binance_interval, timeframe_name)
                )
        
        # Run all checks concurrently
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def check_symbol_volume(self, symbol: str, interval: str, timeframe_name: str):
        """Check volume for a specific symbol and timeframe
        
        Sends alert IMMEDIATELY if:
        1. Volume change is >= 30%
        2. Haven't sent 3+ alerts for this symbol in this cycle
        """
        try:
            # Fetch current and previous candles
            result = self.fetcher.get_current_and_previous(symbol, interval)
            
            if not result:
                return
            
            current, previous = result
            
            # Detect if alert should be sent
            alert = self.detector.detect_volume_alert(current, previous)
            
            if alert:
                # Check if we can send more alerts for this symbol
                if self.alerts_sent_this_cycle[symbol] < self.max_alerts_per_symbol:
                    # Send immediately
                    await self.telegram.send_alert(alert)
                    self.alerts_sent_this_cycle[symbol] += 1
                    logger.info(f"📤 Alert sent for {symbol} - {self.alerts_sent_this_cycle[symbol]}/{self.max_alerts_per_symbol}")
                else:
                    logger.debug(f"⚠️ Max alerts reached for {symbol} this cycle ({self.max_alerts_per_symbol})")
        
        except Exception as e:
            logger.error(f"Error checking {symbol} {timeframe_name}: {e}")
    
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
        print(f"📊 Volume threshold: {VolumeAlertConfig.VOLUME_THRESHOLD}%")
        print(f"⏳ Check interval: {bot.check_interval}s (5 minutes)")
        print(f"� Max alerts per symbol: {bot.max_alerts_per_symbol}")
        print(f"�💬 Telegram Chat ID: {bot.telegram_chat_id}")
        print(f"\n🔔 Strategy: Send alert IMMEDIATELY when volume > 30%")
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
