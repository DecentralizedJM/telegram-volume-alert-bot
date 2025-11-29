from dataclasses import dataclass
from typing import Dict

@dataclass
class VolumeAlertConfig:
    """Configuration for Volume Alert Bot"""
    
    # Monitoring assets
    SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    
    # Timeframes to monitor (name -> minutes)
    TIMEFRAMES = {
        "1h": 60,
        "12h": 720,
        "24h": 1440
    }
    
    # Volume change threshold (%)
    # Alert when |volume_change| >= this threshold
    VOLUME_THRESHOLD = 30
    
    # Max alerts per symbol to avoid spam
    # Example: Max 3 BTC alerts, max 3 ETH alerts, max 3 SOL alerts
    MAX_ALERTS_PER_SYMBOL = 3
    
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
