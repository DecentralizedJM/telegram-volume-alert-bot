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
- **Smart Alert Queue**: 10-minute gap between alerts to prevent spam (first-alert-first-served basis)
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

## Smart Alert Queue System

### How It Works

To prevent alert spam when multiple assets trigger at similar times, the bot implements a **10-minute queue system**:

**Rule: No two alerts within 10 minutes**

1. **First Alert**: Sent immediately (t=0)
   - "🚨 BTC volume +45%" → Sent now
   - `last_alert_timestamp = 0`

2. **Subsequent Alerts**: Queued if within 10 minutes
   - "🚨 ETH volume -35%" (t=30s) → Queued (not sent yet)
   - "🚨 SOL volume +60%" (t=45s) → Queued (not sent yet)

3. **After 10 Minutes**: Next queued alert is released
   - At t=600s → "🚨 ETH volume -35%" → Sent
   - `last_alert_timestamp = 600`

4. **10 Minutes Later**: Next alert from queue
   - At t=1200s → "🚨 SOL volume +60%" → Sent
   - `last_alert_timestamp = 1200`

### Timeline Example

```
Time (min:sec)  Event                           Action
───────────────────────────────────────────────────────────
00:00           BTC volume drops -64%          📤 Sent (first)
00:30           ETH volume drops -73%          📥 Queued (9:30 min wait)
00:45           SOL volume drops -66%          📥 Queued (9:15 min wait)
10:00           (10 min elapsed)               📤 ETH alert sent (queue: 1 pending)
20:00           (another 10 min)               📤 SOL alert sent (queue: 0 pending)
```

### Benefits

✅ **Prevents Alert Fatigue**: Max 1 notification per 10 minutes
✅ **Fair Queue**: FIFO (First-In-First-Out) - alerts processed in trigger order
✅ **No Lost Alerts**: All alerts are queued and will eventually be sent
✅ **Configurable**: Change `ALERT_QUEUE_GAP_SECONDS` in `config.py` to adjust gap

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

The bot compares **consecutive closed candles** to detect significant volume changes:

**1-Hour Timeframe (1h)**
- Compares: Most recent closed hour vs Previous closed hour
- Threshold: ±30% volume change
- Updates: Every 5 minutes with latest market data
- Example: If 12-1 PM hour had 75M volume and 1-2 PM hour has 27M volume → -64% alert

**24-Hour Rolling Window (24h)**
- Compares: Most recent closed day vs Previous closed day
- Threshold: ±50% volume change
- Updates: Every 5 minutes with latest volume data

### Why Consecutive Closed Candles?

**Why not use the current incomplete candle?**
- Binance returns 3 candles: [older_closed, newer_closed, current_incomplete]
- The incomplete candle [2] has almost no data (e.g., 4K trades vs 135K in complete hours)
- Comparing to incomplete = unrealistic percentage changes
- Solution: Use [0] and [1] which are both complete and give realistic comparisons

**Example:**
- [0] = 75.6M volume (complete hour, 135K trades)
- [1] = 27.0M volume (complete hour, 61K trades)
- [2] = 0.7M volume (incomplete, only 4.3K trades) ← Skip this!

Change [1] vs [0] = -64.21% ✓ (realistic)
Change [2] vs [1] = -97.40% ✗ (unrealistic, incomplete data)

### Detection Formula

```
Volume Change % = ((Current Closed Volume - Previous Closed Volume) / Previous Closed Volume) × 100

Alert Triggers When:
- 1h:  |Volume Change %| ≥ 30%
- 24h: |Volume Change %| ≥ 50%
```

### Independent Per-Asset Alerting

✅ **Each asset checks independently and alerts when it crosses the threshold:**

Example Timeline (every 5-minute check):
- **1:00 PM** - New hour closes. Bot now compares 12-1 PM (75M) vs 1-2 PM (27M)
- **1:05 PM** - Check 1: BTC -64% ≥ ±30% → **BTC Alert sent**
- **1:10 PM** - Check 2: BTC still -64% (same closed hour) → No duplicate
- **1:15 PM** - Check 3: ETH -73% ≥ ±30% → **ETH Alert sent** (independent)
- **1:20 PM** - Check 4: SOL -66% ≥ ±30% → **SOL Alert sent** (independent)
- **2:00 PM** - New hour closes. State resets for next comparison
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
2. **Fetch Strategy** (Using consecutive closed candles):
   - Fetches 3 candles from Binance in chronological order
   - Discards incomplete candle [2] (has almost no trading data)
   - Uses candles [0] and [1]: Both are CLOSED/COMPLETE candles
   - This ensures realistic and meaningful volume comparisons
3. **For 1h**: Compares 2 most recent closed hourly candles
4. **For 24h**: Compares 2 most recent closed daily candles
5. **Calculates**: Volume change percentage: `((current_closed - previous_closed) / previous_closed) × 100`
6. **Compares**: If `|change|` meets threshold (1h: ±30%, 24h: ±50%), generates alert
7. **Independent Alerts**: Each asset (BTC, ETH, SOL) checks independently and can trigger separate alerts
8. **Sends**: Instant Telegram notification to monitoring group with formatted data

**Important**: Crypto markets are 24/7. Volume changes at any hour (even off-hours) are real market movements and should trigger alerts.
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

