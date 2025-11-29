import requests
import logging
from typing import Optional, Dict, Tuple
from datetime import datetime
from config import VolumeAlertConfig

logger = logging.getLogger(__name__)

class BinanceDataFetcher:
    """Fetch OHLCV data from Binance public API"""
    
    def __init__(self):
        self.base_url = VolumeAlertConfig.BINANCE_BASE_URL
        self.timeout = 10
    
    def get_klines(
        self,
        symbol: str,
        interval: str,
        limit: int = 2
    ) -> Optional[list]:
        """
        Fetch OHLCV candles from Binance
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            interval: Timeframe (1h, 12h, 1d)
            limit: Number of candles to fetch (default 2 for current + previous)
        
        Returns:
            List of candles [[open_time, open, high, low, close, volume, ...], ...]
            or None on error
        """
        try:
            params = {
                "symbol": symbol,
                "interval": interval,
                "limit": limit
            }
            
            url = f"{self.base_url}{VolumeAlertConfig.BINANCE_KLINES_ENDPOINT}"
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            return response.json()
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching {symbol} {interval} from Binance: {e}")
            return None
    
    def get_current_and_previous(
        self,
        symbol: str,
        interval: str
    ) -> Optional[Tuple[Dict, Dict]]:
        """
        Get current and previous period for volume comparison
        
        For 1h: Get last 2 hourly candles (current hour + previous hour)
        For 24h: Get data to compare 24h rolling windows
        
        Returns:
            Tuple of (current_candle, previous_candle) or None on error
        """
        if interval == "1h":
            # For 1-hour: Need 2 candles (current + previous hour)
            klines = self.get_klines(symbol, interval, limit=2)
            if not klines or len(klines) < 2:
                logger.warning(f"Insufficient candle data for {symbol} {interval}")
                return None
            
            # Binance returns candles in ascending order (oldest first)
            previous_candle = self._parse_candle(klines[0], symbol, interval)
            current_candle = self._parse_candle(klines[1], symbol, interval)
            
            return current_candle, previous_candle
        
        elif interval == "24h":
            # For 24h rolling window: Need 2 complete 24h candles
            # Binance's 1d interval = 24h candle, so limit=2 gives us what we need
            klines = self.get_klines(symbol, "1d", limit=2)
            if not klines or len(klines) < 2:
                logger.warning(f"Insufficient 24h data for {symbol}")
                return None
            
            # Binance returns candles in ascending order (oldest first)
            previous_candle = self._parse_candle(klines[0], symbol, "24h")
            current_candle = self._parse_candle(klines[1], symbol, "24h")
            
            return current_candle, previous_candle
        
        return None
    
    @staticmethod
    def _parse_candle(kline: list, symbol: str, interval: str) -> Dict:
        """Parse Binance kline into structured format"""
        return {
            "symbol": symbol,
            "interval": interval,
            "open_time": int(kline[0]),
            "open": float(kline[1]),
            "high": float(kline[2]),
            "low": float(kline[3]),
            "close": float(kline[4]),
            "volume": float(kline[7]),  # Quote asset volume
            "trades": int(kline[8]),
            "timestamp": datetime.fromtimestamp(int(kline[0]) / 1000).isoformat()
        }
    
    def get_latest_price(self, symbol: str) -> Optional[float]:
        """Get latest price for a symbol"""
        try:
            url = f"{self.base_url}/api/v3/ticker/price"
            response = requests.get(url, params={"symbol": symbol}, timeout=self.timeout)
            response.raise_for_status()
            return float(response.json()["price"])
        except Exception as e:
            logger.error(f"Error fetching price for {symbol}: {e}")
            return None
