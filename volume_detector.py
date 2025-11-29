import logging
import json
from typing import Dict, Optional, Tuple
from datetime import datetime
from config import VolumeAlertConfig

logger = logging.getLogger(__name__)

class VolumeDetector:
    """Detect volume spikes and drops"""
    
    def __init__(self):
        self.threshold = VolumeAlertConfig.VOLUME_THRESHOLD
        self.state_file = VolumeAlertConfig.STATE_FILE
        self.state = self._load_state()
    
    def detect_volume_alert(
        self,
        current_candle: Dict,
        previous_candle: Dict
    ) -> Optional[Dict]:
        """
        Detect if volume has significantly changed
        
        Args:
            current_candle: Current candle data
            previous_candle: Previous candle data
        
        Returns:
            Alert dict if volume change meets threshold, None otherwise
        """
        if not previous_candle or not current_candle:
            return None
        
        # Avoid division by zero
        if previous_candle["volume"] == 0:
            logger.warning(f"Previous volume is 0 for {current_candle['symbol']} {current_candle['interval']}")
            return None
        
        # Calculate volume change percentage
        volume_change_pct = self._calculate_volume_change(
            current_candle["volume"],
            previous_candle["volume"]
        )
        
        # Check if change meets threshold
        if abs(volume_change_pct) >= self.threshold:
            alert = {
                "symbol": current_candle["symbol"],
                "interval": current_candle["interval"],
                "type": "volume_spike" if volume_change_pct > 0 else "volume_drop",
                "volume_change_pct": round(volume_change_pct, 2),
                "current_volume": round(current_candle["volume"], 2),
                "previous_volume": round(previous_candle["volume"], 2),
                "current_price": current_candle.get("close", 0),
                "timestamp": datetime.now().isoformat(),
                "open_time": current_candle["open_time"]
            }
            
            # Check if we already sent alert for this candle
            if self._should_alert(alert):
                self._save_state(alert)
                logger.info(f"Volume alert: {alert['symbol']} {alert['interval']} {alert['volume_change_pct']}%")
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
