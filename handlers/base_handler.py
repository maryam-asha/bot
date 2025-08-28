from abc import ABC, abstractmethod
from typing import Optional, Any
from telegram import Update
from telegram.ext import ContextTypes
from config.conversation_states import ConversationState
from utils.error_handler import BotErrorHandler
import logging

logger = logging.getLogger(__name__)

class BaseHandler(ABC):
    """Base class for all conversation handlers using Template Method pattern"""
    
    def __init__(self):
        self.error_handler = BotErrorHandler()
    
    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> ConversationState:
        """Main handler method following Template Method pattern"""
        try:
            # Pre-processing
            await self.pre_process(update, context)
            
            # Main processing
            result = await self.process(update, context)
            
            # Post-processing
            await self.post_process(update, context, result)
            
            return result
            
        except Exception as e:
            await self.error_handler.handle_generic_error(
                update, e, self.__class__.__name__
            )
            return await self.handle_error(update, context, e)
    
    @abstractmethod
    async def process(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> ConversationState:
        """Main processing logic - must be implemented by subclasses"""
        pass
    
    async def pre_process(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Pre-processing logic - can be overridden by subclasses"""
        # Update last activity
        if hasattr(self, 'update_last_activity'):
            self.update_last_activity(context)
        
        # Log incoming message
        if update and update.message:
            logger.debug(f"Processing message in {self.__class__.__name__}: {update.message.text}")
    
    async def post_process(self, update: Update, context: ContextTypes.DEFAULT_TYPE, result: ConversationState) -> None:
        """Post-processing logic - can be overridden by subclasses"""
        # Update conversation state
        if context and hasattr(context, 'user_data'):
            context.user_data['conversation_state'] = result
        
        logger.debug(f"Handler {self.__class__.__name__} completed, returning state: {result}")
    
    async def handle_error(self, update: Update, context: ContextTypes.DEFAULT_TYPE, error: Exception) -> ConversationState:
        """Error handling logic - can be overridden by subclasses"""
        logger.error(f"Error in {self.__class__.__name__}: {str(error)}", exc_info=True)
        return ConversationState.MAIN_MENU
    
    def update_last_activity(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Update last activity timestamp"""
        if context and hasattr(context, 'user_data'):
            from datetime import datetime
            context.user_data['last_activity'] = datetime.now()
    
    def get_user_data(self, context: ContextTypes.DEFAULT_TYPE, key: str, default: Any = None) -> Any:
        """Safely get user data from context"""
        if context and hasattr(context, 'user_data'):
            return context.user_data.get(key, default)
        return default
    
    def set_user_data(self, context: ContextTypes.DEFAULT_TYPE, key: str, value: Any) -> None:
        """Safely set user data in context"""
        if context and hasattr(context, 'user_data'):
            context.user_data[key] = value
