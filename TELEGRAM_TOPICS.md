# Telegram Topics Support

## ⚠️ IMPORTANT: How Alert Routing Works

**Alerts will ONLY be routed to a topic IF you set TELEGRAM_TOPIC_ID**

### Alert Routing Rules:
- **TELEGRAM_TOPIC_ID is SET** (e.g., `52310`):
  - ✅ All alerts go to that specific topic
  - ✅ Group chat remains clean (no alerts in general chat)

- **TELEGRAM_TOPIC_ID is EMPTY** (or not set):
  - ✅ All alerts go directly to group chat (general channel)
  - ✅ No topic filtering applied

This gives you complete control over where your alerts appear!

---

## Overview

The Volume Alert Bot now supports sending alerts to specific **Telegram Topics** when your group has topics enabled.

Topics allow you to organize conversations in a supergroup into separate threads. For example:
- "BTC Alerts" topic
- "ETH Alerts" topic  
- "General Discussion" topic

## How to Use

### 1. Enable Topics in Your Telegram Group

1. Go to your Telegram group settings
2. Click **"Edit Group"** → **"Topics"**
3. Toggle **"Topics"** to ON
4. Telegram will create a default "General" topic

### 2. Create Alert Topic (Optional)

1. Click **"+" button** to create a new topic
2. Name it something like "📊 Volume Alerts"
3. Note the **Topic ID** (visible in the topic details)

### 3. Find Your Topic ID

**Method A: In Telegram (UI)**
- Open the topic in your group
- Click the **topic name** at the top
- You'll see the topic ID in the URL or details

**Method B: Using Bot**
```python
# Send any message to the topic from the bot
# Check the logs to see the message_thread_id
```

### 4. Configure Your .env File

Add the `TELEGRAM_TOPIC_ID` to your `.env`:

```bash
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
TELEGRAM_OWNER_CHAT_ID=your_owner_id_here
TELEGRAM_TOPIC_ID=12345  # Replace with your topic ID
```

**OR leave it empty for alerts in general chat:**

```bash
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
TELEGRAM_OWNER_CHAT_ID=your_owner_id_here
TELEGRAM_TOPIC_ID=  # Empty = alerts go to group chat
```

### 5. Restart the Bot

```bash
pkill -9 -f "volume_alert_bot.py"
sleep 2
nohup caffeinate -s python3 volume_alert_bot.py > logs/volume_bot.log 2>&1 &
```

The bot logs will show (if topic is set):
```
✅ Telegram topic configured: Topic ID 12345
```

Or (if topic is not set):
```
ℹ️ No Telegram topic configured - alerts will go to group chat
```

---

## How It Works Internally

### Conditional Routing Logic

The bot checks if `TELEGRAM_TOPIC_ID` is set before routing:

```python
# In telegram_client.py:
effective_topic_id = topic_id or self.topic_id  # None if not configured

if effective_topic_id:
    # Topic is configured - send to topic
    payload["message_thread_id"] = effective_topic_id
else:
    # No topic - send to group chat (general channel)
    # message_thread_id NOT included
```

**This means:**
- ✅ If `TELEGRAM_TOPIC_ID` is set → alert goes to that topic
- ✅ If `TELEGRAM_TOPIC_ID` is empty → alert goes to general group chat
- ✅ Complete control is in your hands via configuration

---

## Configuration Examples

### Send to Specific Topic
```bash
# .env file
TELEGRAM_TOPIC_ID=52310

# Result: All alerts go to topic 52310
```

### Send to Group Chat (No Topic)
```bash
# .env file
TELEGRAM_TOPIC_ID=

# Result: All alerts go to general group chat
```

### Send to Default/General Topic
```bash
# .env file (topic not set)
# Alerts will go to the general chat area
```

### Send to Specific Topic
````

### Send to Different Topics by Symbol (Advanced)

If you want different symbols to go to different topics, you can modify the code:

**Example: BTC alerts to one topic, ETH to another**

```python
# In volume_alert_bot.py, modify send_alert_formatted():

async def send_alert_formatted(self, alert: dict) -> bool:
    symbol = alert["symbol"]
    
    # Route to different topics
    if symbol == "BTCUSDT":
        topic_id = 12345  # BTC topic
    elif symbol == "ETHUSDT":
        topic_id = 12346  # ETH topic
    else:
        topic_id = self.telegram.topic_id  # Default topic
    
    # Send with specific topic
    return await self.telegram.send_message(
        self.telegram.chat_id,
        message,
        topic_id=topic_id
    )
```

---

## How It Works

### Current Implementation

When `TELEGRAM_TOPIC_ID` is set:
1. Bot sends ALL alerts to that specific topic
2. The `message_thread_id` parameter is included in API calls
3. Telegram routes the message to the specified topic thread

### Telegram API

The bot uses the Telegram Bot API parameter:
```
message_thread_id: The topic ID (for topics in supergroups)
```

This parameter is optional - if not provided, message goes to general chat.

---

## Troubleshooting

### Topic ID Not Working
- ✅ Verify topics are enabled in your group
- ✅ Check the topic ID is correct (should be an integer)
- ✅ Restart the bot after changing .env
- ✅ Check bot logs for error messages

### Bot Not Sending to Topic
```bash
# Check logs
tail -50 logs/volume_bot.log | grep -i topic

# Should see:
# ✅ Telegram topic configured: Topic ID xxxxx
```

### Topic ID Format
- Should be a **positive integer** (e.g., `12345`)
- Different from chat ID
- Unique per topic in your group

---

## API Reference

### TelegramClient Constructor

```python
TelegramClient(
    bot_token: str,
    chat_id: int,
    topic_id: Optional[int] = None  # NEW: Optional topic ID
)
```

### send_message Method

```python
async def send_message(
    self,
    chat_id: int,
    text: str,
    topic_id: Optional[int] = None  # NEW: Optional override
) -> bool:
    """
    Send message to chat, optionally to a specific topic
    
    Args:
        chat_id: Target chat
        text: Message text
        topic_id: Optional topic ID (overrides self.topic_id)
    """
```

---

## Example Scenarios

### Scenario 1: Basic Topic Setup
```bash
# .env
TELEGRAM_TOPIC_ID=98765

# All alerts → "📊 Volume Alerts" topic
```

### Scenario 2: No Topic (Default Behavior)
```bash
# .env (without TELEGRAM_TOPIC_ID)

# All alerts → General chat area
```

### Scenario 3: Multiple Topics (Custom Code)
Create separate bot instances or modify the routing logic:

```python
# Different bots for different topics:
# - bot1: TELEGRAM_TOPIC_ID=11111 (BTC alerts)
# - bot2: TELEGRAM_TOPIC_ID=22222 (ETH alerts)
```

---

## Questions?

- Topic not receiving alerts? Check bot logs
- Don't know your topic ID? Open topic → click info icon
- Need custom routing? Modify `send_alert_formatted()` method

Happy alert routing! 🎯

