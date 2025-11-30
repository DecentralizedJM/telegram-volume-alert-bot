# Alert Routing Behavior - Key Points

## ⚠️ CRITICAL: Conditional Alert Routing

**Alerts are routed ONLY if TELEGRAM_TOPIC_ID is configured**

### The Rule:

```
IF TELEGRAM_TOPIC_ID is SET (e.g., 52310):
    ✅ Send alerts to that specific topic
    ✅ Alerts appear in the topic thread
    ✅ General group chat stays clean

IF TELEGRAM_TOPIC_ID is EMPTY or NOT SET:
    ✅ Send alerts directly to group chat
    ✅ Alerts appear in general channel
    ✅ No topic filtering applied
```

### Examples:

**Configuration 1: With Topic**
```env
TELEGRAM_TOPIC_ID=52310
```
→ Alerts go to topic 52310 ONLY
→ General group chat has no alerts

**Configuration 2: Without Topic (Empty)**
```env
TELEGRAM_TOPIC_ID=
```
→ Alerts go to group chat ONLY
→ No topic routing applied

**Configuration 3: Without Topic (Not Set)**
```bash
# TELEGRAM_TOPIC_ID not in .env at all
```
→ Same as Configuration 2
→ Alerts go to group chat

---

## Code Implementation

### How It Works (telegram_client.py)

```python
def send_message(self, chat_id: int, text: str, topic_id: Optional[int] = None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    
    # CONDITIONAL ROUTING:
    effective_topic_id = topic_id or self.topic_id
    
    if effective_topic_id:
        # Topic is configured - route to topic
        payload["message_thread_id"] = effective_topic_id
    else:
        # No topic - send to group chat (general channel)
        # Do NOT add message_thread_id parameter
    
    # Send message to Telegram
    response = requests.post(f"{self.api_url}/sendMessage", json=payload)
```

### Key Points:

1. **`effective_topic_id` variable**: Determines routing
   - If topic ID exists → use it
   - If topic ID is None → don't use it (send to general)

2. **`message_thread_id` parameter**: Only added if topic is set
   - Present → routes to topic
   - Absent → sends to group chat

3. **No errors or warnings**: Falls back gracefully
   - No exception if topic_id is None
   - Message always sends (to appropriate location)

---

## User's Setup: @officialmudrex with Topic 52310

For the official Mudrex group:

```env
TELEGRAM_BOT_TOKEN=<your_token>
TELEGRAM_CHAT_ID=-1002xxxxxxxxx  # @officialmudrex group ID
TELEGRAM_OWNER_CHAT_ID=<owner_id>
TELEGRAM_TOPIC_ID=52310  # Volume Alerts topic
```

With this configuration:
- ✅ All alerts go to topic 52310 (Volume Alerts)
- ✅ @officialmudrex general chat stays clean
- ✅ Users can join the topic to see alerts only

To disable topic routing for a group:
```env
TELEGRAM_TOPIC_ID=
```
Then alerts go to general @officialmudrex chat.

---

## Testing the Configuration

### Verify Topic Routing is Active:
```bash
# Check logs
tail -20 logs/volume_bot.log | grep -i topic

# Should show:
# ✅ Telegram topic configured: Topic ID 52310
```

### Verify No Topic (General Chat):
```bash
# Check logs (when TELEGRAM_TOPIC_ID is empty)
tail -20 logs/volume_bot.log

# Should NOT show topic configuration message
# Alerts will go to general chat
```

### Test Alert Delivery:
1. Wait for next volume alert
2. Check where it appears:
   - **With topic set**: Should appear in the topic thread
   - **Without topic**: Should appear in general chat

---

## Frequently Asked Questions

**Q: Why send alerts to both topic and general?**
A: We don't! Conditional routing means:
- Topic ID set → topic ONLY (not general)
- Topic ID empty → general ONLY (not topic)

**Q: Can I change routing without restarting?**
A: No, you must restart the bot after changing `.env`
```bash
pkill -9 -f volume_alert_bot.py
sleep 2
nohup python3 volume_alert_bot.py > logs/volume_bot.log 2>&1 &
```

**Q: What if I want different symbols in different topics?**
A: Advanced routing available! See TELEGRAM_TOPICS.md for custom code examples.

**Q: Does this affect other features?**
A: No, only alert routing. All other features (commands, status, etc.) work the same.

---

## Summary

✅ **Conditional routing is implemented and working**
✅ **Controlled entirely by TELEGRAM_TOPIC_ID setting**
✅ **No alerting to multiple locations**
✅ **Clean, deterministic behavior**

Alerts go where you configure them to go - nowhere else!

