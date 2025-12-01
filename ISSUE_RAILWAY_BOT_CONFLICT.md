# Issue: Railway Bot Instance Conflicting with Local Development

## Problem

The local bot is receiving **HTTP 409 "Conflict"** errors from Telegram API with message:
```
"Conflict: terminated by other getUpdates request; make sure that only one bot instance is running"
```

This indicates that **another bot instance is actively polling the same Telegram bot token**.

## Root Cause

During earlier attempts to deploy on Railway, a bot instance was deployed and is still running on Railway servers. The Railway instance and the local bot are competing for messages from the same token.

- **Railway instance**: Still actively polling Telegram API at railway app
- **Local instance**: PID 86445, trying to poll same token

Result: Updates come in, Railway instance consumes them, local bot gets 409 conflicts.

## Solutions

### Option 1: Stop Railway Instance (Recommended)

**Steps:**
1. Go to https://railway.app
2. Log in to your account
3. Find the "volume-alert-bot" project
4. Click on the project
5. Click "Settings" → "Danger Zone" → "Delete project"
6. Confirm deletion

After Railway is deleted, the local bot will work immediately.

### Option 2: Create New Bot Token (Alternative)

If you want to keep Railway or access it later:

1. Go to Telegram @BotFather
2. Send `/newbot`
3. Create a new bot (name it "Volume Alert Local" or similar)
4. Get the new token
5. Update `.env` file:
   ```bash
   TELEGRAM_BOT_TOKEN=YOUR_NEW_TOKEN_HERE
   ```
6. Restart the bot
7. Add new bot to test group `-1003269114897`

## Testing

Once Railway is stopped, test with:

```bash
# Send a test message to bot in group
curl -X POST "https://api.telegram.org/bot$TOKEN/sendMessage" \
  -H "Content-Type: application/json" \
  -d '{"chat_id": -1003269114897, "text": "/status @Mudrex_Volume_bot"}'

# Check logs for message reception
tail -20 logs/volume_bot.log | grep "📨"
```

Expected output:
```
📨 Message from YourName (ID: 395803228) in chat -1003269114897 (type: supergroup): /status @Mudrex_Volume_bot
```

## Current Bot State

- **Local Bot PID**: 86445
- **Running**: ✅ Yes (with caffeinate)
- **Bot Token**: 8218195916:AAGwDqqpn3SQ4wrTPb1vVO0ec_14
- **Test Group**: -1003269114897
- **User ID**: 395803228 (@DecentralizedJM)
- **Issue**: 409 Conflicts due to Railway instance

## Features Implemented & Ready

✅ Per-asset cooldown (3h for 1h, 24h for 24h)  
✅ Volume alerts (≥75% increase both timeframes)  
✅ Alert persistence (prevents duplicates after restart)  
✅ Command handling (/start, /stop, /status)  
✅ Telegram timeout improvements  
✅ Conflict detection and offset reset  

All features will work once Railway instance is stopped.
