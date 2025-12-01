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
• Real-time volume spike detection (≥75% threshold)
• <b>1h Timeframe:</b> Alerts on ≥75% volume increase
• <b>24h Timeframe:</b> Alerts on ≥75% volume increase
• Per-asset cooldown: 3 hours (1h) / 24 hours (24h)
• Max alerts: 3/day (1h), 1/day (24h) per asset
• Monitoring: BTCUSDT, ETHUSDT, SOLUSDT
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
    
    @staticmethod
    def get_status_message(bot_running: bool):
        """
        Get status message showing bot state
        
        Args:
            bot_running: Boolean indicating if bot is active
        """
        status_emoji = "✅" if bot_running else "🛑"
        status_text = "Bot is active" if bot_running else "Bot is paused"
        
        check_text = "Volume data checking every 5 minutes" if bot_running else "Volume data not checking"
        
        message = f"""<b>📊 Mudrex Volume Alert Bot Status</b>

{status_emoji} <b>{status_text}</b>

⏱️ <b>{check_text}</b>

<b>Current Configuration:</b>
• Monitoring: BTCUSDT, ETHUSDT, SOLUSDT
• Timeframes: 1h, 24h
• Volume Threshold: ≥75% increase
• Check Interval: 5 minutes

<b>Alert Rules:</b>
• <b>1h Timeframe:</b> Max 3 alerts/day per asset, 3-hour cooldown between alerts
• <b>24h Timeframe:</b> Max 1 alert/day per asset, 24-hour cooldown between alerts
• Global Queue Gap: 10 minutes between any alerts

<b>Commands:</b>
• /start @Mudrex_Volume_bot - Activate monitoring
• /stop @Mudrex_Volume_bot - Pause monitoring
• /status @Mudrex_Volume_bot - Show this status

<i>Only the owner can control the bot with /start and /stop commands.</i>"""
        
        return message
    
    @staticmethod
    async def handle_status(telegram_client, chat_id: int, bot_running: bool):
        """Handle /status command"""
        try:
            message = CommandHandler.get_status_message(bot_running)
            await telegram_client.send_message(chat_id, message)
            logger.info(f"✅ Status message sent to {chat_id}")
        except Exception as e:
            logger.error(f"Error sending status message: {e}")
