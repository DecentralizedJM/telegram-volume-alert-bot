# ✅ Implementation Complete: Per-Asset Alert Cooldown System

## Summary

The volume alert bot now enforces **per-asset cooldown periods** to prevent alert spam while allowing multiple alerts per asset per day.

---

## Feature: Cooldown-Based Alert Control

### **1-Hour Timeframe (1h)**
- **Cooldown per Asset**: 3 hours
- **Daily Maximum**: 3 alerts per asset
- **Global Queue Gap**: 10 minutes (between ANY alerts across all assets)
- **Total Daily Capacity**: ~8 alerts per asset (24h ÷ 3h cooldown)

**Example Timeline for BTC (1h)**:
```
10:30 PM - BTC alert #1 sent ✅
  └─ Cooldown starts (3 hours)
10:40 PM - BTC volume spike → SUPPRESSED ❌ (in cooldown)
11:30 PM - BTC volume spike → SUPPRESSED ❌ (in cooldown)
1:30 AM+ - Cooldown expires, BTC alert #2 can send ✅
  └─ Cooldown resets
5:00 AM+ - BTC alert #3 can send ✅
5:30 AM - BTC volume spike → SUPPRESSED ❌ (daily max reached: 3)
```

### **24-Hour Timeframe (24h)**
- **Cooldown per Asset**: 24 hours (exactly 1 alert per asset per day)
- **Daily Maximum**: 1 alert per asset
- **Global Queue Gap**: 10 minutes (between ANY alerts across all assets)
- **Total Daily Capacity**: 1 alert per asset

**Example Timeline for BTC (24h)**:
```
10:30 PM Day 1 - BTC 24h alert #1 sent ✅
  └─ Cooldown starts (24 hours)
11:00 PM Day 1 - BTC 24h volume spike → SUPPRESSED ❌ (already alerted today)
12:00 AM Day 2 - Daily reset + cooldown check
1:00 AM Day 2 - BTC 24h alert #2 can send ✅ (new day + cooldown expired)
```

### **Different Assets Have Independent Cooldowns**
```
10:30 PM - BTC alert sent ✅ (starts global queue)
10:35 PM - ETH volume spike → QUEUED (waiting for 10-min gap)
10:40 PM - ETH alert sent ✅ (10 min gap respected)
10:45 PM - BTC volume spike → SUPPRESSED ❌ (in 3h cooldown)
10:50 PM - ETH volume spike → Can alert ✅ (independent 3h cooldown for ETH)
```

---

## Technical Implementation

### Data Structure
Each symbol/timeframe now tracks:
```json
{
  "BTCUSDT": {
    "1h": {
      "count": 2,                          // Alerts sent today
      "last_reset": "2025-11-30",          // Daily reset date
      "last_alerted_open_time": 1700000400,  // Candle timestamp (same-candle dedup)
      "last_alert_timestamp": 1700000000,    // Unix timestamp when alert was sent
      "cooldown_seconds": 10800            // 3 hours (10800s) for 1h timeframe
    },
    "24h": {
      "count": 1,
      "last_reset": "2025-11-30",
      "last_alerted_open_time": 1700000400,
      "last_alert_timestamp": 1700000000,
      "cooldown_seconds": 86400           // 24 hours (86400s) for 24h timeframe
    }
  }
}
```

### Alert Processing Flow

```
Check Volume for Symbol/Timeframe
  ↓
1️⃣ Same-Candle Duplicate Check
   └─ current_open_time == last_alerted_open_time?
   └─ YES → Skip (already alerted for this exact candle) ❌
   └─ NO → Continue ✅
  ↓
2️⃣ Asset Cooldown Check
   └─ (current_time - last_alert_timestamp) < cooldown_seconds?
   └─ YES → Skip (in cooldown period) ❌
   └─ NO → Continue ✅
  ↓
3️⃣ Daily Limit Check
   └─ count < max_alerts?
   └─ YES → Continue ✅
   └─ NO → Skip (daily limit reached) ❌
  ↓
4️⃣ Global Queue Gap Check
   └─ (current_time - global_last_alert) < 600 seconds?
   └─ YES → Queue alert (wait 10 min) ⏳
   └─ NO → Send immediately ✅
```

### Four-Layer Deduplication

| Layer | Purpose | Scope | Trigger |
|-------|---------|-------|---------|
| **Same-Candle** | Prevent duplicate of exact same candle | Per Asset | `current_open_time == last_alerted_open_time` |
| **Cooldown** | Enforce minimum time between alerts | Per Asset | `current_time - last_alert_timestamp < cooldown_seconds` |
| **Daily Limit** | Max alerts per day | Per Asset | `count >= max_alerts` |
| **Global Queue** | Prevent Telegram spam | All Assets | `current_time - global_last_alert < 600s` |

---

## Configuration

### Edit Cooldown Values
File: `volume_alert_bot.py` (lines 69-80)
```python
self.alert_tracking = {
    symbol: {
        timeframe: {
            ...
            "cooldown_seconds": 10800 if timeframe == "1h" else 86400
            #                    ↑ 3h (10800s) for 1h
            #                                      ↑ 24h (86400s) for 24h
        }
        ...
    }
}
```

### To Change Values:
```python
# For 1h: change 10800 to desired seconds (e.g., 7200 = 2 hours)
# For 24h: change 86400 to desired seconds (e.g., 43200 = 12 hours)
```

### Global Queue Gap
File: `config.py`
```python
ALERT_QUEUE_GAP_SECONDS = 600  # 10 minutes, change as needed
```

---

## Persistence Across Restarts

✅ **All cooldown state is saved to disk**
- File: `data/alert_tracking.json`
- Updated after every alert
- Loaded on bot startup

**Example**: If alert sent 30 minutes ago with 3-hour cooldown:
- Bot restarts
- Cooldown state loaded: 2 hours 30 minutes remaining
- Alert suppressed until cooldown expires

---

## Testing the Cooldown Feature

### Test Case 1: Per-Asset 3-Hour Cooldown (1h)
```
1. 10:30 PM - BTC volume +105% → Alert sent ✅
2. 10:40 PM - BTC volume +95% → Alert queued ⏳ (10-min gap)
3. 10:50 PM - BTC new candle volume +110% → Suppressed ❌ (in 3h cooldown)
4. 1:31 AM - BTC volume +85% → Can send ✅ (3h cooldown expired)
```

### Test Case 2: One Alert Per Day (24h)
```
1. 10:30 PM - BTC 24h volume +105% → Alert sent ✅ (count=1)
2. 10:40 PM - BTC 24h volume +110% → Queued ⏳ (10-min gap)
3. 11:00 PM - BTC 24h volume +95% → Suppressed ❌ (max 1 per day reached)
4. Next day 12:01 AM - BTC 24h volume +88% → Can send ✅ (new day)
```

### Test Case 3: Independent Cooldowns (Different Assets)
```
1. 10:30 PM - BTC alert sent ✅ (global queue starts)
2. 10:35 PM - ETH volume spike → Queued ⏳ (waiting for 10-min gap)
3. 10:40 PM - ETH alert sent ✅ (10-min gap met)
4. 10:45 PM - BTC volume spike → Suppressed ❌ (BTC 3h cooldown active)
5. 10:50 PM - ETH volume spike → Can send ✅ (ETH independent cooldown)

Result: BTC and ETH have separate 3-hour cooldowns
```

---

## Recent Changes

### Files Modified
- `volume_alert_bot.py`: Core cooldown implementation
- `ALERT_FREQUENCY_RULES.md`: Complete documentation

### Commits
```
ec4457b - fix: handle missing fields when loading old persisted alert tracking
befff5a - debug: add logging to monitor loop startup
e04557c - feat: implement per-asset cooldown with 3h/24h suppression
```

### Git History
```
befff5a - debug: add logging to monitor loop startup
ec4457b - fix: handle missing fields when loading old persisted alert tracking
e04557c - feat: implement per-asset cooldown with 3h/24h suppression
ddf3bfd - simplify: queue clearing logic to avoid timeouts
73fe1e6 - fix: improve telegram queue clearing logic
26d876a - fix: prevent duplicate activation messages and improve dedup logging
```

---

## How It Works: Example Scenario

### Scenario: BTC and ETH Both Spike at 10:30 PM

**Timeline**:
```
10:30:00 PM - BTC volume check
  ├─ Same-candle dedup: No previous alert → Pass ✅
  ├─ Cooldown check: No previous alert → Pass ✅
  ├─ Daily limit: count=0 < 3 → Pass ✅
  ├─ Global queue: First alert, send now → BTC Alert SENT ✅
  └─ Save state: last_alert_timestamp = 10:30 PM
     
10:30:30 PM - ETH volume check
  ├─ Same-candle dedup: No previous alert → Pass ✅
  ├─ Cooldown check: No previous alert → Pass ✅
  ├─ Daily limit: count=0 < 3 → Pass ✅
  ├─ Global queue: 30s since last alert < 600s → Queue ⏳
  └─ Add to pending queue, wait until 10:40 PM
     
10:35:00 PM - BTC volume check (same candle, volume still high)
  ├─ Same-candle dedup: open_time matches → SKIP ❌
  
10:40:00 PM - ETH alert ready (10-min gap met)
  ├─ Process queued alert → ETH Alert SENT ✅
  └─ Save state: last_alert_timestamp = 10:40 PM
     
10:45:00 PM - BTC volume check (new candle)
  ├─ Same-candle dedup: Different open_time → Pass ✅
  ├─ Cooldown check: (10:45 PM - 10:30 PM) = 15 min < 3h → SKIP ❌
  
10:50:00 PM - ETH volume check (new candle)
  ├─ Same-candle dedup: Different open_time → Pass ✅
  ├─ Cooldown check: (10:50 PM - 10:40 PM) = 10 min < 3h → SKIP ❌
```

---

## Summary of Alert Rules

### 1-Hour Timeframe
| Rule | Value | Notes |
|------|-------|-------|
| Cooldown | 3 hours | Between alerts for same asset |
| Max/Day | 3 | Resets at UTC midnight |
| Queue Gap | 10 minutes | Between any assets |
| Threshold | 75% | Volume increase required |

### 24-Hour Timeframe
| Rule | Value | Notes |
|------|-------|-------|
| Cooldown | 24 hours | Between alerts for same asset |
| Max/Day | 1 | Resets at UTC midnight |
| Queue Gap | 10 minutes | Between any assets |
| Threshold | 75% | Volume increase required |

---

## Monitoring the Bot

### View Active Cooldowns
```bash
tail -f logs/volume_bot.log | grep "⏳"
```

### View Alerts Sent
```bash
tail -f logs/volume_bot.log | grep "📤"
```

### View Suppressed (Cooldown)
```bash
tail -f logs/volume_bot.log | grep "In cooldown"
```

### Check Persisted State
```bash
cat data/alert_tracking.json | python3 -m json.tool
```

---

## What Changed From Before

### Before
- Max 3 alerts per day per asset
- No per-asset cooldown
- Multiple alerts possible within same hour for same asset

### After  
- Max 3 alerts per day per asset (same)
- **Per-asset 3-hour cooldown** (NEW)
- Minimum 3-hour gap between alerts for same asset (NEW)
- Different assets can alert independently (NEW)
- Persistence improved to handle field additions (NEW)

---

## Status: ✅ LIVE

Bot is now running with the new cooldown feature:
- ✅ Per-asset cooldown enforcement
- ✅ 3-hour suppression for 1h timeframe
- ✅ 24-hour suppression for 24h timeframe
- ✅ Independent asset cooldowns
- ✅ State persistence across restarts
- ✅ Global 10-minute queue gap maintained

Test by sending volume spikes and checking logs for cooldown messages.
