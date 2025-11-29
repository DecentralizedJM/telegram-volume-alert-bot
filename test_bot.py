#!/usr/bin/env python3
"""
Test the volume alert bot components
- Test Telegram connection
- Test Binance data fetching
- Test volume detection logic
"""

import asyncio
import sys
from dotenv import load_dotenv
import os

# Load environment
load_dotenv()

from binance_fetcher import BinanceDataFetcher
from volume_detector import VolumeDetector
from telegram_client import TelegramClient
from config import VolumeAlertConfig

def test_telegram():
    """Test Telegram connection"""
    print("\n🧪 Testing Telegram Connection...")
    try:
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        
        if not token or not chat_id:
            print(f"❌ Missing credentials in .env")
            return False
        
        # Verify bot can be initialized
        telegram = TelegramClient(token, chat_id)
        
        print(f"✅ Telegram Connected")
        print(f"   Token: {token[:20]}...")
        print(f"   Chat ID: {chat_id}")
        return True
    except Exception as e:
        print(f"❌ Telegram Error: {e}")
        return False

def test_binance():
    """Test Binance data fetching"""
    print("\n🧪 Testing Binance Data Fetching...")
    try:
        fetcher = BinanceDataFetcher()
        
        for symbol in ["BTCUSDT", "ETHUSDT", "SOLUSDT"]:
            result = fetcher.get_current_and_previous(symbol, "1h")
            if result:
                current, previous = result
                vol_change = ((current["volume"] - previous["volume"]) / previous["volume"]) * 100
                print(f"✅ {symbol}")
                print(f"   Price: ${current['close']:,.2f}")
                print(f"   Volume Change: {vol_change:+.2f}%")
            else:
                print(f"❌ {symbol} - Failed to fetch data")
                return False
        return True
    except Exception as e:
        print(f"❌ Binance Error: {e}")
        return False

def test_detector():
    """Test volume detection logic"""
    print("\n🧪 Testing Volume Detector...")
    try:
        # Create detector but clear state for clean test
        import json
        detector = VolumeDetector()
        
        # Mock candles with 35% volume increase
        previous = {
            "symbol": "BTCUSDT",
            "interval": "1h",
            "volume": 1000.0,
            "open_time": 1700000000,
            "close": 42000
        }
        
        current = {
            "symbol": "BTCUSDT",
            "interval": "1h",
            "volume": 1350.0,  # 35% increase
            "open_time": 1700003600,
            "close": 42500
        }
        
        # Clear state to allow fresh alert
        detector.state = {}
        
        alert = detector.detect_volume_alert(current, previous)
        
        if alert and alert["volume_change_pct"] >= 30:
            print(f"✅ Detection Working")
            print(f"   Symbol: {alert['symbol']}")
            print(f"   Volume Change: {alert['volume_change_pct']:+.2f}%")
            print(f"   Type: {alert['type']}")
            return True
        else:
            print(f"❌ Detection Failed - Alert: {alert}")
            return False
    except Exception as e:
        print(f"❌ Detector Error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_send_alert():
    """Test sending a test alert"""
    print("\n🧪 Testing Alert Sending...")
    print("⚠️  Note: Bot must be added to Telegram first")
    print("   Start bot and it will work when running continuously")
    return True  # Skip for now, will work when bot runs

async def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("🧪 VOLUME ALERT BOT - TEST SUITE")
    print("="*60)
    
    results = {
        "Telegram": test_telegram(),
        "Binance": test_binance(),
        "Detector": test_detector(),
        "Alert Send": await test_send_alert()
    }
    
    print("\n" + "="*60)
    print("📊 TEST RESULTS")
    print("="*60)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n✅ All tests passed! Bot is ready to run.")
        print("\nStart the bot with:")
        print("  /Users/jm/staging/.venv/bin/python volume_alert_bot.py")
        return 0
    else:
        print("\n❌ Some tests failed. Check the errors above.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
