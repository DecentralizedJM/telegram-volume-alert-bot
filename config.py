from dataclasses import dataclass
from typing import Dict

@dataclass
class VolumeAlertConfig:
    """Configuration for Volume Alert Bot"""
    
    # Monitoring assets
    SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    
    # Timeframes to monitor (name -> minutes)
    # 1h: alerts on ±30% change from previous hour
    # 24h: alerts on ±50% change in rolling 24h window
    TIMEFRAMES = {
        "1h": 60,
        "24h": 1440
    }
    
    # Volume change thresholds (%) by timeframe
    VOLUME_THRESHOLDS = {
        "1h": 75,      # 1-hour: ±75% threshold (high to reduce spam, only major spikes)
        "24h": 75      # 24-hour rolling: ±75% threshold (restrictive, only major changes)
    }
    
    # Max alerts per symbol to avoid spam
    # Max 3 BTC alerts per DAY, max 3 ETH alerts per DAY, max 3 SOL alerts per DAY
    # Period resets daily at UTC midnight
    # BUG FIX #4: Clarified that reset is DAILY, not hourly
    MAX_ALERTS_PER_SYMBOL = 3
    
    # Alert queue settings: Minimum gap between alerts (in seconds)
    # When first alert is sent, wait at least 10 minutes before next alert
    # This prevents alert spam - only 1 alert per 10 minutes maximum
    ALERT_QUEUE_GAP_SECONDS = 600  # 10 minutes = 600 seconds
    
    # Check interval in seconds (5 minutes = 300 seconds)
    # Bot checks every 5 minutes and sends alerts immediately if volume > 30%
    CHECK_INTERVAL = 300
    
    # Binance API settings
    BINANCE_BASE_URL = "https://api.binance.com"
    BINANCE_KLINES_ENDPOINT = "/api/v3/klines"
    
    # Data storage
    DATA_DIR = "data"
    STATE_FILE = "data/candle_state.json"
    LOG_FILE = "data/volume_alerts.log"
    
    # Telegram settings (loaded from .env)
    # TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    # TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
    # TELEGRAM_TOPIC_ID = os.getenv("TELEGRAM_TOPIC_ID", None)  # Optional: Topic ID if using Telegram topics
    
    @staticmethod
    def get_binance_interval(minutes: int) -> str:
        """Convert minutes to Binance interval format"""
        if minutes == 60:
            return "1h"
        elif minutes == 720:
            return "12h"
        elif minutes == 1440:
            return "1d"
        else:
            return f"{minutes}m"
