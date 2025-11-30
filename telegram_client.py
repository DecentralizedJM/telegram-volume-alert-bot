import logging
import os
import requests
from typing import Dict, Optional
from telegram import Bot
from telegram.error import TelegramError

logger = logging.getLogger(__name__)

class TelegramClient:
    """Send alerts to Telegram with optional topic support"""
    
    def __init__(self, bot_token: str, chat_id, topic_id: Optional[int] = None):
        """
        Initialize Telegram client
        
        Args:
            bot_token: Telegram bot token from BotFather
            chat_id: Target chat ID for alerts (can be int or str)
            topic_id: Optional Telegram topic ID (for supergroups with topics enabled)
                     If provided, all alerts will be sent to this specific topic
        """
        self.bot_token = bot_token
        self.chat_id = int(chat_id) if isinstance(chat_id, str) else chat_id
        self.topic_id = topic_id
        self.bot = Bot(token=bot_token)
        self.api_url = f"https://api.telegram.org/bot{bot_token}"
        
        if not bot_token or not chat_id:
            logger.error("Telegram credentials missing. Check .env file.")
            raise ValueError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID required in .env")
        
        if self.topic_id:
            logger.info(f"✅ Telegram topic configured: Topic ID {self.topic_id}")
    
    async def send_alert(self, alert: Dict) -> bool:
        """
        Send volume alert to Telegram
        
        Args:
            alert: Alert dict from VolumeDetector
        
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            message = self._format_message(alert)
            return await self.send_message(self.chat_id, message)
        
        except Exception as e:
            logger.error(f"Error sending alert: {e}")
            return False
    
    async def send_alert_message(self, message: str) -> bool:
        """
        Send pre-formatted alert message to Telegram
        
        Args:
            message: Pre-formatted message text
        
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            return await self.send_message(self.chat_id, message)
        except Exception as e:
            logger.error(f"Error sending alert message: {e}")
            return False
    
    async def send_message(self, chat_id: int, text: str, topic_id: Optional[int] = None) -> bool:
        """
        Send a message to a specific chat, optionally to a specific topic
        
        Args:
            chat_id: Target chat ID
            text: Message text (supports HTML formatting)
            topic_id: Optional topic ID (overrides self.topic_id if provided)
        
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            payload = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML"
            }
            
            # Use provided topic_id, fall back to self.topic_id, or send to general chat
            effective_topic_id = topic_id or self.topic_id
            if effective_topic_id:
                payload["message_thread_id"] = effective_topic_id
            
            response = requests.post(
                f"{self.api_url}/sendMessage",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                topic_info = f" (topic {effective_topic_id})" if effective_topic_id else ""
                logger.debug(f"Message sent to chat {chat_id}{topic_info}")
                return True
            else:
                logger.error(f"Telegram error: {response.text}")
                return False
        
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False
    
    @staticmethod
    def _format_message(alert: Dict) -> str:
        """Format alert into readable Telegram message"""
        emoji = "📈" if alert["type"] == "volume_spike" else "📉"
        direction = "INCREASE" if alert["type"] == "volume_spike" else "DECREASE"
        
        message = f"""
<b>🚨 {alert['symbol']} VOLUME ALERT {emoji}</b>

<b>⏱️ Timeframe:</b> {alert['interval']}
<b>💹 Current Price:</b> ${alert['current_price']:,.2f}
<b>📊 Volume Change:</b> <code>{alert['volume_change_pct']:+.2f}%</code>

<b>⚠️ {direction} VOLUME DETECTED</b>
"""
        return message.strip()
