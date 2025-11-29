"""
Command Handler for Telegram Bot
Handles /start and user messages
"""

import logging

logger = logging.getLogger(__name__)

class CommandHandler:
    """Handle Telegram commands and messages"""
    
    @staticmethod
    def get_welcome_message():
        """
        Professional welcome message for the bot
        This is sent when /start is clicked or bot is messaged
        """
        message = """<b>🚀 Mudrex Volume Alert Bot</b>

<b>Proprietary Trading Signal Service</b>

This bot is a <b>proprietary service</b> created for <b>@DecentralizedJM</b> to deliver real-time cryptocurrency volume alerts.

<b>📊 Features:</b>
• Real-time volume change detection (≥30%)
• Monitoring: BTC, ETH, SOL
• Timeframes: 1h, 12h, 24h
• Instant Telegram notifications

<b>🎯 Purpose:</b>
To identify significant volume movements that signal potential trading opportunities.

<b>👥 Join Our Community:</b>
For more trading insights and updates, join us at <a href="https://t.me/officialmudrex">@officialmudrex</a>

<i>This bot operates automatically. You'll receive alerts when volume thresholds are met.</i>

---
<i>Built with ❤️ for traders by @DecentralizedJM</i>"""
        
        return message
    
    @staticmethod
    async def handle_start(telegram_client, chat_id: int):
        """Handle /start command"""
        try:
            message = CommandHandler.get_welcome_message()
            await telegram_client.send_message(chat_id, message)
            logger.info(f"✅ Welcome message sent to {chat_id}")
        except Exception as e:
            logger.error(f"Error sending welcome message: {e}")
    
    @staticmethod
    async def handle_message(telegram_client, chat_id: int, text: str):
        """Handle user messages"""
        try:
            # Respond with welcome message to any message
            message = CommandHandler.get_welcome_message()
            await telegram_client.send_message(chat_id, message)
            logger.info(f"✅ Response sent to {chat_id}")
        except Exception as e:
            logger.error(f"Error handling message: {e}")
