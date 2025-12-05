# Conditional Alert Routing - Technical Deep Dive

## Overview

The bot implements **conditional alert routing**: alerts are sent to a Telegram Topic ONLY if `TELEGRAM_TOPIC_ID` is configured. Otherwise, alerts go directly to the group chat.

---

## Implementation

### 1. Configuration Parsing (volume_alert_bot.py)

```python
class VolumeAlertBot:
    def __init__(self):
        # ... other initialization ...
        
        # Parse TELEGRAM_TOPIC_ID from environment
        # If not set or empty string, will be None
        self.telegram_topic_id = os.getenv("TELEGRAM_TOPIC_ID")
        
        # Initialize Telegram client with optional topic_id
        self.telegram = TelegramClient(
            bot_token=self.telegram_token,
            chat_id=self.telegram_chat_id,
            topic_id=int(self.telegram_topic_id) if self.telegram_topic_id else None
            #        ↑ Convert to int ONLY if it exists, else None ↑
        )
```

**Key Point**: `topic_id` is either an integer or `None` (never sent if not configured)

---

### 2. Telegram Client Initialization (telegram_client.py)

```python
class TelegramClient:
    def __init__(self, bot_token: str, chat_id, topic_id: Optional[int] = None):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.topic_id = topic_id  # None if not configured
        
        # Log configuration status
        if self.topic_id:
            logger.info(f"✅ Telegram topic configured: Topic ID {self.topic_id}")
        else:
            logger.info("ℹ️ No Telegram topic configured - alerts will go to group chat")
```

**Startup Logs**:
- With topic: `✅ Telegram topic configured: Topic ID 52310`
- Without topic: `ℹ️ No Telegram topic configured - alerts will go to group chat`

---

### 3. Conditional Routing (telegram_client.py send_message method)

```python
async def send_message(self, chat_id: int, text: str, topic_id: Optional[int] = None) -> bool:
    """
    Send message with conditional routing to topic or general chat
    """
    try:
        # Build base payload (required fields)
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        
        # CONDITIONAL ROUTING LOGIC
        # Use provided topic_id override, fall back to self.topic_id
        effective_topic_id = topic_id or self.topic_id
        
        if effective_topic_id:
            # ✅ Topic is configured
            # Add message_thread_id to route to specific topic
            payload["message_thread_id"] = effective_topic_id
            logger.debug(f"Message sent to chat {chat_id} (topic {effective_topic_id})")
        else:
            # ✅ No topic configured
            # Send WITHOUT message_thread_id parameter
            # This sends to general chat/channel
            logger.debug(f"Message sent to chat {chat_id} (general chat)")
        
        # Send to Telegram API
        response = requests.post(
            f"{self.api_url}/sendMessage",
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            return True
        else:
            logger.error(f"Telegram error: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return False
```

---

## Decision Tree

```
Alert Triggered
    ↓
Check TELEGRAM_TOPIC_ID
    ↓
    ├─ Is it SET? (e.g., 52310)
    │   ↓
    │   Add to payload: "message_thread_id": 52310
    │   ↓
    │   Message goes to TOPIC 52310 ✅
    │
    └─ Is it EMPTY or NOT SET? (None)
        ↓
        Don't add message_thread_id parameter
        ↓
        Message goes to GENERAL CHAT ✅
```

---

## Payload Differences

### With Topic (TELEGRAM_TOPIC_ID=52310)

```json
{
  "chat_id": -1003269114897,
  "text": "🚨 BTCUSDT VOLUME ALERT 📈\n⏱️ Timeframe: 1h\n...",
  "parse_mode": "HTML",
  "message_thread_id": 52310  ← ROUTED TO TOPIC
}
```

**Result**: Alert appears in topic 52310 thread only

### Without Topic (TELEGRAM_TOPIC_ID empty or not set)

```json
{
  "chat_id": -1003269114897,
  "text": "🚨 BTCUSDT VOLUME ALERT 📈\n⏱️ Timeframe: 1h\n...",
  "parse_mode": "HTML"
}
```

**Result**: Alert appears in general group chat

---

## Configuration Examples

### Example 1: With Topic

**.env**:
```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=-1003269114897
TELEGRAM_OWNER_CHAT_ID=your_chat_id
TELEGRAM_TOPIC_ID=52310
```

**Behavior**:
- ✅ TELEGRAM_TOPIC_ID = 52310 (integer)
- ✅ effective_topic_id = 52310
- ✅ message_thread_id = 52310 added to payload
- ✅ Alert goes to topic 52310 ONLY
- ✅ General chat has no alerts

**Logs**:
```
✅ Telegram topic configured: Topic ID 52310
Message sent to chat -1003269114897 (topic 52310)
```

---

### Example 2: Without Topic (Empty String)

**.env**:
```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=-1003269114897
TELEGRAM_OWNER_CHAT_ID=your_chat_id
TELEGRAM_TOPIC_ID=
```

**Behavior**:
- ✅ TELEGRAM_TOPIC_ID = "" (empty string)
- ✅ int("") would fail, so condition is False
- ✅ effective_topic_id = None
- ✅ message_thread_id NOT added to payload
- ✅ Alert goes to general group chat

**Logs**:
```
ℹ️ No Telegram topic configured - alerts will go to group chat
Message sent to chat -1003269114897 (general chat)
```

---

### Example 3: Without Topic (Not Set at All)

**.env**:
```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=-1003269114897
TELEGRAM_OWNER_CHAT_ID=your_chat_id
# TELEGRAM_TOPIC_ID is not in .env
```

**Behavior**:
- ✅ TELEGRAM_TOPIC_ID = None (os.getenv returns None)
- ✅ int(None) would fail, so condition is False
- ✅ effective_topic_id = None
- ✅ message_thread_id NOT added to payload
- ✅ Alert goes to general group chat

**Same as Example 2**: Alerts go to general chat

---

## Runtime Verification

### Check Topic Configuration

```bash
# View bot logs
tail -20 logs/volume_bot.log

# Look for one of these messages:
# ✅ Telegram topic configured: Topic ID 52310
# ℹ️ No Telegram topic configured - alerts will go to group chat
```

### Verify Alert Routing

**With Topic Set**:
1. Wait for volume alert
2. Alert appears in topic 52310 thread
3. General chat has no new alerts

**Without Topic**:
1. Wait for volume alert
2. Alert appears in general group chat
3. No topic specified

---

## Advanced: Per-Symbol Routing

If you want different symbols to go to different topics, you can override:

```python
# In volume_alert_bot.py, modify send_alert_formatted():

async def send_alert_formatted(self, alert: dict) -> bool:
    symbol = alert["symbol"]
    
    # Route to different topics by symbol
    if symbol == "BTCUSDT":
        override_topic = 52310  # BTC topic
    elif symbol == "ETHUSDT":
        override_topic = 52311  # ETH topic
    else:
        override_topic = self.telegram.topic_id  # Use default
    
    # Send with override
    return await self.telegram.send_message(
        self.telegram.chat_id,
        message,
        topic_id=override_topic  # ← Override routing per symbol
    )
```

This allows:
- BTC alerts → Topic 52310
- ETH alerts → Topic 52311
- Other alerts → Default topic (or general if no default)

---

## Safety & Error Handling

### Graceful Degradation

The routing logic is safe:
- ✅ If TELEGRAM_TOPIC_ID is invalid: Fails to convert to int, falls back to general chat
- ✅ If topic doesn't exist: Telegram API returns error, message NOT sent (prevents noise)
- ✅ If no topic specified: Sends to general chat (always works)

### Configuration Validation

```python
# Safe parsing from .env
topic_id_str = os.getenv("TELEGRAM_TOPIC_ID")

if topic_id_str:
    try:
        topic_id = int(topic_id_str)
        # Use topic_id
    except ValueError:
        logger.warning(f"Invalid TELEGRAM_TOPIC_ID: {topic_id_str}, using general chat")
        topic_id = None
else:
    # Empty or not set
    topic_id = None
```

---

## Summary

### Conditional Routing Rules

| Config | Action | Result |
|--------|--------|--------|
| TELEGRAM_TOPIC_ID=52310 | Add message_thread_id: 52310 | Alert → Topic 52310 |
| TELEGRAM_TOPIC_ID= | Don't add message_thread_id | Alert → General Chat |
| TELEGRAM_TOPIC_ID not set | Don't add message_thread_id | Alert → General Chat |

### Key Files

- **telegram_client.py** (lines 13, 25, 33-34, 70-110): Conditional routing logic
- **volume_alert_bot.py**: Parse TELEGRAM_TOPIC_ID and pass to TelegramClient

### Configuration

- **.env.example**: Documents TELEGRAM_TOPIC_ID with examples
- **README.md**: Notes optional Topics feature
- **TELEGRAM_TOPICS.md**: Complete guide with configuration examples

---

