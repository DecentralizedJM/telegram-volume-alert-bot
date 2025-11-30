# Telegram Topics - Quick Start

## ⚠️ IMPORTANT: Conditional Alert Routing

**Alerts will ONLY go to a topic IF you configure TELEGRAM_TOPIC_ID**

- ✅ **With Topic ID set**: Alerts → Specific Topic
- ✅ **Without Topic ID (empty)**: Alerts → Group Chat (General Channel)

This means you control where alerts appear!

### 1️⃣ Enable Topics in Telegram Group
- Group Settings → Topics → Toggle ON
- Create "📊 Volume Alerts" topic (optional)

### 2️⃣ Get Topic ID
- Open the topic
- Click info → Note the Topic ID (integer like `12345`)

### 3️⃣ Update `.env`
```bash
TELEGRAM_TOPIC_ID=12345
```

### 4️⃣ Restart Bot
```bash
pkill -9 -f volume_alert_bot.py && sleep 2 && nohup caffeinate -s python3 volume_alert_bot.py > logs/volume_bot.log 2>&1 &
```

### ✅ Done!
Alerts now go to your topic!

---

## Common Commands

### Find Topic ID
```bash
# Check bot logs - it will show received topic ID
tail -20 logs/volume_bot.log | grep -i thread
```

### Verify Setup
```bash
# Send a test message
python3 -c "
import asyncio
from telegram_client import TelegramClient

async def test():
    client = TelegramClient('YOUR_TOKEN', YOUR_CHAT_ID, topic_id=YOUR_TOPIC_ID)
    await client.send_message('Test message to topic!')

asyncio.run(test())
"
```

### Disable Topics (Send to General Chat)
```bash
# Remove TELEGRAM_TOPIC_ID from .env
# Or set it to empty/0
TELEGRAM_TOPIC_ID=
```

---

## Topic ID Formats

| Format | Valid? | Example |
|--------|--------|---------|
| Integer | ✅ Yes | `12345` |
| Negative | ❌ No | `-12345` |
| String | ❌ No | `"12345"` |
| Float | ❌ No | `123.45` |

---

## Troubleshooting Table

| Issue | Solution |
|-------|----------|
| Alerts not in topic | Check topic ID in .env, restart bot |
| Bot has no access to topic | Make bot admin or topic moderator |
| Topic ID not found | Use Telegram app, click info icon |
| Permission denied error | Add bot to topic/group again |

---

## See Also
- Full documentation: `TELEGRAM_TOPICS.md`
- Bot setup: `README.md`
- Configuration: `.env.example`

