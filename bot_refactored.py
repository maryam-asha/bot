import logging
import asyncio
from typing import Dict, Any, Optional
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, CallbackQueryHandler
from telegram import ReplyKeyboardRemove

# Import our new modular components
from config.settings import settings
from config.conversation_states import ConversationState, get_previous_state
from handlers.main_menu_handler import MainMenuHandler
from handlers.service_menu_handler import ServiceMenuHandler
from handlers.form_handler import FormHandler
from handlers.auth_handler import AuthHandler
from handlers.request_handler import RequestHandler
from utils.error_handler import BotErrorHandler
from services.api_service import ApiService

# Configure logging
logging.basicConfig(
    format=settings.log_format,
    level=getattr(logging, settings.log_level.upper())
)
logger = logging.getLogger(__name__)

class YourVoiceBot:
    """Main bot class using dependency injection and better organization"""
    
    def __init__(self):
        self.api_service: Optional[ApiService] = None
        self.error_handler = BotErrorHandler()
        
        # Initialize handlers
        self.main_menu_handler = MainMenuHandler()
        self.service_menu_handler = ServiceMenuHandler()
        self.form_handler = FormHandler()
        self.auth_handler = AuthHandler()
        self.request_handler = RequestHandler()
        
        # Application instance
        self.application: Optional[Application] = None
    
    async def initialize(self) -> None:
        """Initialize bot components"""
        try:
            logger.info("Initializing bot...")
            
            # Initialize API service
            self.api_service = ApiService()
            await self.api_service.initialize_urls()
            
            # Build application
            self.application = Application.builder().token(settings.telegram_token).build()
            
            # Set up handlers
            await self._setup_handlers()
            
            logger.info("Bot initialization complete.")
            
        except Exception as e:
            logger.error(f"Failed to initialize bot: {str(e)}")
            raise
    
    async def _setup_handlers(self) -> None:
        """Set up conversation handlers"""
        # Main conversation handler
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', self._start_command)],
            states={
                ConversationState.MAIN_MENU: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.main_menu_handler.handle)
                ],
                ConversationState.SERVICE_MENU: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.service_menu_handler.handle)
                ],
                ConversationState.ENTER_MOBILE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.auth_handler.handle_mobile)
                ],
                ConversationState.ENTER_OTP: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.auth_handler.handle_otp)
                ],
                ConversationState.SELECT_REQUEST_TYPE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.service_menu_handler.handle_request_type)
                ],
                ConversationState.SELECT_COMPLIMENT_SIDE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.service_menu_handler.handle_side_selection)
                ],
                ConversationState.SELECT_SUBJECT: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.service_menu_handler.handle_subject_selection)
                ],
                ConversationState.SELECT_SERVICE_CATEGORY: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.service_menu_handler.handle_service_category)
                ],
                ConversationState.SELECT_SERVICE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.service_menu_handler.handle_service_selection)
                ],
                ConversationState.FILL_FORM: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.form_handler.handle_text_input),
                    MessageHandler(filters.ATTACHMENT, self.form_handler.handle_attachment)
                ],
                ConversationState.CONFIRM_SUBMISSION: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.form_handler.handle_confirmation)
                ],
                ConversationState.SELECT_REQUEST_NUMBER: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.request_handler.handle_request_selection)
                ],
                ConversationState.SELECT_TIME_AM_PM: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.form_handler.handle_time_am_pm)
                ],
            },
            fallbacks=[CommandHandler('cancel', self._cancel_command)]
        )
        
        self.application.add_handler(conv_handler)
        
        # Add callback query handler for file viewing
        self.application.add_handler(
            CallbackQueryHandler(self.request_handler.handle_file_view, pattern=r"^view_files:")
        )
        
        # Add global error handler
        self.application.add_error_handler(self._error_handler)
    
    async def _start_command(self, update, context) -> ConversationState:
        """Handle /start command"""
        try:
            # Clear any existing user data
            context.user_data.clear()
            
            # Set initial state
            context.user_data['authenticated'] = True
            
            # Get user info
            if self.api_service:
                try:
                    user_info = await self.api_service.user_info()
                    logger.info(f"User info fetched: {user_info}")
                except Exception as e:
                    logger.error(f"Failed to fetch user info: {str(e)}")
            
            # Show main menu
            return await self.main_menu_handler.show_main_menu(update, context)
            
        except Exception as e:
            await self.error_handler.handle_generic_error(update, e, "start_command")
            return ConversationState.MAIN_MENU
    
    async def _cancel_command(self, update, context) -> ConversationState:
        """Handle /cancel command"""
        try:
            await update.message.reply_text(
                "تم إلغاء العملية. يمكنك البدء من جديد باستخدام /start.",
                reply_markup=self.main_menu_handler.get_main_menu_keyboard()
            )
            context.user_data.clear()
            return ConversationHandler.END
            
        except Exception as e:
            await self.error_handler.handle_generic_error(update, e, "cancel_command")
            return ConversationHandler.END
    
    async def _error_handler(self, update, context) -> None:
        """Global error handler"""
        logger.error(f"Exception while handling an update: {context.error}", exc_info=context.error)
        
        if update and update.message:
            await self.error_handler.handle_generic_error(
                update, 
                context.error, 
                "global_error_handler"
            )
    
    async def run(self) -> None:
        """Run the bot"""
        try:
            # Initialize bot
            await self.initialize()
            
            # Start polling
            logger.info("Starting polling...")
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling(allowed_updates=update.ALL_TYPES)
            logger.info("Bot is polling...")
            
            # Keep running until interrupted
            try:
                while True:
                    await asyncio.sleep(3600)
            except KeyboardInterrupt:
                logger.info("Shutting down bot...")
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
                logger.info("Bot stopped.")
                
        except Exception as e:
            logger.error(f"Failed to run bot: {str(e)}")
            raise

async def main():
    """Main entry point"""
    bot = YourVoiceBot()
    await bot.run()

if __name__ == '__main__':
    asyncio.run(main())
