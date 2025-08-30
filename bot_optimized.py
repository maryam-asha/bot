import logging
import asyncio
from telegram.ext import Application, ContextTypes, CommandHandler, MessageHandler, filters, ConversationHandler, CallbackQueryHandler
from telegram import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from datetime import datetime, timedelta
from services.api_service import ApiService
from forms.form_model import FormAttribute, FormDocument, DynamicForm
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from handlers.base_handler import BaseHandler
from handlers.main_menu_handler import MainMenuHandler
from keyboards.base_keyboard import BaseKeyboard
from config.conversation_states import ConversationState, get_previous_state
from config.settings import settings
from utils.performance_monitor import performance_monitor, monitor_async_performance
from utils.cache_manager import cache_manager
import re
from typing import List, Union, Optional
import io
import httpx
import json
import signal
import sys

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class OptimizedBot:
    """Optimized Telegram bot with performance monitoring and connection pooling"""
    
    def __init__(self):
        self.api_service: Optional[ApiService] = None
        self.application: Optional[Application] = None
        self.keyboard = BaseKeyboard()
        self.MOBILE_PREFIX = f"+{settings.country_code}"
        self.MOBILE_LENGTH = settings.mobile_length
        self.MOBILE_CODE = settings.mobile_code
        self.USERNAME_HINT = settings.username_hint
        self.MAIN_MENU_BUTTON = "⏩ العودةإلى القائمة الرئيسية"
        
        self.MAIN_MENU_OPTIONS = ["حول المنصة", "حول الوزارة", "حول الشركة المطورة", "سمعنا صوتك"]
        self.MAIN_MENU_RESPONSES = {
            "حول المنصة": "منصة صوتك هي المنصة الأولى للمواطنين للتعبير عن آرائهم ومقترحاتهم وتقديم شكاويهم في كل المواضيع والخدمات والجهات العاملة تحت وزارة التقانة والاتصالات للجمهورية العربية السورية وقريباً في جميع الوزارات",
            "حول الوزارة": "تتولى وزارة الاتصالات وتقانة المعلومات في الجمهورية العربية السورية بموجب قواعد تنظيمها مهام متعددة تشمل: تنفيذ السياسات العامة في قطاعات الاتصالات والبريد وتقانة المعلومات، تنظيم وتطوير هذه القطاعات، دعم صناعة البرمجيات والخدمات الرقمية، تشجيع الاستثمار والشراكات بين القطاعين العام والخاص، وضع الخطط اللازمة للتحول الرقمي وضمان أمن المعلومات، المشاركة في المشاريع الدولية والإقليمية، بناء القدرات الفنية والعلمية عبر التدريب ودعم البحث العلمي، ورفع الوعي بأهمية الاتصالات وتقانة المعلومات في التنمية الاقتصادية والاجتماعية",
            "حول الشركة المطورة": "مجموعة أوتوماتا4 هي شركة إقليمية مكرسة لتقديم حلول وخدمات استشارية مخصصة عالية الجودة لتكنولوجيا المعلومات..."
        }
        
        # Performance monitoring
        performance_monitor.enable_tracemalloc()
        
    @monitor_async_performance
    async def initialize(self):
        """Initialize the bot with performance monitoring"""
        try:
            # Start cache manager
            await cache_manager.start()
            
            # Initialize API service
            self.api_service = ApiService()
            await self.api_service.initialize_urls()
            
            # Build application with optimized settings
            self.application = Application.builder().token(settings.telegram_token).build()
            
            # Setup handlers
            await self._setup_handlers()
            
            logger.info("Bot initialization complete")
            
        except Exception as e:
            logger.error(f"Failed to initialize bot: {str(e)}")
            raise
            
    async def _setup_handlers(self):
        """Setup conversation handlers with optimized patterns"""
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', self.start)],
            states={
                ConversationState.MAIN_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.main_menu)],
                ConversationState.SERVICE_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.service_menu)],
                ConversationState.ENTER_MOBILE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.enter_mobile)],
                ConversationState.ENTER_OTP: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.enter_otp)],
                ConversationState.SELECT_REQUEST_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.select_request_type)],
                ConversationState.SELECT_COMPLAINT_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.select_subject)],
                ConversationState.SELECT_COMPLIMENT_SIDE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.select_compliment_side)],
                ConversationState.FILL_FORM: [
                    MessageHandler(filters.LOCATION, self.handle_location),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.fill_form),
                    MessageHandler(filters.ATTACHMENT, self.fill_form),
                ],
                ConversationState.SELECT_SERVICE_CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.select_service_category)],
                ConversationState.COLLECT_FORM_FIELD: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.collect_form_field)],
                ConversationState.CONFIRM_SUBMISSION: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.confirm_submission)],
                ConversationState.SELECT_REQUEST_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.select_request_number)],
                ConversationState.SELECT_SERVICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.select_service)],
                ConversationState.SELECT_SUBJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.select_subject)],
                ConversationState.SELECT_OTHER_SUBJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.select_other_subject)],
                ConversationState.SELECT_TIME_AM_PM: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.select_time_am_pm)],
            },
            fallbacks=[CommandHandler('cancel', self.cancel)]
        )
        
        self.application.add_handler(conv_handler)
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.main_menu_handler))
        self.application.add_handler(CallbackQueryHandler(self.handle_view_file, pattern=r"^view_files:"))
        
    @monitor_async_performance
    async def create_reply_keyboard(self, buttons: List[List[str]], include_back=True, include_main_menu=True, one_time=True) -> ReplyKeyboardMarkup:
        """Create reply keyboard with optimized logic"""
        keyboard = [row[:] for row in buttons]
        
        # Remove existing back and main menu buttons
        for row in keyboard:
            if "▶️ الرجوع" in row:
                row.remove("▶️ الرجوع")
            if self.MAIN_MENU_BUTTON in row:
                row.remove(self.MAIN_MENU_BUTTON)
                
        keyboard = [row for row in keyboard if row]

        # Add back button if needed
        if include_back and any("التالي" in row for row in keyboard):
            for row in keyboard:
                if "التالي" in row and "▶️ الرجوع" not in row:
                    row.insert(1, "▶️ الرجوع")
                    break
        elif include_back:
            if include_main_menu:
                keyboard.append(["▶️ الرجوع", self.MAIN_MENU_BUTTON])
            else:
                keyboard.append(["▶️ الرجوع"])

        # Add main menu button if needed
        if include_main_menu and not any(self.MAIN_MENU_BUTTON in row for row in keyboard):
            keyboard.append([self.MAIN_MENU_BUTTON])

        return ReplyKeyboardMarkup(
            keyboard=keyboard,
            resize_keyboard=True,
            one_time_keyboard=one_time
        )

    @monitor_async_performance
    async def send_error_message(self, update: Update, message: str, field=None, keyboard_buttons: List[List[str]] = None) -> None:
        """Send error message with optimized keyboard creation"""
        keyboard = keyboard_buttons or [['▶️ الرجوع', self.MAIN_MENU_BUTTON]]
        await update.message.reply_text(
            message,
            reply_markup=await self.create_reply_keyboard(keyboard, include_back=True, include_main_menu=True)
        )

    @monitor_async_performance
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Start command handler"""
        await self.show_main_menu(update, context, "مرحباً بك في منصة صوتك! 👋")
        return ConversationState.MAIN_MENU

    @monitor_async_performance
    async def main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Main menu handler with caching"""
        text = update.message.text
        
        if text in self.MAIN_MENU_OPTIONS:
            response = self.MAIN_MENU_RESPONSES.get(text, "معلومات غير متوفرة")
            await update.message.reply_text(response, reply_markup=await self.get_main_menu_keyboard())
            return ConversationState.MAIN_MENU
        elif text == "الخدمات":
            return await self.service_menu(update, context)
        else:
            await self.send_error_message(update, "يرجى اختيار خيار من القائمة.")
            return ConversationState.MAIN_MENU

    async def get_main_menu_keyboard(self):
        """Get main menu keyboard with caching"""
        keyboard = [[option] for option in self.MAIN_MENU_OPTIONS]
        keyboard.append(["الخدمات"])
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

    @monitor_async_performance
    async def service_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Service menu handler with authentication check"""
        if not context.user_data.get('user_authenticated'):
            await update.message.reply_text(
                "يرجى إدخال رقم الهاتف للمتابعة:",
                reply_markup=ReplyKeyboardRemove()
            )
            return ConversationState.ENTER_MOBILE
        else:
            return await self.show_service_options(update, context)

    async def show_service_options(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Show service options"""
        keyboard = [["شكوى"], ["شكر وتقدير"], ["استفسار"], ["اقتراح"]]
        await update.message.reply_text(
            "اختر نوع الطلب:",
            reply_markup=await self.create_reply_keyboard(keyboard, include_back=True, include_main_menu=True)
        )
        return ConversationState.SELECT_REQUEST_TYPE

    @monitor_async_performance
    async def enter_mobile(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Mobile number input handler with validation"""
        mobile = update.message.text.strip()
        
        # Validate mobile number
        if not mobile.startswith(self.MOBILE_CODE):
            await self.send_error_message(update, f"يرجى إدخال رقم هاتف صحيح يبدأ بـ {self.MOBILE_CODE}")
            return ConversationState.ENTER_MOBILE
            
        if len(mobile) != self.MOBILE_LENGTH:
            await self.send_error_message(update, f"يرجى إدخال رقم هاتف من {self.MOBILE_LENGTH} أرقام")
            return ConversationState.ENTER_MOBILE
            
        # Store mobile number
        context.user_data['mobile'] = mobile
        
        # Request OTP
        try:
            await self.api_service.request_otp(mobile)
            await update.message.reply_text(
                f"تم إرسال رمز التحقق إلى {mobile}",
                reply_markup=ReplyKeyboardRemove()
            )
            return ConversationState.ENTER_OTP
        except Exception as e:
            logger.error(f"Error requesting OTP: {e}")
            await self.send_error_message(update, "حدث خطأ في إرسال رمز التحقق. يرجى المحاولة مرة أخرى.")
            return ConversationState.ENTER_MOBILE

    @monitor_async_performance
    async def enter_otp(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """OTP verification handler"""
        otp = update.message.text.strip()
        mobile = context.user_data.get('mobile')
        
        if not mobile:
            await self.send_error_message(update, "يرجى إعادة إدخال رقم الهاتف أولاً.")
            return ConversationState.ENTER_MOBILE
            
        try:
            result = await self.api_service.login_otp(mobile, otp)
            if result.get('status') == 'success':
                context.user_data['user_authenticated'] = True
                await update.message.reply_text(
                    "تم تسجيل الدخول بنجاح! 🎉",
                    reply_markup=await self.get_main_menu_keyboard()
                )
                return ConversationState.MAIN_MENU
            else:
                await self.send_error_message(update, "رمز التحقق غير صحيح. يرجى المحاولة مرة أخرى.")
                return ConversationState.ENTER_OTP
        except Exception as e:
            logger.error(f"Error verifying OTP: {e}")
            await self.send_error_message(update, "حدث خطأ في التحقق من الرمز. يرجى المحاولة مرة أخرى.")
            return ConversationState.ENTER_OTP

    @monitor_async_performance
    async def select_request_type(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Request type selection handler"""
        text = update.message.text
        
        request_types = {
            "شكوى": 1,
            "شكر وتقدير": 2,
            "استفسار": 3,
            "اقتراح": 4
        }
        
        if text in request_types:
            context.user_data['request_type_id'] = request_types[text]
            return await self.select_compliment_side(update, context)
        elif text == "▶️ الرجوع":
            return await self.service_menu(update, context)
        else:
            await self.send_error_message(update, "يرجى اختيار نوع طلب صحيح.")
            return ConversationState.SELECT_REQUEST_TYPE

    @monitor_async_performance
    async def select_compliment_side(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Compliment side selection handler"""
        # This would typically fetch sides from API
        keyboard = [["الجانب الأول"], ["الجانب الثاني"]]
        await update.message.reply_text(
            "اختر الجانب:",
            reply_markup=await self.create_reply_keyboard(keyboard, include_back=True, include_main_menu=True)
        )
        return ConversationState.SELECT_COMPLIMENT_SIDE

    async def handle_location(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Location handler"""
        location = update.message.location
        logger.info(f"Received location: {location}")
        # Handle location data
        return ConversationState.FILL_FORM

    @monitor_async_performance
    async def fill_form(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Form filling handler"""
        # Handle form filling logic
        return ConversationState.FILL_FORM

    async def collect_form_field(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Form field collection handler"""
        return ConversationState.COLLECT_FORM_FIELD

    async def confirm_submission(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Submission confirmation handler"""
        return ConversationState.CONFIRM_SUBMISSION

    async def select_request_number(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Request number selection handler"""
        return ConversationState.SELECT_REQUEST_NUMBER

    async def select_service_category(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Service category selection handler"""
        return ConversationState.SELECT_SERVICE_CATEGORY

    async def select_service(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Service selection handler"""
        return ConversationState.SELECT_SERVICE

    async def select_subject(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Subject selection handler"""
        return ConversationState.SELECT_SUBJECT

    async def select_other_subject(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Other subject selection handler"""
        return ConversationState.SELECT_OTHER_SUBJECT

    async def select_time_am_pm(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Time AM/PM selection handler"""
        return ConversationState.SELECT_TIME_AM_PM

    async def main_menu_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Fallback main menu handler"""
        return await self.main_menu(update, context)

    async def handle_view_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle file view requests"""
        # Handle file viewing logic
        pass

    @monitor_async_performance
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Cancel operation handler"""
        await update.message.reply_text(
            "تم إلغاء العملية. يمكنك البدء من جديد باستخدام /start.",
            reply_markup=await self.get_main_menu_keyboard()
        )
        context.user_data.clear()
        return ConversationHandler.END

    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message: str = None) -> None:
        """Show main menu with optional message"""
        keyboard = await self.get_main_menu_keyboard()
        if message:
            await update.message.reply_text(message, reply_markup=keyboard)
        else:
            await update.message.edit_text("القائمة الرئيسية:", reply_markup=keyboard)

    async def run(self):
        """Run the bot with performance monitoring"""
        try:
            await self.initialize()
            
            # Initialize and start the application
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
            
            logger.info("Bot is running with performance monitoring...")
            
            # Performance monitoring loop
            while True:
                await asyncio.sleep(3600)  # Print stats every hour
                performance_monitor.print_summary()
                
        except KeyboardInterrupt:
            logger.info("Shutting down bot...")
        except Exception as e:
            logger.error(f"Error running bot: {e}")
        finally:
            await self.cleanup()

    async def cleanup(self):
        """Cleanup resources"""
        try:
            if self.application:
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
                
            if self.api_service:
                await self.api_service.close()
                
            await cache_manager.stop()
            performance_monitor.disable_tracemalloc()
            
            logger.info("Bot cleanup complete")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, shutting down...")
    sys.exit(0)

async def main():
    """Main entry point"""
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    bot = OptimizedBot()
    await bot.run()

if __name__ == '__main__':
    asyncio.run(main())