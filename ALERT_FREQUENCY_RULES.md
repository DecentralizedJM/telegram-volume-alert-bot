# Alert Frequency & Cooldown Rules

## Overview

The bot enforces strict alert frequency rules to prevent spam while allowing multiple alerts per asset per day.

---

## 1-Hour Timeframe (1h) Rules

### Cooldown Per Asset
- **Minimum Gap**: 3 hours between alerts for the SAME asset
- **Example**: 
  - BTC alerts at 10:30 PM (9-10 PM candle)
  - Next BTC alert can only trigger after 1:30 AM (minimum)
  - If BTC has another spike at 11:00 PM (10-11 PM candle), alert is **SUPPRESSED** until 1:30 AM

### Global Queue Gap
- **Minimum Gap**: 10 minutes between sending ANY alerts (across all assets)
- **Purpose**: Prevent telegram spam from multiple assets triggering simultaneously
- **Example**:
  - BTC alert sent at 10:30 PM
  - ETH triggers at 10:35 PM → alert is QUEUED
  - ETH alert actually sends at 10:40 PM (10 min after BTC)

### Daily Maximum
- **Max Alerts**: 3 per asset per day
- **Reset**: Daily at UTC midnight (00:00 UTC)
- **Example**: BTC can have max 3 alerts in a 24-hour period

### Summary: 1-Hour Behavior
```
Asset: BTC
Timeline:
  10:30 PM - BTC alert #1 sent ✅ (cooldown starts)
  11:00 PM - BTC volume spike ❌ (in 3h cooldown, suppressed)
  11:30 PM - BTC volume spike ❌ (in 3h cooldown, suppressed)
  1:30 AM+ - BTC alert #2 can send ✅ (cooldown expires)
  2:00 AM - BTC alert #2 sent ✅ (cooldown resets)
  5:00 AM+ - BTC alert #3 can send ✅ (after 3h cooldown)
  5:30 AM - BTC alert #3 sent ✅ (max 3 reached)
  5:35 AM - BTC volume spike ❌ (max 3 alerts reached for today)
  
Different Asset: ETH
Timeline:
  10:30 PM - BTC alert sent (starts global queue)
  10:35 PM - ETH volume spike → QUEUED (waiting for 10-min gap)
  10:40 PM - ETH alert #1 sent ✅ (10 min gap respected)
```

---

## 24-Hour Timeframe (24h) Rules

### Cooldown Per Asset
- **Minimum Gap**: 24 hours between alerts for the SAME asset
- **Exactly**: One alert per asset per day
- **Example**:
  - BTC 24h alert sent at 10:30 PM
  - Next BTC 24h alert can only trigger after 10:30 PM next day

### Global Queue Gap
- **Minimum Gap**: 10 minutes between sending ANY alerts (across all assets)
- **Purpose**: Prevent telegram spam
- **Example**:
  - BTC 24h alert sent at 10:30 PM
  - ETH 24h triggers at 10:35 PM → alert is QUEUED
  - ETH 24h alert actually sends at 10:40 PM (10 min after BTC)

### Daily Maximum
- **Max Alerts**: 1 per asset per day
- **Reset**: Daily at UTC midnight (00:00 UTC)
- **Example**: BTC can have max 1 alert in a 24-hour period

### Summary: 24-Hour Behavior
```
Asset: BTC (24h)
Timeline:
  10:30 PM - BTC 24h alert #1 sent ✅ (cooldown starts)
  10:35 PM - BTC 24h volume spike ❌ (same day, already alerted)
  11:00 PM - BTC 24h volume spike ❌ (same day, already alerted)
  11:59 PM - BTC 24h volume spike ❌ (same day, already alerted)
  12:00 AM (next day) - Alert count resets
  12:01 AM - BTC 24h volume spike → Can alert ✅ (new day, cooldown expired)

Different Asset: ETH (24h)
Timeline:
  10:30 PM - BTC 24h alert sent (starts global queue)
  10:35 PM - ETH 24h volume spike → QUEUED (waiting for 10-min gap)
  10:40 PM - ETH 24h alert #1 sent ✅ (10 min gap respected)
```

---

## Implementation Details

### Data Structure
```python
alert_tracking = {
    "BTCUSDT": {
        "1h": {
            "count": 2,                      # Alerts sent today
            "last_reset": "2025-11-30",      # Daily reset date
            "last_alerted_open_time": 1700000400,  # Candle timestamp (dedup)
            "last_alert_timestamp": 1700000000,    # Unix timestamp of last alert (cooldown)
            "cooldown_seconds": 10800        # 3 hours for 1h, 86400 for 24h
        },
        "24h": {
            "count": 1,
            "last_reset": "2025-11-30",
            "last_alerted_open_time": 1700000400,
            "last_alert_timestamp": 1700000000,
            "cooldown_seconds": 86400       # 24 hours for 24h
        }
    }
}
```

### Three-Layer Deduplication

1. **Same-Candle Check** (Per Asset)
   - Compares `current_open_time` with `last_alerted_open_time`
   - Prevents 2 alerts for the exact same candle
   - Example: 9-10 PM candle can only trigger once

2. **Cooldown Check** (Per Asset)
   - Checks if `(current_time - last_alert_timestamp) < cooldown_seconds`
   - Enforces minimum time gap between alerts for same asset
   - 1h: 3-hour cooldown
   - 24h: 24-hour cooldown

3. **Daily Limit Check** (Per Asset)
   - Checks if `count < max_alerts`
   - Resets when `last_reset` date changes
   - 1h: max 3 per day
   - 24h: max 1 per day

4. **Global Queue Gap** (All Assets)
   - Checks if `(current_time - last_alert_timestamp_global) < 600 seconds`
   - If gap not met, alert is queued and sent 10 minutes after last alert
   - Applies to all assets equally

### Alert Processing Flow
```
Check Symbol Volume
  ↓
Same-Candle Duplicate? → YES → Skip ❌
  ↓ NO
Asset in Cooldown Period? → YES → Skip ❌
  ↓ NO
Daily Limit Reached? → YES → Skip ❌
  ↓ NO
Global Queue Gap Met? → YES → Send Immediately ✅
  ↓ NO
Global Queue Gap Met? → NO → Queue Alert, Send After Gap ✅
```

---

## Daily Reset Behavior

### Reset Time
- **UTC Midnight**: 00:00 UTC (or local midnight, depending on server timezone)
- **Fields Reset**:
  - `count` → 0
  - `last_reset` → "2025-12-01" (new date)
- **Fields NOT Reset**:
  - `last_alerted_open_time` → kept for historical dedup
  - `last_alert_timestamp` → kept for cooldown calculation across day boundary

### Edge Case: Daily Reset with Active Cooldown
```
Scenario: Alert sent at 10:00 PM, cooldown expires at 1:00 AM next day
  10:00 PM (Day 1) - Alert sent
  1:00 AM (Day 2) - Cooldown expires, but count has been reset
  1:00 AM (Day 2) - New alert can trigger (count = 0, cooldown met)
```

---

## Configuration

### Current Settings
```python
# Symbols monitored
SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']

# Timeframes
TIMEFRAMES = {
    '1h': {'cooldown': 3 * 3600, 'max_alerts': 3},
    '24h': {'cooldown': 24 * 3600, 'max_alerts': 1}
}

# Global queue gap
ALERT_QUEUE_GAP_SECONDS = 600  # 10 minutes

# Volume thresholds
VOLUME_THRESHOLDS = {
    '1h': 75,   # 75% increase required
    '24h': 75   # 75% increase required
}
```

### To Modify
Edit `config.py`:
```python
# For 1h: change cooldown from 10800 (3h) to another value
# For 24h: change cooldown from 86400 (24h) to another value
# For global queue: change ALERT_QUEUE_GAP_SECONDS from 600 to another value
```

---

## Alert Storage & Persistence

### File Location
`data/alert_tracking.json`

### Persisted Across Restarts
All fields are saved to disk:
- `count` ✅
- `last_reset` ✅
- `last_alerted_open_time` ✅
- `last_alert_timestamp` ✅

### Load on Startup
- Bot loads previous state from `data/alert_tracking.json`
- Cooldown state is preserved (if alert sent 30 min ago, 2h 30min cooldown remains)
- Daily limit is preserved (if 2 alerts sent, only 1 remaining for today)

---

## Testing the Rules

### Test Case 1: 1-Hour Cooldown
```
Setup: BTC 1h, threshold 75%
1. 10:30 PM - Volume +105% → Alert sent ✅
2. 10:40 PM - Volume +85% → Alert QUEUED (10-min gap)
3. 10:50 PM - Volume +90% → Skip (in queue)
4. 11:00 PM - New candle, volume +78% → Alert in cooldown ❌ Skip
5. 1:31 PM+1h - Volume +80% → Alert can send ✅ (3h cooldown met)
```

### Test Case 2: 24-Hour Limit
```
Setup: BTC 24h, max 1 alert per day
1. 10:30 PM - Volume +105% → Alert sent ✅ (count=1)
2. 10:40 PM - Volume +110% → Alert QUEUED (10-min gap)
3. 10:50 PM - Next candle, volume +95% → Skip (max 1 reached) ❌
4. Next day 12:01 AM - Count resets, volume +78% → Alert can send ✅ (new day)
```

### Test Case 3: Different Assets
```
Setup: BTC & ETH 1h, both volume spikes
1. 10:30 PM - BTC volume +105% → BTC alert sent ✅
2. 10:35 PM - ETH volume +80% → ETH alert QUEUED (10-min gap)
3. 10:40 PM - ETH alert actually sends ✅
4. 10:45 PM - BTC volume +90% → BTC in 3h cooldown ❌ Skip
5. 10:50 PM - ETH volume +85% → ETH can alert (different asset, own cooldown)

Result: Different assets have independent cooldowns
```
