# Telegram Volume Alert Bot

Real-time cryptocurrency volume alert system for Telegram. Monitors BTC, ETH, and SOL for significant volume movements across multiple timeframes and sends instant notifications.

**Created for Mudrex™ | Proprietary Software**

---

## Features

- **Multi-Asset Monitoring**: BTC, ETH, SOL (easily extensible to other assets)
- **Dual Timeframe Monitoring**: 
  - **1-Hour**: ±30% volume change detection
  - **24-Hour**: ±50% volume change detection (rolling window)
- **Consecutive Period Comparison**: Compares volume between consecutive periods (not fixed baselines)
- **Real-Time Alerts**: Instant Telegram notifications with price and volume data
- **Owner Control**: Start/stop monitoring with Telegram commands
- **Persistent Monitoring**: Continuous market surveillance (checks every 5 minutes)
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

### Bot Commands

#### `/start @BotUsername` - Activate Monitoring
In Telegram group chat:
```
/start @YourBotUsername
```
**Owner-only**: Activates volume monitoring (only the owner can use this)

#### `/stop @BotUsername` - Pause Monitoring
In Telegram group chat:
```
/stop @YourBotUsername
```
**Owner-only**: Pauses volume monitoring (only the owner can use this)

#### `/status @BotUsername` - Check Bot Status
In Telegram group chat:
```
/status @YourBotUsername
```
**Anyone can use**: Shows the current bot status, configuration, and available commands

Example Response:
```
📊 Mudrex Volume Alert Bot Status

✅ Bot is active
⏱️ Volume data checking every 5 minutes

Current Configuration:
• Monitoring: BTCUSDT, ETHUSDT, SOLUSDT
• 1h Threshold: ±30% volume change
• 24h Threshold: ±50% volume change
• Check Interval: 5 minutes
```

---

**Note**: `/start` and `/stop` are owner-only commands (defined by `TELEGRAM_OWNER_CHAT_ID`). Anyone can use `/status`.

---

## Configuration

Edit `config.py` to customize:

```python
# Monitoring symbols
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

# Timeframes to monitor
TIMEFRAMES = {
    "1h": 60,       # 1-hour candle
    "24h": 1440     # 24-hour rolling window
}

# Volume change thresholds (%) by timeframe
VOLUME_THRESHOLDS = {
    "1h": 30,       # Alert on ±30% hourly volume change
    "24h": 50       # Alert on ±50% 24h rolling window change
}

# Check interval in seconds (5 minutes)
CHECK_INTERVAL = 300

# Max alerts per symbol per cycle
MAX_ALERTS_PER_SYMBOL = 3
```

---

## Volume Detection Logic

### How It Works

The bot compares **previous closed candle with current incomplete candle** to detect volume changes in REAL-TIME:

**1-Hour Timeframe (1h)**
- Compares: Previous complete hour (closed) vs Current incomplete hour (live data)
- Threshold: ±30% volume change
- Updates: Every 5 minutes with fresh market data
- Example: At 1:14 PM, if volume spike >30% compared to 12-1 PM close → Alert immediately (no wait for 1 PM close)

**24-Hour Rolling Window (24h)**
- Compares: Previous complete day (closed) vs Current incomplete day (rolling 24h)
- Threshold: ±50% volume change
- Updates: Every 5 minutes with latest volume data

### Detection Formula

```
Volume Change % = ((Current Incomplete Volume - Previous Closed Volume) / Previous Closed Volume) × 100

Alert Triggers When:
- 1h:  |Volume Change %| ≥ 30%
- 24h: |Volume Change %| ≥ 50%
```

### Real-Time Behavior

⚡ **Alerts happen continuously throughout the hour, not just when the candle closes:**

Example Timeline:
- **1:00 PM** - Previous hour (12-1 PM) closes, bot starts checking against new incomplete hour
- **1:05 PM** - Volume spike detected in BTC → **Alert sent for BTC only**
- **1:14 PM** - ETH volume changes → **Alert sent for ETH only**  
- **1:30 PM** - SOL volume changes → **Alert sent for SOL only**
- **2:00 PM** - New hour starts, state resets

**Key Point**: Each asset alerts **independently** when it crosses the threshold. You won't get batched alerts for all three together.

---

## How It Works (Detailed)

### Data Flow

```
Binance API → Fetch OHLCV Data → Compare Consecutive Periods → Volume Analysis → Alert Trigger → Telegram
```

### Alert Generation Process

1. **Every 5 minutes**, bot fetches OHLCV candle data from Binance
2. **Fetch Strategy** (Real-time monitoring with incomplete candles):
   - Fetches 3 candles from Binance
   - Uses: **Previous CLOSED candle** vs **Current INCOMPLETE candle** (real-time data)
   - This allows detection of volume spikes WITHOUT waiting for candle to close
3. **For 1h**: Compares previous complete hour vs current incomplete hour (updates every 5 min)
4. **For 24h**: Compares previous complete day vs current incomplete rolling 24h (updates every 5 min)
5. **Calculates**: Volume change percentage: `((current_incomplete - previous_closed) / previous_closed) × 100`
6. **Compares**: If `|change|` meets threshold (1h: ±30%, 24h: ±50%), generates alert
7. **Prevents Duplicates**: Uses open_time to avoid re-alerting on same incomplete candle within same period
8. **Independent Alerts**: Each asset (BTC, ETH, SOL) alerts separately when it crosses threshold
9. **Sends**: Instant Telegram notification with formatted data

**Why this works better**: Real-time comparison detects volume changes immediately, not after candle closes. Each asset can alert independently throughout the hour.

### Alert Format

```
🚨 BTCUSDT VOLUME ALERT 📈

⏱️ Timeframe: 1h
💹 Current Price: $42,530.50
📊 Volume Change: +35.2%

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

## Critical Fix: Incomplete Candle Handling

**Latest Update (v1.1)**: Fixed issue where bot was comparing incomplete current candles to complete previous candles.

### The Problem
- Binance API returns the current incomplete candle as the newest data point
- Comparing incomplete candle (1 min old, partial data) to complete candle (60 min old, full data)
- Result: False alerts showing -95%, -97% volume changes

### The Solution  
- Fetch 3 candles instead of 2
- Discard the current incomplete candle
- Compare only 2 COMPLETE/CLOSED candles
- Result: Realistic alerts like +63.51% volume changes

### Impact
✅ All false alerts eliminated
✅ Only real market movements detected
✅ Accurate ±30% and ±50% threshold comparisons

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

