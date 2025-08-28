import logging
from telegram import Update
from telegram.ext import ContextTypes
from config.conversation_states import ConversationState
from handlers.main_menu_handler import MainMenuHandler
from handlers.service_menu_handler import ServiceMenuHandler
from handlers.form_handler import FormHandler
from handlers.auth_handler import AuthHandler
from handlers.request_handler import RequestHandler
from utils.performance_monitor import monitor_async_performance

logger = logging.getLogger(__name__)

class MessageRouter:
    """Router لتوجيه الرسائل للهاندلر الصحيح"""
    
    def __init__(self, api_service):
        self.api_service = api_service
        
        # Initialize all handlers
        self.main_menu_handler = MainMenuHandler(api_service)
        self.service_menu_handler = ServiceMenuHandler(api_service)
        self.form_handler = FormHandler(api_service)
        self.auth_handler = AuthHandler(api_service)
        self.request_handler = RequestHandler(api_service)
        
        # Define state to handler mapping
        self.state_handlers = {
            ConversationState.MAIN_MENU: self.main_menu_handler,
            ConversationState.SERVICE_MENU: self.service_menu_handler,
            ConversationState.ENTER_MOBILE: self.auth_handler,
            ConversationState.ENTER_OTP: self.auth_handler,
            ConversationState.SELECT_REQUEST_TYPE: self.request_handler,
            ConversationState.SELECT_COMPLIMENT_SIDE: self.request_handler,
            ConversationState.SELECT_SUBJECT: self.request_handler,
            ConversationState.SELECT_OTHER_SUBJECT: self.request_handler,
            ConversationState.SELECT_SERVICE_CATEGORY: self.request_handler,
            ConversationState.SELECT_SERVICE: self.request_handler,
            ConversationState.FILL_FORM: self.form_handler,
            ConversationState.COLLECT_FORM_FIELD: self.form_handler,
            ConversationState.CONFIRM_SUBMISSION: self.form_handler,
            ConversationState.SELECT_REQUEST_NUMBER: self.service_menu_handler,
        }
        
    @monitor_async_performance
    async def route_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> ConversationState:
        """Route message to appropriate handler based on current state"""
        try:
            # Get current state from context
            current_state = context.user_data.get('current_state', ConversationState.MAIN_MENU)
            
            # Get appropriate handler for current state
            handler = self.state_handlers.get(current_state)
            
            if not handler:
                logger.warning(f"No handler found for state: {current_state}")
                return ConversationState.MAIN_MENU
                
            logger.debug(f"Routing message to {handler.__class__.__name__} for state: {current_state}")
            
            # Process message with appropriate handler
            new_state = await handler.process(update, context)
            
            # Update context with new state
            context.user_data['current_state'] = new_state
            
            return new_state
            
        except Exception as e:
            logger.error(f"Error routing message: {e}")
            # Fallback to main menu on error
            context.user_data['current_state'] = ConversationState.MAIN_MENU
            return ConversationState.MAIN_MENU
            
    async def handle_special_commands(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> ConversationState:
        """Handle special commands (start, cancel, etc.)"""
        text = update.message.text
        
        if text == '/start':
            # Reset to main menu
            context.user_data.clear()
            context.user_data['current_state'] = ConversationState.MAIN_MENU
            return await self.main_menu_handler.show_main_menu(update, context, "مرحباً بك في منصة صوتك! 👋")
            
        elif text == '/cancel':
            # Cancel current operation
            context.user_data.clear()
            context.user_data['current_state'] = ConversationState.MAIN_MENU
            return await self.main_menu_handler.show_main_menu(update, context, "تم إلغاء العملية. يمكنك البدء من جديد.")
            
        elif text == '/help':
            # Show help message
            help_text = """
🤖 مساعدة البوت:

/start - بدء البوت من جديد
/cancel - إلغاء العملية الحالية
/help - عرض هذه المساعدة
/location - إرسال الموقع
            """
            await update.message.reply_text(help_text)
            return context.user_data.get('current_state', ConversationState.MAIN_MENU)
            
        else:
            # Route to appropriate handler
            return await self.route_message(update, context)
            
    async def handle_location(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> ConversationState:
        """Handle location updates"""
        current_state = context.user_data.get('current_state')
        
        if current_state == ConversationState.FILL_FORM:
            # Route location to form handler
            return await self.form_handler._handle_location_input(update, context)
        else:
            # Store location in context for later use
            location = update.message.location
            context.user_data['user_location'] = {
                'latitude': location.latitude,
                'longitude': location.longitude
            }
            
            await update.message.reply_text(
                "تم حفظ موقعك بنجاح! 📍",
                reply_markup=None
            )
            
            return current_state
            
    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> ConversationState:
        """Handle document uploads"""
        current_state = context.user_data.get('current_state')
        
        if current_state == ConversationState.FILL_FORM:
            # Route document to form handler
            return await self.form_handler._handle_document_input(update, context)
        else:
            await update.message.reply_text(
                "لا يمكن رفع الملفات في هذه المرحلة. يرجى الانتقال إلى تعبئة النموذج أولاً."
            )
            return current_state
            
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> ConversationState:
        """Handle photo uploads"""
        current_state = context.user_data.get('current_state')
        
        if current_state == ConversationState.FILL_FORM:
            # Convert photo to document and route to form handler
            photo = update.message.photo[-1]  # Get highest resolution
            # Convert photo to document format
            update.message.document = type('Document', (), {
                'file_id': photo.file_id,
                'file_name': f"photo_{photo.file_id}.jpg"
            })()
            return await self.form_handler._handle_document_input(update, context)
        else:
            await update.message.reply_text(
                "لا يمكن رفع الصور في هذه المرحلة. يرجى الانتقال إلى تعبئة النموذج أولاً."
            )
            return current_state
            
    async def handle_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> ConversationState:
        """Handle voice messages"""
        current_state = context.user_data.get('current_state')
        
        if current_state == ConversationState.FILL_FORM:
            # Convert voice to document and route to form handler
            voice = update.message.voice
            update.message.document = type('Document', (), {
                'file_id': voice.file_id,
                'file_name': f"voice_{voice.file_id}.ogg"
            })()
            return await self.form_handler._handle_document_input(update, context)
        else:
            await update.message.reply_text(
                "لا يمكن رفع الرسائل الصوتية في هذه المرحلة. يرجى الانتقال إلى تعبئة النموذج أولاً."
            )
            return current_state
            
    async def get_handler_for_state(self, state: ConversationState):
        """Get handler for specific state"""
        return self.state_handlers.get(state)
        
    async def set_state_handler(self, state: ConversationState, handler):
        """Set custom handler for specific state"""
        self.state_handlers[state] = handler
        
    def get_available_states(self):
        """Get list of available states with handlers"""
        return list(self.state_handlers.keys())