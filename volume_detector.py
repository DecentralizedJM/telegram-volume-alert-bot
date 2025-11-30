import logging
import json
from typing import Dict, Optional, Tuple
from datetime import datetime
from config import VolumeAlertConfig

logger = logging.getLogger(__name__)

class VolumeDetector:
    """Detect volume changes between consecutive time periods"""
    
    def __init__(self):
        self.thresholds = VolumeAlertConfig.VOLUME_THRESHOLDS
        self.state_file = VolumeAlertConfig.STATE_FILE
        self.state = self._load_state()
    
    def detect_volume_alert(
        self,
        current_candle: Dict,
        previous_candle: Dict
    ) -> Optional[Dict]:
        """
        Detect if volume has significantly changed between consecutive periods
        
        For 1h: Compare current hour to previous hour
        For 24h: Compare last 24h rolling window to previous 24h rolling window
        
        Args:
            current_candle: Current period candle data
            previous_candle: Previous period candle data
        
        Returns:
            Alert dict if volume change meets threshold, None otherwise
        """
        if not previous_candle or not current_candle:
            return None
        
        interval = current_candle.get("interval")
        if not interval or interval not in self.thresholds:
            return None
        
        # Avoid division by zero
        if previous_candle["volume"] == 0:
            logger.debug(f"Previous volume is 0 for {current_candle['symbol']} {interval}")
            return None
        
        # Calculate volume change percentage (current vs previous period)
        volume_change_pct = self._calculate_volume_change(
            current_candle["volume"],
            previous_candle["volume"]
        )
        
        # Get threshold for this timeframe
        threshold = self.thresholds[interval]
        
        # Check if change meets threshold
        # IMPORTANT: Only alert on INCREASES (positive changes)
        # Decreases in volume don't help traders, so we skip them
        if volume_change_pct >= threshold:
            alert = {
                "symbol": current_candle["symbol"],
                "interval": current_candle["interval"],
                "type": "volume_spike",  # Only positive spikes, no drops
                "volume_change_pct": round(volume_change_pct, 2),
                "current_volume": round(current_candle["volume"], 2),
                "previous_volume": round(previous_candle["volume"], 2),
                "current_price": current_candle.get("close", 0),
                "timestamp": datetime.now().isoformat(),
                "open_time": current_candle["open_time"]
            }
            
            # Check if we already sent alert for this candle/period
            if self._should_alert(alert):
                self._save_state(alert)
                logger.info(f"🔔 Volume Spike Detected: {alert['symbol']} {interval} {volume_change_pct:+.2f}% (threshold: ±{threshold}%)")
                return alert
        
        return None
    
    @staticmethod
    def _calculate_volume_change(current_vol: float, previous_vol: float) -> float:
        """Calculate percentage change in volume"""
        return ((current_vol - previous_vol) / previous_vol) * 100
    
    def _should_alert(self, alert: Dict) -> bool:
        """Check if we should send alert (avoid duplicates for same candle)"""
        key = f"{alert['symbol']}_{alert['interval']}"
        
        if key not in self.state:
            return True
        
        # Check if open_time is different (new candle)
        if self.state[key].get("open_time") != alert["open_time"]:
            return True
        
        return False
    
    def _load_state(self) -> Dict:
        """Load previously processed candles"""
        try:
            with open(self.state_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
        except Exception as e:
            logger.error(f"Error loading state: {e}")
            return {}
    
    def _save_state(self, alert: Dict) -> None:
        """Save processed candle to avoid duplicate alerts"""
        try:
            key = f"{alert['symbol']}_{alert['interval']}"
            self.state[key] = {
                "open_time": alert["open_time"],
                "timestamp": alert["timestamp"]
            }
            
            import os
            os.makedirs(os.path.dirname(self.state_file) or ".", exist_ok=True)
            
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving state: {e}")
