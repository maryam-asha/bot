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
        """Process service menu input"""
        user_input = update.message.text.strip()
        logger.debug(f"Service menu selection: {user_input}")
        
        try:
            if user_input == "طلباتي":
                return await self._show_user_requests(update, context)
            elif user_input == "تقديم طلب":
                return await self._start_new_request(update, context)
            elif user_input == "عودة للقائمة الرئيسية":
                return await self._back_to_main_menu(update, context)
            else:
                await update.message.reply_text(
                    "يرجى اختيار خيار من القائمة.",
                    reply_markup=self._get_service_menu_keyboard()
                )
                return ConversationState.SERVICE_MENU
                
        except Exception as e:
            logger.error(f"Error in service menu: {e}")
            await update.message.reply_text(
                "حدث خطأ في معالجة الطلب. يرجى المحاولة مرة أخرى."
            )
            return ConversationState.SERVICE_MENU
    
    async def _show_user_requests(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> ConversationState:
        """Show user's existing requests"""
        try:
            if not self.api_service:
                await update.message.reply_text(
                    "خدمة API غير متوفرة حالياً.",
                    reply_markup=self._get_service_menu_keyboard()
                )
                return ConversationState.SERVICE_MENU
            
            # Get user requests from API
            requests = await self.api_service.get_user_requests()
            
            if not requests or len(requests) == 0:
                await update.message.reply_text(
                    "لا توجد طلبات حالياً.",
                    reply_markup=self._get_service_menu_keyboard()
                )
                return ConversationState.SERVICE_MENU
            
            # Display requests with pagination
            await self._display_requests_page(update, context, requests, 0)
            return ConversationState.VIEW_REQUESTS
            
        except Exception as e:
            logger.error(f"Error fetching user requests: {e}")
            await update.message.reply_text(
                "حدث خطأ في جلب الطلبات. يرجى المحاولة مرة أخرى.",
                reply_markup=self._get_service_menu_keyboard()
            )
            return ConversationState.SERVICE_MENU
    
    async def _display_requests_page(self, update: Update, context: ContextTypes.DEFAULT_TYPE, requests: list, page: int):
        """Display a page of requests"""
        page_size = 5
        start_idx = page * page_size
        end_idx = start_idx + page_size
        current_requests = requests[start_idx:end_idx]
        
        # Store requests in context for navigation
        context.user_data['all_requests'] = requests
        context.user_data['current_page'] = page
        
        # Create message text
        message = f"📋 طلباتك (الصفحة {page + 1}):\n\n"
        for i, req in enumerate(current_requests):
            message += f"{start_idx + i + 1}. طلب رقم: {req.get('request_number', 'غير محدد')}\n"
            message += f"   النوع: {req.get('request_type', 'غير محدد')}\n"
            message += f"   الحالة: {req.get('status', 'غير محدد')}\n\n"
        
        # Create navigation keyboard
        keyboard = []
        for i, req in enumerate(current_requests):
            keyboard.append([f"عرض الطلب {start_idx + i + 1}"])
        
        # Add navigation buttons
        nav_row = []
        if page > 0:
            nav_row.append("⬅️ السابق")
        if end_idx < len(requests):
            nav_row.append("التالي ➡️")
        if nav_row:
            keyboard.append(nav_row)
        
        keyboard.append(["عودة لقائمة الخدمات"])
        
        await update.message.reply_text(
            message,
            reply_markup=ReplyKeyboardMarkup(
                keyboard=keyboard,
                resize_keyboard=True,
                one_time_keyboard=True
            )
        )
    
    async def _start_new_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> ConversationState:
        """Start the process of submitting a new request"""
        try:
            if not self.api_service:
                await update.message.reply_text(
                    "خدمة API غير متوفرة حالياً.",
                    reply_markup=self._get_service_menu_keyboard()
                )
                return ConversationState.SERVICE_MENU
            
            # Get parent sides to start entity selection
            parent_sides = await self.api_service.get_parent_sides()
            
            if not parent_sides:
                await update.message.reply_text(
                    "لا توجد جهات متاحة حالياً.",
                    reply_markup=self._get_service_menu_keyboard()
                )
                return ConversationState.SERVICE_MENU
            
            # Store parent sides and start entity selection
            context.user_data['parent_sides'] = parent_sides
            context.user_data['current_entity_level'] = 0
            context.user_data['selected_entities'] = []
            
            await self._show_entity_selection(update, context, parent_sides)
            return ConversationState.SELECT_ENTITY
            
        except Exception as e:
            logger.error(f"Error starting new request: {e}")
            await update.message.reply_text(
                "حدث خطأ في بدء الطلب الجديد. يرجى المحاولة مرة أخرى.",
                reply_markup=self._get_service_menu_keyboard()
            )
            return ConversationState.SERVICE_MENU
    
    async def _show_entity_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE, entities: list):
        """Show entity selection options"""
        message = "🏛️ اختر الجهة الرئيسية:\n\n"
        keyboard = []
        
        for i, entity in enumerate(entities):
            name = entity.get('name', f'جهة {i+1}')
            keyboard.append([name])
        
        keyboard.append(["عودة لقائمة الخدمات"])
        
        await update.message.reply_text(
            message,
            reply_markup=ReplyKeyboardMarkup(
                keyboard=keyboard,
                resize_keyboard=True,
                one_time_keyboard=True
            )
        )
    
    async def _back_to_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> ConversationState:
        """Return to main menu"""
        from handlers.main_menu_handler import MainMenuHandler
        
        # Create temporary main menu handler to show menu
        main_handler = MainMenuHandler()
        await main_handler.show_main_menu(update, context)
        return ConversationState.MAIN_MENU
    
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