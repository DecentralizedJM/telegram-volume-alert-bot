# Railway Deployment Guide

## Quick Deploy

1. Connect your GitHub repo to Railway
2. Set environment variables in Railway dashboard:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
   - `TELEGRAM_TOPIC_ID` (optional)
   - `TELEGRAM_OWNER_CHAT_ID`

3. Deploy!

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | ✅ | Bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | ✅ | Target group/chat ID |
| `TELEGRAM_TOPIC_ID` | ❌ | Topic ID for forum groups |
| `TELEGRAM_OWNER_CHAT_ID` | ✅ | Your Telegram user ID (for /start, /stop) |

## Files Added for Railway

- `railway.json` - Railway configuration
- `railway.toml` - Alternative Railway config
- `.python-version` - Python version (3.11)

## Notes

- Bot runs continuously with auto-restart on failure
- Logs available in Railway dashboard
- No ports exposed (bot uses polling, not webhooks)
