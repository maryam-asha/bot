import logging
from typing import Optional
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes
from config.conversation_states import ConversationState
from handlers.base_handler import BaseHandler
from keyboards.base_keyboard import BaseKeyboard
from utils.error_handler import BotErrorHandler
import logging

logger = logging.getLogger(__name__)

class MainMenuHandler(BaseHandler):
    """Handler for main menu operations"""
    
    MAIN_MENU_OPTIONS = [
        "حول المنصة",
        "حول الوزارة", 
        "حول الشركة المطورة",
        "سمعنا صوتك"
    ]
    
    MAIN_MENU_RESPONSES = {
        "حول المنصة": "منصة صوتك هي المنصة الأولى للمواطنين للتعبير عن آرائهم ومقترحاتهم وتقديم شكاويهم في كل المواضيع والخدمات والجهات العاملة تحت وزارة التقانة والاتصالات للجمهورية العربية السورية وقريباً في جميع الوزارات",
        "حول الوزارة": "تتولى وزارة الاتصالات وتقانة المعلومات في الجمهورية العربية السورية بموجب قواعد تنظيمها مهام متعددة تشمل: تنفيذ السياسات العامة في قطاعات الاتصالات والبريد وتقانة المعلومات، تنظيم وتطوير هذه القطاعات، دعم صناعة البرمجيات والخدمات الرقمية، تشجيع الاستثمار والشراكات بين القطاعين العام والخاص، وضع الخطط اللازمة للتحول الرقمي وضمان أمن المعلومات، المشاركة في المشاريع الدولية والإقليمية، بناء القدرات الفنية والعلمية عبر التدريب ودعم البحث العلمي، ورفع الوعي بأهمية الاتصالات وتقانة المعلومات في التنمية الاقتصادية والاجتماعية",
        "حول الشركة المطورة": "مجموعة أوتوماتا4 هي شركة إقليمية مكرسة لتقديم حلول وخدمات استشارية مخصصة عالية الجودة لتكنولوجيا المعلومات..."
    }
    
    def __init__(self, api_service=None, auth_handler=None):
        super().__init__()
        self.keyboard = BaseKeyboard()
        self.api_service = api_service
        self.auth_handler = auth_handler
    
    async def process(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> ConversationState:
        """Process main menu input"""
        user_input = update.message.text.strip()
        logger.debug(f"Main menu selection: {user_input}")
        
        try:
            # Handle menu options
            if user_input in self.MAIN_MENU_RESPONSES:
                await self._show_info_response(update, context, user_input)
                return ConversationState.MAIN_MENU
            
            # Handle service access - this requires authentication
            elif user_input == "سمعنا صوتك":
                return await self._handle_service_access(update, context)
            
            # Handle invalid input
            else:
                await self._show_invalid_input_message(update, context)
                return ConversationState.MAIN_MENU
                
        except Exception as e:
            await self.error_handler.handle_generic_error(update, e, "main_menu_processing")
            return ConversationState.MAIN_MENU
    
    async def _show_info_response(self, update: Update, context: ContextTypes.DEFAULT_TYPE, option: str) -> None:
        """Show information response for menu option"""
        response_text = self.MAIN_MENU_RESPONSES.get(option, "معلومات غير متوفرة")
        await self.show_main_menu(update, context, response_text)
    
    async def _handle_service_access(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> ConversationState:
        """Handle service access request - requires authentication"""
        # Check authentication status
        if self.auth_handler:
            is_authenticated = await self.auth_handler.is_authenticated(context)
        else:
            # Fallback to user_data check
            is_authenticated = self.get_user_data(context, 'user_authenticated', False)
        
        if is_authenticated:
            logger.info("User authenticated, transitioning to SERVICE_MENU")
            # Update token activity
            if self.auth_handler:
                await self.auth_handler.update_token_activity(context)
            
            await update.message.reply_text(
                "مرحباً بك في قائمة الخدمات! 🚀\n\nاختر ما تريد القيام به:",
                reply_markup=self._get_service_menu_keyboard()
            )
            return ConversationState.SERVICE_MENU
        else:
            logger.info("User not authenticated, starting authentication flow")
            # Start authentication flow
            context.user_data['current_state'] = ConversationState.AUTH_CHECK
            return ConversationState.AUTH_CHECK
    
    async def _show_invalid_input_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show message for invalid input"""
        await self.show_main_menu(update, context, "يرجى اختيار خيار من القائمة.")
    
    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message: Optional[str] = None) -> None:
        """Show main menu with optional message"""
        default_message = "☑️ YourVoiceSyBot v1.0.0\n\nاختر من القائمة أدناه:"
        display_message = message or default_message
        
        await update.message.reply_text(
            display_message,
            reply_markup=self.get_main_menu_keyboard()
        )
    
    def get_main_menu_keyboard(self) -> ReplyKeyboardMarkup:
        """Get main menu keyboard"""
        keyboard = [[option] for option in self.MAIN_MENU_OPTIONS]
        return ReplyKeyboardMarkup(
            keyboard=keyboard,
            resize_keyboard=True,
            one_time_keyboard=True
        )
    
    def _get_service_menu_keyboard(self) -> ReplyKeyboardMarkup:
        """Get service menu keyboard"""
        keyboard = [
            ["طلباتي", "تقديم طلب"],
            ["عودة للقائمة الرئيسية"]
        ]
        return ReplyKeyboardMarkup(
            keyboard=keyboard,
            resize_keyboard=True,
            one_time_keyboard=True
        )
