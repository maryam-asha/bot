import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes
from config.conversation_states import ConversationState
from handlers.base_handler import BaseHandler
from utils.performance_monitor import monitor_async_performance

logger = logging.getLogger(__name__)

class ServiceMenuHandler(BaseHandler):
    """Handler for service menu operations"""
    
    def __init__(self, api_service=None):
        super().__init__()
        self.api_service = api_service
        
    @monitor_async_performance
    async def process(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> ConversationState:
        """Process service menu interactions"""
        text = update.message.text
        
        # Check if user is authenticated
        if not context.user_data.get('user_authenticated'):
            await update.message.reply_text(
                "يرجى إدخال رقم الهاتف للمتابعة:",
                reply_markup=ReplyKeyboardRemove()
            )
            return ConversationState.ENTER_MOBILE
        
        # Handle service options
        if text == "الخدمات":
            return await self._show_service_options(update, context)
        elif text == "عرض طلباتي":
            return await self._show_user_requests(update, context)
        elif text == "▶️ الرجوع":
            return await self._back_to_main_menu(update, context)
        else:
            await update.message.reply_text(
                "يرجى اختيار خيار صحيح من القائمة.",
                reply_markup=await self._get_service_menu_keyboard()
            )
            return ConversationState.SERVICE_MENU
            
    async def _show_service_options(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> ConversationState:
        """Show service type options"""
        keyboard = [["شكوى"], ["شكر وتقدير"], ["استفسار"], ["اقتراح"]]
        
        await update.message.reply_text(
            "اختر نوع الطلب:",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=keyboard,
                resize_keyboard=True,
                one_time_keyboard=True
            )
        )
        return ConversationState.SELECT_REQUEST_TYPE
        
    async def _show_user_requests(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> ConversationState:
        """Show user's previous requests"""
        try:
            # Get user requests from API
            requests_data = await self.api_service.get_user_requests()
            
            if not requests_data.get('data'):
                await update.message.reply_text(
                    "لا توجد طلبات سابقة.",
                    reply_markup=await self._get_service_menu_keyboard()
                )
                return ConversationState.SERVICE_MENU
                
            # Format and display requests
            requests_list = requests_data['data']
            if len(requests_list) <= 5:
                message = "طلباتك السابقة:\n\n"
                for req in requests_list:
                    message += f"📋 {req.get('request_number', 'N/A')}\n"
                    message += f"   النوع: {req.get('request_type_name', 'غير محدد')}\n"
                    message += f"   الحالة: {req.get('status_name', 'غير محدد')}\n"
                    message += f"   التاريخ: {req.get('created_at', 'غير محدد')}\n\n"
                    
                keyboard = [["عرض تفاصيل الطلب"]]
            else:
                message = f"لديك {len(requests_list)} طلب. عرض أول 5 طلبات:\n\n"
                for req in requests_list[:5]:
                    message += f"📋 {req.get('request_number', 'N/A')}\n"
                    message += f"   النوع: {req.get('request_type_name', 'غير محدد')}\n"
                    message += f"   الحالة: {req.get('status_name', 'غير محدد')}\n\n"
                    
                keyboard = [["عرض تفاصيل الطلب"], ["عرض المزيد"]]
                
            # Store requests in context for later use
            context.user_data['user_requests'] = requests_list
            
            await update.message.reply_text(
                message,
                reply_markup=ReplyKeyboardMarkup(
                    keyboard=keyboard,
                    resize_keyboard=True,
                    one_time_keyboard=True
                )
            )
            return ConversationState.SELECT_REQUEST_NUMBER
            
        except Exception as e:
            logger.error(f"Error fetching user requests: {e}")
            await update.message.reply_text(
                "حدث خطأ في جلب الطلبات. يرجى المحاولة مرة أخرى.",
                reply_markup=await self._get_service_menu_keyboard()
            )
            return ConversationState.SERVICE_MENU
            
    async def _get_service_menu_keyboard(self):
        """Get service menu keyboard"""
        keyboard = [
            ["الخدمات", "عرض طلباتي"],
            ["▶️ الرجوع"]
        ]
        return ReplyKeyboardMarkup(
            keyboard=keyboard,
            resize_keyboard=True,
            one_time_keyboard=True
        )
        
    async def _back_to_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> ConversationState:
        """Return to main menu"""
        await update.message.reply_text(
            "القائمة الرئيسية:",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[
                    ["حول المنصة"], ["حول الوزارة"], ["حول الشركة المطورة"], ["سمعنا صوتك"],
                    ["الخدمات"],
                    ["▶️ الرجوع"]
                ],
                resize_keyboard=True,
                one_time_keyboard=True
            )
        )
        return ConversationState.MAIN_MENU