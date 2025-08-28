import logging
from typing import Optional, Any
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

class BotErrorHandler:
    """Centralized error handling for the bot"""
    
    @staticmethod
    async def handle_api_error(
        update: Update, 
        error: Exception, 
        context: str,
        user_message: str = "عذراً، حدث خطأ في الخدمة. يرجى المحاولة لاحقاً."
    ) -> None:
        """Handle API-related errors"""
        logger.error(f"API error in {context}: {str(error)}", exc_info=True)
        if update and update.message:
            await update.message.reply_text(user_message)
    
    @staticmethod
    async def handle_validation_error(
        update: Update, 
        field_name: str, 
        error: str
    ) -> None:
        """Handle form validation errors"""
        logger.warning(f"Validation error in field {field_name}: {error}")
        if update and update.message:
            await update.message.reply_text(f"خطأ في {field_name}: {error}")
    
    @staticmethod
    async def handle_generic_error(
        update: Update, 
        error: Exception, 
        context: str,
        user_message: str = "حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى."
    ) -> None:
        """Handle generic errors"""
        logger.error(f"Unexpected error in {context}: {str(error)}", exc_info=True)
        if update and update.message:
            await update.message.reply_text(user_message)
    
    @staticmethod
    async def handle_file_error(
        update: Update, 
        error: Exception, 
        file_name: str,
        user_message: str = "حدث خطأ أثناء معالجة الملف. يرجى المحاولة مرة أخرى."
    ) -> None:
        """Handle file-related errors"""
        logger.error(f"File error for {file_name}: {str(error)}", exc_info=True)
        if update and update.message:
            await update.message.reply_text(user_message)
    
    @staticmethod
    def log_error(error: Exception, context: str, **kwargs: Any) -> None:
        """Log errors with context and additional data"""
        logger.error(
            f"Error in {context}: {str(error)}", 
            extra=kwargs,
            exc_info=True
        )
