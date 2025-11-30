# Telegram Volume Alert Bot

Real-time cryptocurrency volume alert system for Telegram. Monitors BTC, ETH, and SOL for significant volume movements across multiple timeframes and sends instant notifications.

**Created for Mudrex™ | Proprietary Software**

---

## Features

- **Multi-Asset Monitoring**: BTC, ETH, SOL (easily extensible to other assets)
- **Independent Timeframe Checking**:
  - **1-Hour**: ±50% volume change detection (max 3 alerts per day per asset)
  - **24-Hour**: ±75% volume change detection (max 1 alert per day per asset)
- **Period-Based Locking**: Once an alert triggers, it's locked until the next period starts (resets daily for both timeframes)
- **Consecutive Period Comparison**: Compares volume between consecutive closed periods
- **Real-Time Alerts**: Instant Telegram notifications with price and volume data
- **Owner Control**: Start/stop monitoring with Telegram commands
- **Smart Alert Queue**: 10-minute gap between alerts to prevent spam (FIFO queue system)
- **Persistent Monitoring**: Continuous market surveillance (checks every 5 minutes)
- **Professional Formatting**: Clean, emoji-enhanced Telegram messages with direction and metrics
- **Optional Telegram Topics**: Route alerts to specific topics or keep in general group chat

---

## Quick Start

### Prerequisites

- Python 3.8+
- Telegram Bot (created via @BotFather)
- Telegram group (for receiving alerts)

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
TELEGRAM_TOPIC_ID=your_topic_id_here  # Optional: for Telegram Topics
```

2. **Run the bot**:
```bash
python3 volume_alert_bot.py
```

#### Optional: Telegram Topics Support

Send all alerts to a specific **Telegram Topic** in your group chat:

```
TELEGRAM_TOPIC_ID=12345
```

📖 **See [TELEGRAM_TOPICS_QUICK_START.md](./TELEGRAM_TOPICS_QUICK_START.md) for setup instructions**

Or read the full guide: [TELEGRAM_TOPICS.md](./TELEGRAM_TOPICS.md)

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
• 1h Threshold: ±50% volume change (max 3/day per asset)
• 24h Threshold: ±75% volume change (max 1/day per asset)
• Check Interval: 5 minutes
• Alert Queue Gap: 10 minutes
```

---

**Note**: `/start` and `/stop` are owner-only commands (defined by `TELEGRAM_OWNER_CHAT_ID`). Anyone can use `/status`.

---

## Smart Alert Queue System

### How It Works

To prevent alert spam and maintain professional alert delivery, the bot implements a **period-based locking with 10-minute queue system**:

**Alert Limits per Day:**
- **1-Hour Timeframe**: Maximum 3 alerts per asset per day (resets daily at midnight)
- **24-Hour Timeframe**: Maximum 1 alert per asset per day (resets daily at midnight)

**Queue Spacing Rule: Minimum 10 minutes between alert deliveries**

1. **First Alert**: Sent immediately (t=0)
   - "� BTC 1h: -64.21% volume" → Sent now
   - Count: 1/3, Period Lock: ON

2. **Subsequent Alerts** (within 10 minutes): Queued
   - "� ETH 1h: +73.56% volume" (t=30s) → Queued (will send in 9:30)
   - "� SOL 1h: -66.43% volume" (t=45s) → Queued (will send in 9:15)

3. **After 10 Minutes**: Next queued alert is released
   - At t=600s → "� ETH 1h: +73.56% volume" → Sent
   - Count: 1/3, Period Lock: ON

4. **10 Minutes Later**: Next alert from queue
   - At t=1200s → "� SOL 1h: -66.43% volume" → Sent
   - Count: 1/3, Period Lock: ON

### Timeline Example

```
Time (min:sec)  Symbol  Event                   Action                    Queue Size
────────────────────────────────────────────────────────────────────────
00:00           BTC     -64% volume             📤 Sent (first)            0
00:30           ETH     +73% volume             📥 Queued (9:30 wait)       1
00:45           SOL     -66% volume             📥 Queued (9:15 wait)       2
10:00           ETH     (10 min elapsed)        📤 Dequeued & sent          1
20:00           SOL     (another 10 min)        📤 Dequeued & sent          0
```

### Period-Based Locking

Once an alert triggers for a symbol/timeframe:
- **Lock is activated** for that period
- **No more alerts** can be sent for that symbol/timeframe until the period changes
- **Period resets** automatically:
  - **1h**: Daily at midnight UTC (allows up to 3 alerts per day)
  - **24h**: Daily at midnight UTC (allows up to 1 alert per day)

**Example**:
- 02:15 AM: BTC 1h alert sent (-64%), lock ON, count 1/3
- 02:20 AM: Another -50% volume for BTC 1h detected → **Blocked** (already alerted this hour)
- 03:00 AM: New hour starts → lock resets, counter resets to 0
- 03:05 AM: Same -50% pattern detected → **Can send again** (new period)

### Benefits

✅ **Prevents Alert Fatigue**: Max 1 notification per 10 minutes
✅ **Fair Queue**: FIFO (First-In-First-Out) - alerts processed in trigger order
✅ **Limits Per Period**: Can't exceed 3 alerts/hour or 1 alert/day per asset
✅ **No Lost Alerts**: All alerts are queued and will eventually be sent
✅ **No Duplicate Alerts**: Period locking prevents multiple alerts for same movement
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
    "1h": 50,       # Alert on ±50% hourly volume change
    "24h": 75       # Alert on ±75% daily volume change
}

# Check interval in seconds (5 minutes)
CHECK_INTERVAL = 300

# Alert queue gap in seconds (10 minutes minimum between alerts)
ALERT_QUEUE_GAP_SECONDS = 600
```

---

## Volume Detection Logic

### How It Works

The bot independently checks each symbol and timeframe combination to detect significant volume changes:

**1-Hour Timeframe (1h)**
- Compares: Most recent closed hour vs Previous closed hour
- Threshold: ±50% volume change
- Max Alerts: 3 per asset per day (resets daily at midnight)
- Updates: Every 5 minutes with latest market data
- Example: Hour 1-2 PM has 75M volume, Hour 2-3 PM has 27M volume → -64% alert

**24-Hour Timeframe (24h)**
- Compares: Most recent closed day vs Previous closed day
- Threshold: ±75% volume change
- Max Alerts: 1 per asset per day (resets daily at midnight)
- Updates: Every 5 minutes with latest volume data
- Example: Day 1 has 2B volume, Day 2 has 525M volume → -73.75% alert

### Independent Checking

Each symbol × timeframe combination is checked **independently**:
- BTC 1h and BTC 24h are checked separately
- ETH 1h and SOL 1h are independent of each other
- No "dual requirement" - each triggers its own alerts
- Alerts queue and throttle independently per period

### Why Consecutive Closed Periods?

**Why compare consecutive closed periods only?**
- Binance returns 3 candles: [older_closed, newer_closed, current_incomplete]
- The incomplete candle has almost no data (e.g., 4K trades vs 135K in complete periods)
- Comparing to incomplete = unrealistic percentage changes (-95% false positives)
- Solution: Use [0] and [1] which are both complete and complete for realistic comparisons

### Alert Counter Example

**Symbol: BTC, Timeframe: 1h (Daily Limit)**
```
Day 1 - 02:15 AM - Alert #1: -64% volume (counter shows: 1/3) 🔐 Lock ON
Day 1 - 02:20 AM - Another -50% detected → BLOCKED (already alerted today)
Day 1 - 02:55 AM - Another +45% detected → BLOCKED (already alerted today)
Day 1 - 23:59 PM - Still blocked, still at 1/3 alerts for the day
Day 2 - 00:00 AM - New day starts → Lock releases, counter resets to 0/3
Day 2 - 01:05 AM - Alert #1 (new day): +45% volume (counter shows: 1/3) 🔐 Lock ON
```

**Symbol: ETH, Timeframe: 24h (Daily Limit)**
```
Day 1 - 14:30 - Alert #1: +85% volume (counter shows: 1/1) 🔐 Lock ON
Day 1 - 15:00 - Another +75% detected → BLOCKED (daily limit reached)
Day 1 - 23:59 - Still blocked, still at 1/1 alert for the day
Day 2 - 00:00 - New day starts → Lock releases, counter resets to 0/1
Day 2 - 08:20 - Alert #1 (new day): -80% volume (counter shows: 1/1) 🔐 Lock ON
```

**Example Candle Data:**
- [0] = 75.6M volume (complete period, 135K trades)
- [1] = 27.0M volume (complete period, 61K trades)
- [2] = 0.7M volume (incomplete, only 4.3K trades) ← Skip this!

Change [1] vs [0] = -64.21% ✓ (realistic)
Change [2] vs [1] = -97.40% ✗ (unrealistic, incomplete data)

### Detection Formula

```
Volume Change % = ((Current Closed Volume - Previous Closed Volume) / Previous Closed Volume) × 100

Alert Triggers When:
- 1h:  |Volume Change %| ≥ 50%  (max 3 alerts per day per asset)
- 24h: |Volume Change %| ≥ 75% (max 1 alert per day per asset)
```

Each timeframe is checked **independently**. No "dual requirement" - each alert triggers separately.

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

