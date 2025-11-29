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
        Get previous CLOSED candle and current INCOMPLETE candle for real-time comparison
        
        Fetches 3 candles to get 2 most recent candles:
        - previous_closed: The last fully closed candle (e.g., last complete hour)
        - current_incomplete: The current ongoing candle with real-time data
        
        This allows real-time volume spike detection WITHOUT waiting for candle close.
        
        For 1h: Compares closed hour vs current incomplete hour (updates every 5 min)
        For 24h: Compares closed day vs current incomplete day (updates every 5 min)
        
        Returns:
            Tuple of (previous_closed_candle, current_incomplete_candle) or None on error
        """
        if interval == "1h":
            # Fetch 3 hourly candles
            klines = self.get_klines(symbol, interval, limit=3)
            if not klines or len(klines) < 2:
                logger.warning(f"Insufficient candle data for {symbol} {interval}")
                return None
            
            # Binance returns in ascending order: [oldest, middle, current_INCOMPLETE]
            # Index [1] = previous complete closed candle
            # Index [2] = current incomplete candle (real-time data, still forming)
            previous_closed = self._parse_candle(klines[1], symbol, interval)
            current_incomplete = self._parse_candle(klines[2], symbol, interval)
            
            logger.debug(f"{symbol} 1h: Comparing closed {previous_closed['timestamp']} "
                        f"(vol: {previous_closed['volume']}) vs "
                        f"incomplete {current_incomplete['timestamp']} (vol: {current_incomplete['volume']})")
            
            return previous_closed, current_incomplete
        
        elif interval == "24h":
            # For 24h rolling window: Fetch 3 daily candles
            klines = self.get_klines(symbol, "1d", limit=3)
            if not klines or len(klines) < 2:
                logger.warning(f"Insufficient 24h data for {symbol}")
                return None
            
            # Binance returns in ascending order: [oldest, middle, current_INCOMPLETE]
            # Index [1] = previous complete closed day
            # Index [2] = current incomplete day (real-time data, still forming)
            previous_closed = self._parse_candle(klines[1], symbol, "24h")
            current_incomplete = self._parse_candle(klines[2], symbol, "24h")
            
            logger.debug(f"{symbol} 24h: Comparing closed {previous_closed['timestamp']} "
                        f"(vol: {previous_closed['volume']}) vs "
                        f"incomplete {current_incomplete['timestamp']} (vol: {current_incomplete['volume']})")
            
            return previous_closed, current_incomplete
        
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
