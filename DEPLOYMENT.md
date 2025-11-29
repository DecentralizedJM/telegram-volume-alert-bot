# Deployment Guide

This guide covers deploying the Telegram Volume Alert Bot to services like Railway, Heroku, Render, or any cloud platform.

## Prerequisites

- Python 3.8+
- Telegram Bot Token (from @BotFather)
- Environment variables configured

## Local Setup

### 1. Clone the Repository

```bash
git clone https://github.com/DecentralizedJM/telegram-volume-alert-bot.git
cd telegram-volume-alert-bot
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file:

```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
TELEGRAM_OWNER_CHAT_ID=your_owner_chat_id_here
```

**How to get these values:**

1. **TELEGRAM_BOT_TOKEN**: 
   - Chat with @BotFather on Telegram
   - Send `/newbot`
   - Follow prompts and copy the token

2. **TELEGRAM_CHAT_ID**: 
   - Add your bot to a group chat
   - Send a message
   - Visit: `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
   - Find `"chat":{"id":...}` (negative number for groups)

3. **TELEGRAM_OWNER_CHAT_ID**: 
   - Your personal user ID (positive number)
   - Get it from the same getUpdates URL

### 5. Run Locally

```bash
python3 volume_alert_bot.py
```

## Deployment to Railway

### Step 1: Prepare Repository

```bash
git add .
git commit -m "Prepare for Railway deployment"
git push
```

### Step 2: Create Railway Account

1. Go to [railway.app](https://railway.app)
2. Sign up with GitHub
3. Create a new project

### Step 3: Connect GitHub Repository

1. Click "New" → "GitHub Repo"
2. Select your repository
3. Railway will auto-detect Python

### Step 4: Configure Environment Variables

In Railway Dashboard:

1. Go to your project
2. Click "Variables"
3. Add these environment variables:
   ```
   TELEGRAM_BOT_TOKEN=your_token
   TELEGRAM_CHAT_ID=your_chat_id
   TELEGRAM_OWNER_CHAT_ID=your_owner_id
   ```

### Step 5: Set Start Command

In Railway, set the start command:

```bash
python volume_alert_bot.py
```

Or create a `Procfile`:

```
worker: python volume_alert_bot.py
```

### Step 6: Deploy

Railway will automatically deploy when you push to GitHub.

---

## Deployment to Other Platforms

### Heroku

```bash
heroku login
heroku create your-app-name
git push heroku main
heroku config:set TELEGRAM_BOT_TOKEN=your_token
heroku config:set TELEGRAM_CHAT_ID=your_chat_id
heroku config:set TELEGRAM_OWNER_CHAT_ID=your_owner_id
```

### Docker Deployment

```bash
# Build image
docker build -t volume-alert-bot .

# Run container
docker run -e TELEGRAM_BOT_TOKEN=your_token \
           -e TELEGRAM_CHAT_ID=your_chat_id \
           -e TELEGRAM_OWNER_CHAT_ID=your_owner_id \
           volume-alert-bot
```

Or with docker-compose:

```bash
# Configure .env file
docker-compose up -d
```

---

## Monitoring

### Check Bot Status

```bash
# View logs
tail -f logs/volume_bot.log

# Check running processes
ps aux | grep volume_alert_bot
```

### Useful Commands

Clear Telegram queue (prevents message spam):

```bash
python3 clear_queue.py
```

---

## Troubleshooting

### Bot not responding

1. Verify environment variables are set correctly
2. Check Telegram token is valid
3. Run: `python3 clear_queue.py` to clear message queue
4. Restart the bot

### No alerts being sent

1. Verify `TELEGRAM_CHAT_ID` is correct (group ID must be negative)
2. Check Binance API is accessible
3. Verify volume threshold in `config.py`

### Too many messages

1. Run `clear_queue.py` to clear old messages
2. Reduce `CHECK_INTERVAL` in `config.py`
3. Adjust `VOLUME_THRESHOLD` in `config.py`

---

## Configuration

Edit `config.py` to customize:

```python
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]  # Cryptocurrencies to monitor
TIMEFRAMES = {"1h": 60, "12h": 720, "24h": 1440}  # Time intervals
VOLUME_THRESHOLD = 30  # Alert if volume change > 30%
CHECK_INTERVAL = 300  # Check every 5 minutes (in seconds)
MAX_ALERTS_PER_SYMBOL = 3  # Max alerts per symbol per cycle
```

---

## Files Included

### Core Files

- `volume_alert_bot.py` - Main bot orchestrator
- `binance_fetcher.py` - Binance API integration
- `volume_detector.py` - Volume analysis logic
- `telegram_client.py` - Telegram API client
- `config.py` - Configuration settings
- `command_handler.py` - Command utilities

### Deployment Files

- `requirements.txt` - Python dependencies
- `Dockerfile` - Docker configuration
- `docker-compose.yml` - Docker Compose setup
- `.env.example` - Environment template
- `docker.sh` - Docker helper script

### Utilities

- `clear_queue.py` - Clear Telegram message queue
- `test_bot.py` - Test suite

### Documentation

- `README.md` - Project overview
- `DEPLOYMENT.md` - This file
- `LICENSE` - Proprietary license

---

## Support

For issues or questions, visit: [GitHub Issues](https://github.com/DecentralizedJM/telegram-volume-alert-bot/issues)

---

**Created for Mudrex™** | Copyright © 2025 @DecentralizedJM
