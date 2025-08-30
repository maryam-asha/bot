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
        self.auth_handler = AuthHandler(api_service)
        self.main_menu_handler = MainMenuHandler(api_service, self.auth_handler)
        self.service_menu_handler = ServiceMenuHandler(api_service)
        self.form_handler = FormHandler(api_service)
        self.request_handler = RequestHandler(api_service)
        
        # Define state to handler mapping
        self.state_handlers = {
            # Authentication states
            ConversationState.AUTH_CHECK: self.auth_handler,
            ConversationState.ENTER_MOBILE: self.auth_handler,
            ConversationState.ENTER_OTP: self.auth_handler,
            
            # Main menu
            ConversationState.MAIN_MENU: self.main_menu_handler,
            
            # Service menu
            ConversationState.SERVICE_MENU: self.service_menu_handler,
            
            # View requests
            ConversationState.VIEW_REQUESTS: self.service_menu_handler,
            ConversationState.VIEW_REQUEST_DETAILS: self.service_menu_handler,
            
            # Submit new request
            ConversationState.SELECT_ENTITY: self.request_handler,
            ConversationState.SELECT_ENTITY_CHILDREN: self.request_handler,
            ConversationState.SELECT_REQUEST_TYPE: self.request_handler,
            ConversationState.SELECT_SUBJECTS: self.request_handler,
            ConversationState.SELECT_SERVICE_CATEGORY: self.request_handler,
            ConversationState.SELECT_SERVICE: self.request_handler,
            
            # Form handling
            ConversationState.FILL_FORM: self.form_handler,
            ConversationState.COLLECT_FORM_FIELD: self.form_handler,
            ConversationState.CONFIRM_SUBMISSION: self.form_handler,
            
            # Legacy states (keeping for backward compatibility)
            ConversationState.SELECT_COMPLAINT_TYPE: self.request_handler,
            ConversationState.SELECT_SUBJECT: self.request_handler,
            ConversationState.SELECT_COMPLAINT_SUBJECT: self.request_handler,
            ConversationState.SELECT_OTHER_SUBJECT: self.request_handler,
            ConversationState.SELECT_TIME_AM_PM: self.form_handler,
            ConversationState.SELECT_REQUEST_NUMBER: self.service_menu_handler,
            ConversationState.SELECT_SIDE: self.request_handler,
            ConversationState.SELECT_SERVICE_HIERARCHY: self.request_handler,
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
            # Start with authentication check
            context.user_data.clear()
            context.user_data['current_state'] = ConversationState.AUTH_CHECK
            return await self.auth_handler._check_auth_status(update, context)
            
        elif text == '/cancel':
            # Cancel current operation and return to main menu
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

**تدفق العمل:**
1. تسجيل الدخول (إذا لم تكن مصادق عليه)
2. اختيار "سمعنا صوتك"
3. عرض الطلبات أو تقديم طلب جديد
4. ملء النموذج وتأكيد الإرسال
            """
            await update.message.reply_text(help_text)
            return context.user_data.get('current_state', ConversationState.MAIN_MENU)
            
        else:
            # Route to appropriate handler
            return await self.route_message(update, context)
            
    async def handle_location(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> ConversationState:
        """Handle location updates"""
        current_state = context.user_data.get('current_state')
        
        # Store location in context for later use
        location = update.message.location
        context.user_data['user_location'] = {
            'latitude': location.latitude,
            'longitude': location.longitude
        }
        
        if current_state == ConversationState.FILL_FORM:
            # Route location to form handler
            await update.message.reply_text(
                "تم حفظ موقعك بنجاح! 📍",
                reply_markup=None
            )
            return ConversationState.FILL_FORM
        else:
            await update.message.reply_text(
                "تم حفظ موقعك بنجاح! 📍",
                reply_markup=None
            )
            return current_state
            
    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> ConversationState:
        """Handle document uploads"""
        current_state = context.user_data.get('current_state')
        
        await update.message.reply_text(
            "تم استقبال الملف بنجاح! 📄",
            reply_markup=None
        )
        
        if current_state == ConversationState.FILL_FORM:
            # Route document to form handler
            return ConversationState.FILL_FORM
        else:
            return current_state
            
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> ConversationState:
        """Handle photo uploads"""
        current_state = context.user_data.get('current_state')
        
        await update.message.reply_text(
            "تم استقبال الصورة بنجاح! 📷",
            reply_markup=None
        )
        
        if current_state == ConversationState.FILL_FORM:
            # Route photo to form handler
            return ConversationState.FILL_FORM
        else:
            return current_state
            
    async def handle_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> ConversationState:
        """Handle voice messages"""
        current_state = context.user_data.get('current_state')
        
        await update.message.reply_text(
            "تم استقبال الرسالة الصوتية بنجاح! 🎤",
            reply_markup=None
        )
        
        if current_state == ConversationState.FILL_FORM:
            # Route voice to form handler
            return ConversationState.FILL_FORM
        else:
            return current_state
            
    def get_handler_for_state(self, state: ConversationState):
        """Get handler for specific state"""
        return self.state_handlers.get(state)
        
    def set_state_handler(self, state: ConversationState, handler):
        """Set handler for specific state"""
        self.state_handlers[state] = handler
        
    def get_available_states(self):
        """Get list of available states"""
        return list(self.state_handlers.keys())