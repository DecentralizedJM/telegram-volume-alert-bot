# 🐛 Volume Alert Bot - Bug Report

**Date:** November 30, 2025  
**Status:** Critical & High Priority Issues Identified  
**Bot Version:** Current (with 75% threshold fix)

---

## 🔴 Critical Bug #1: Alert Deduplication Logic is Broken

### Issue
**The same volume spike is generating multiple duplicate alerts within the same period.**

Users reported receiving **17 alerts** with many duplicate entries like:
- 7:03 AM: BTC +73.30%
- 7:34 AM: BTC +73.30% (DUPLICATE - same percentage, same candle)
- 7:44 AM: BTC +73.30% (DUPLICATE - same percentage, same candle)

### Root Cause
The `alert_tracking` system uses **period key + counter**, but has **NO open_time deduplication**:

```python
# Current tracking in volume_alert_bot.py (lines 57-66)
self.alert_tracking = {
    symbol: {
        timeframe: {
            "count": 0,
            "last_reset": self._get_period_key(timeframe),
            "locked": False
        }
        for timeframe in self.timeframes.keys()
    }
    for symbol in self.symbols
}
```

**Problems:**
1. `"locked"` flag is set when alert is queued, but **can be reset** when period changes
2. NO tracking of `open_time` from the candle - same candle triggering multiple times
3. Period reset happens hourly for "1h" timeframe, but bot checks every 5 minutes
   - If a candle has 73% volume, it could trigger at minute 5, 10, 15, 20 of the same hour

### Expected Behavior
- **One alert per unique candle** (identified by `open_time`)
- Once BTC's 7:00-8:00 AM candle triggers at 73%, it should NOT trigger again until the 8:00-9:00 AM candle

### Actual Behavior
- Same candle triggering multiple times within same period
- Lock is not persistent enough or gets cleared

### Code Location
- `volume_alert_bot.py` lines 57-70 (initialization)
- `volume_alert_bot.py` lines 357-370 (`_reset_daily_counts()`)
- `volume_alert_bot.py` lines 372-430 (`check_symbol_timeframe()`)

### Impact
**CRITICAL** - Users receive spam alerts, alert fatigue, trust in bot degraded

### Fix Required
```python
# Add open_time tracking to prevent same-candle re-alerts:
self.alert_tracking = {
    symbol: {
        timeframe: {
            "count": 0,
            "last_reset": self._get_period_key(timeframe),
            "locked": False,
            "last_alerted_open_time": None  # ← ADD THIS
        }
        for timeframe in self.timeframes.keys()
    }
    for symbol in self.symbols
}

# Then in check_symbol_timeframe():
# BEFORE sending alert, check if open_time matches last_alerted_open_time
if current_candle['open_time'] == tracking['last_alerted_open_time']:
    return  # Already alerted for this candle
```

---

## 🔴 Critical Bug #2: Queue System Increments Count But Never Sends

### Issue
**Alerts are queued but the lock prevents them from ever being sent.**

Code flow in `_queue_or_send_alert()` (lines 416-432):

```python
if time_since_last < self.alert_queue_gap and self.last_alert_timestamp > 0:
    # Queue the alert
    self.pending_alerts.append((current_time, alert, symbol, timeframe, max_alerts))
    
    # Mark as alerted IMMEDIATELY ← PROBLEM: Set locked=True
    self.alert_tracking[symbol][timeframe]["count"] += 1
    self.alert_tracking[symbol][timeframe]["locked"] = True  # ← BLOCKS NEXT ALERTS
```

### Root Cause
When alert is **queued**, the code sets `locked=True` **immediately**. But `locked` is never set back to `False` until the **period resets**.

**Timeline:**
- 12:46:00 PM - First alert comes in, gets queued, `locked=True`
- 12:46:05 PM - Period is still "2025-11-30-12", `locked=True` blocks any new alerts
- 12:50:00 PM - Different symbol alert comes, gets queued, that symbol locked
- 1:00:00 PM - Period resets to "2025-11-30-13", locks are cleared
- But by then, multiple alerts have been queued in pending_alerts

### Expected Behavior
- Queue system should hold alerts without blocking future detections
- `locked` flag should only prevent **alerts for same period**
- Different symbols should have independent locks

### Actual Behavior
- One symbol getting queued locks that symbol for entire hour
- Multiple alerts pile up in queue
- When queue finally processes, they send in bulk instead of staggered

### Code Location
- `volume_alert_bot.py` lines 416-432 (`_queue_or_send_alert()`)
- `volume_alert_bot.py` lines 357-370 (`_reset_daily_counts()`)

### Impact
**CRITICAL** - Queuing system defeats its own purpose by blocking alerts

### Fix Required
```python
# Don't use "locked" for queuing - only for period enforcement
# Remove the locked=True when queueing

# Instead, check count BEFORE queuing:
if tracking["count"] < max_alerts:
    self.pending_alerts.append((current_time, alert, symbol, timeframe, max_alerts))
    self.alert_tracking[symbol][timeframe]["count"] += 1  # Increment count
    # DON'T set locked=True here
```

---

## 🟠 High Priority Bug #3: Daily Reset Logic Resets Locked Flag But Doesn't Clear Open_time

### Issue
**Period resets clear the `locked` flag, but there's no tracking of which candles already triggered.**

When period resets (hourly for "1h"):
```python
if current_period != last_period:
    self.alert_tracking[symbol][timeframe]["count"] = 0
    self.alert_tracking[symbol][timeframe]["locked"] = False  # ← Clears lock
    self.alert_tracking[symbol][timeframe]["last_reset"] = current_period
```

**Problem:** If the last candle of hour 7 was BTC at 73% with `open_time=1700000400`, and we reset at hour 8, the `open_time` is lost. If the same 73% candle somehow gets checked again (shouldn't happen but could with API retries), it will trigger again.

### Expected Behavior
- Track which `open_time` values have already triggered
- Keep historical data of alerted candles

### Actual Behavior
- No `open_time` tracking at all
- Only time-based period tracking

### Code Location
- `volume_alert_bot.py` lines 357-370 (`_reset_daily_counts()`)

### Impact
**HIGH** - Secondary issue, manifests only with API edge cases or retries

---

## 🟠 High Priority Bug #4: MAX_ALERTS_PER_SYMBOL=3 But Daily Resets Hourly

### Issue
**Inconsistency between config comment and actual reset behavior.**

Config says:
```python
# Max alerts per symbol to avoid spam
# Example: Max 3 BTC alerts, max 3 ETH alerts, max 3 SOL alerts
MAX_ALERTS_PER_SYMBOL = 3
```

But reset happens **hourly for 1h timeframe**:
```python
def _get_period_key(self, timeframe):
    now = datetime.now()
    if timeframe == "1h":
        return now.strftime("%Y-%m-%d-%H")  # ← Resets every HOUR
    else:  # 24h
        return now.strftime("%Y-%m-%d")
```

**Problem:** This means max 3 alerts **per HOUR** for 1h timeframe, not per day. Could be up to 72 alerts per symbol per day (3 per hour × 24 hours).

### Expected Behavior
- Document clearly: is it per-hour or per-day?
- If per-day, reset at UTC midnight
- If per-hour, update config comment

### Actual Behavior
- Code implements per-hour reset for "1h" timeframe
- Per-day reset for "24h" timeframe
- Config comment says "per symbol" without clarity on time window

### Code Location
- `config.py` lines 24-27 (comment)
- `volume_alert_bot.py` lines 351-356 (`_get_period_key()`)

### Impact
**HIGH** - Could still generate many alerts: 3/hour × 24h = 72 alerts/day if all thresholds hit

---

## 🟡 Medium Priority Bug #5: Alert Queue Processor Doesn't Enforce Per-Symbol Limits

### Issue
**The queue processor sends alerts without checking per-symbol counts.**

Code in `alert_queue_processor()` (lines 149-173):
```python
# Dequeue and send alert
self.pending_alerts.pop(0)

# Send alert
await self.telegram.send_alert_message(message)
self.last_alert_timestamp = current_time
```

**Problem:** This doesn't increment the `count` or check if symbol already has 3 alerts. It just sends whatever is in the queue.

### Expected Behavior
- Verify count hasn't exceeded max before dequeuing
- Enforce per-symbol limits during send

### Actual Behavior
- Queue processor is separate from count enforcement
- Could send alert even after hitting limit

### Code Location
- `volume_alert_bot.py` lines 149-173 (`alert_queue_processor()`)

### Impact
**MEDIUM** - Combined with bug #1 and #2, makes alert limiting ineffective

---

## 🟡 Medium Priority Bug #6: Decrease Alerts "Fixed" But Max_alerts Logic Inconsistent

### Issue
**The code checks `>= threshold` for volume increase only, but never explicitly handles or logs decrease detection.**

Code at line 410:
```python
if volume_change_pct >= threshold:
    # Threshold met! Check if we can send alert
    if tracking["count"] < max_alerts:
        # Send the alert
```

**Problem:** There's no `else` clause logging that a decrease was detected. This makes debugging hard. Also, if somehow a negative `volume_change_pct` >= 75 (impossible), it might trigger.

### Expected Behavior
- Explicit logging of decreases detected and ignored
- Clear separation of increase vs decrease logic

### Actual Behavior
- Decreases silently ignored (good) but not logged
- Could cause confusion if someone reviews logs

### Code Location
- `volume_alert_bot.py` lines 409-418

### Impact
**MEDIUM** - Debugging/monitoring issue, not functional

---

## Summary Table

| Bug # | Priority | Issue | Impact | Lines |
|-------|----------|-------|--------|-------|
| 1 | 🔴 CRITICAL | No open_time tracking - same candle alerts multiple times | Duplicate alerts, spam | 57-70, 372-430 |
| 2 | 🔴 CRITICAL | Locked flag blocks queue processing | Alerts queued but never sent | 416-432 |
| 3 | 🟠 HIGH | No historical candle tracking | Edge case re-triggering | 357-370 |
| 4 | 🟠 HIGH | Max alerts per HOUR not per day | Up to 72/day instead of 3 | config.py:24-27 |
| 5 | 🟡 MEDIUM | Queue processor doesn't check counts | Limit enforcement broken | 149-173 |
| 6 | 🟡 MEDIUM | Decreases not explicitly logged | Debugging difficulty | 409-418 |

---

## Recommended Fix Priority

1. **Bug #1** - Implement `last_alerted_open_time` tracking (FIXES duplicate alerts immediately)
2. **Bug #2** - Remove `locked=True` when queueing, use count only (FIXES queue blocking)
3. **Bug #4** - Clarify daily vs hourly reset behavior (FIXES ambiguity)
4. **Bug #3** - Add historical candle tracking
5. **Bug #5** - Validate counts in queue processor
6. **Bug #6** - Add explicit decrease logging

---

## Testing After Fixes

```python
# Test Case 1: Same candle shouldn't alert twice
# Expected: 1 alert for 7:00-8:00 BTC candle with 73% volume
# Actual: Multiple alerts from same candle

# Test Case 2: Queue should allow new alerts while processing
# Expected: All 3 symbols can queue alerts within same minute
# Actual: First symbol locks everything

# Test Case 3: Reset timing should match configuration
# Expected: Period resets at hour/day boundary as configured
# Actual: Resets happen on schedule but lock conflicts
```

---

**Next Steps:** Await approval to implement fixes in priority order.
