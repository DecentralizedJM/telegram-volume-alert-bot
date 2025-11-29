# Telegram Volume Alert Bot

Real-time cryptocurrency volume alert system for Telegram. Monitors BTC, ETH, and SOL for significant volume movements (±30%+) across multiple timeframes and sends instant notifications.

**Created for Mudrex™ | Proprietary Software**

---

## Features

- **Multi-Asset Monitoring**: BTC, ETH, SOL (easily extensible to other assets)
- **Multiple Timeframes**: 1-hour, 12-hour, 24-hour candles
- **Volume Detection**: Identifies volume increases/decreases of 30%+ from previous candle
- **Real-Time Alerts**: Instant Telegram notifications with price and volume data
- **Owner Control**: Start/stop monitoring with Telegram commands
- **Persistent Monitoring**: Continuous market surveillance with configurable intervals
- **Professional Formatting**: HTML-formatted Telegram messages with emojis and metrics

---

## Quick Start

### Prerequisites

- Python 3.8+
- Telegram Bot (created via @BotFather)
- Telegram group or personal chat

### Installation

```bash
git clone https://github.com/DecentralizedJM/telegram-volume-alert-bot.git
cd telegram-volume-alert-bot
pip install -r requirements.txt
```

### Configuration

1. **Create `.env` file**:
```
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
TELEGRAM_OWNER_CHAT_ID=your_owner_chat_id_here
```

2. **Run the bot**:
```bash
python3 volume_alert_bot.py
```

---

## Usage

### Starting the Bot

In Telegram group chat:
```
/start @YourBotUsername
```

### Stopping the Bot

In Telegram group chat:
```
/stop @YourBotUsername
```

**Note**: Only the owner (defined by `TELEGRAM_OWNER_CHAT_ID`) can control the bot.

---

## Configuration

Edit `config.py` to customize:

```python
# Monitoring symbols
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

# Timeframes (in minutes)
TIMEFRAMES = {
    "1h": 60,
    "12h": 720,
    "24h": 1440
}

# Volume threshold percentage
VOLUME_THRESHOLD = 30

# Check interval in seconds
CHECK_INTERVAL = 300

# Max alerts per symbol per cycle
MAX_ALERTS_PER_SYMBOL = 3
```

---

## How It Works

### Data Flow

```
Binance API → Fetch OHLCV Data → Volume Analysis → Detection → Telegram Alert
```

### Volume Detection

1. Fetches current and previous candle data from Binance
2. Calculates volume change: `((current - previous) / previous) × 100`
3. If `|change| ≥ VOLUME_THRESHOLD`: Generates alert
4. Respects maximum alert limit per symbol per monitoring cycle

### Alert Format

```
🚨 BTCUSDT VOLUME ALERT 📈

⏱️ Timeframe: 1h
� Current Price: $42,530.50
� Volume Change: +35.2%

⚠️ INCREASE VOLUME DETECTED
```

---

## Architecture

### File Structure

```
telegram-volume-alert-bot/
├── volume_alert_bot.py       # Main entry point
├── config.py                 # Configuration settings
├── binance_fetcher.py        # Binance API integration
├── volume_detector.py        # Volume analysis logic
├── telegram_client.py        # Telegram messaging
├── command_handler.py        # Command utilities
├── requirements.txt          # Python dependencies
├── .env.example              # Environment template
├── LICENSE                   # Proprietary license
└── README.md                 # This file
```

### Components

- **VolumeAlertBot**: Main orchestrator with async monitoring and command loops
- **BinanceDataFetcher**: Real-time OHLCV data retrieval from Binance API
- **VolumeDetector**: Volume change calculation and alert detection
- **TelegramClient**: Message formatting and Telegram API integration

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | Target chat ID for alerts |
| `TELEGRAM_OWNER_CHAT_ID` | Owner chat ID for command control |

---

## Troubleshooting

### Bot not responding to commands

- Verify bot has been added to the group
- Ensure you're using the correct format: `/start @BotUsername`
- Check that your chat ID matches `TELEGRAM_OWNER_CHAT_ID`

### No alerts received

- Verify `.env` file contains correct credentials
- Check network connectivity to Binance API
- Review logs for API errors

### Too many/few alerts

- Adjust `VOLUME_THRESHOLD` in `config.py`
- Modify `CHECK_INTERVAL` for frequency
- Change `MAX_ALERTS_PER_SYMBOL` to control alert cap

---

## Docker Deployment

```bash
docker-compose up -d
```

Configure environment variables in `.env` before running.

---

## API Sources

- **Market Data**: Binance Public API (no authentication required)
- **Notifications**: Telegram Bot API
- **Candle Data**: 15-minute candles with 200-candle history

---

## License

**PROPRIETARY & CONFIDENTIAL**

This software is proprietary and created exclusively for Mudrex. Unauthorized copying, modification, or distribution is prohibited.

**Copyright © 2025 @DecentralizedJM. All rights reserved.**

For licensing inquiries: [@DecentralizedJM](https://github.com/DecentralizedJM)

See [LICENSE](./LICENSE) file for complete terms.

---

## Technical Stack

- **Language**: Python 3.8+
- **Async**: asyncio
- **APIs**: Binance, Telegram
- **Dependencies**: requests, python-dotenv

---

## Status

🟢 **Production Ready** | Last Updated: November 2025

