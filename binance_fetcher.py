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
        # Headers to help with geo-blocking issues
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
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
            response = requests.get(url, params=params, timeout=self.timeout, headers=self.headers)
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
        Get last 2 CLOSED/COMPLETE candles for volume comparison
        
        Fetches 3 candles from Binance but uses only the 2 most recent CLOSED ones.
        The third candle is incomplete and skipped (has almost no data).
        
        For 1h: Compares 2 most recent complete hourly candles
        For 24h: Compares 2 most recent complete daily candles
        
        Returns:
            Tuple of (older_closed_candle, newer_closed_candle) or None on error
        """
        if interval == "1h":
            # Fetch 3 hourly candles
            klines = self.get_klines(symbol, interval, limit=3)
            if not klines or len(klines) < 3:
                logger.warning(f"Insufficient candle data for {symbol} {interval}")
                return None
            
            # Binance returns in ascending order: [oldest, middle, current_INCOMPLETE]
            # We use [0] and [1] which are the 2 most recent CLOSED candles
            # We skip [2] which is incomplete and has almost no volume data
            older_closed = self._parse_candle(klines[0], symbol, interval)
            newer_closed = self._parse_candle(klines[1], symbol, interval)
            
            logger.debug(f"{symbol} 1h: Comparing {older_closed['timestamp']} "
                        f"(vol: {older_closed['volume']}) vs "
                        f"{newer_closed['timestamp']} (vol: {newer_closed['volume']})")
            
            return older_closed, newer_closed
        
        elif interval == "24h":
            # For 24h rolling window: Fetch 3 daily candles
            klines = self.get_klines(symbol, "1d", limit=3)
            if not klines or len(klines) < 3:
                logger.warning(f"Insufficient 24h data for {symbol}")
                return None
            
            # Binance returns in ascending order: [oldest, middle, current_INCOMPLETE]
            # We use [0] and [1] which are the 2 most recent CLOSED candles
            # We skip [2] which is incomplete and has almost no volume data
            older_closed = self._parse_candle(klines[0], symbol, "24h")
            newer_closed = self._parse_candle(klines[1], symbol, "24h")
            
            logger.debug(f"{symbol} 24h: Comparing {older_closed['timestamp']} "
                        f"(vol: {older_closed['volume']}) vs "
                        f"{newer_closed['timestamp']} (vol: {newer_closed['volume']})")
            
            return older_closed, newer_closed
        
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
