import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from config.conversation_states import ConversationState
from handlers.base_handler import BaseHandler
from utils.performance_monitor import monitor_async_performance

logger = logging.getLogger(__name__)

class RequestHandler(BaseHandler):
    """Handler for request type selection and management"""
    
    def __init__(self, api_service):
        super().__init__()
        self.api_service = api_service
        
    @monitor_async_performance
    async def process(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> ConversationState:
        """Process request type selection interactions"""
        text = update.message.text
        
        if text == "▶️ الرجوع":
            return ConversationState.SERVICE_MENU
        elif text == "⏩ العودةإلى القائمة الرئيسية":
            return ConversationState.MAIN_MENU
        else:
            return await self._handle_request_type_selection(update, context)
            
    async def _handle_request_type_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> ConversationState:
        """Handle request type selection"""
        text = update.message.text
        
        request_types = {
            "شكوى": 1,
            "شكر وتقدير": 2,
            "استفسار": 3,
            "اقتراح": 4
        }
        
        if text in request_types:
            context.user_data['request_type_id'] = request_types[text]
            return await self._show_side_selection(update, context)
        else:
            await update.message.reply_text(
                "يرجى اختيار نوع طلب صحيح.",
                reply_markup=ReplyKeyboardMarkup(
                    keyboard=[["شكوى"], ["شكر وتقدير"], ["استفسار"], ["اقتراح"], ["▶️ الرجوع"]],
                    resize_keyboard=True,
                    one_time_keyboard=True
                )
            )
            return ConversationState.SELECT_REQUEST_TYPE
            
    async def _show_side_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> ConversationState:
        """Show side selection options"""
        try:
            # Get sides from API
            sides_data = await self.api_service.get_parent_sides()
            
            if not sides_data.get('data'):
                await update.message.reply_text(
                    "لا توجد خيارات متاحة حالياً.",
                    reply_markup=ReplyKeyboardMarkup(
                        keyboard=[["▶️ الرجوع"]],
                        resize_keyboard=True,
                        one_time_keyboard=True
                    )
                )
                return ConversationState.SELECT_REQUEST_TYPE
                
            # Format sides for keyboard
            sides = sides_data['data']
            keyboard = []
            for side in sides:
                keyboard.append([side.get('name', 'غير محدد')])
                
            # Add navigation buttons
            keyboard.append(["▶️ الرجوع", "⏩ العودةإلى القائمة الرئيسية"])
            
            await update.message.reply_text(
                "اختر الجانب:",
                reply_markup=ReplyKeyboardMarkup(
                    keyboard=keyboard,
                    resize_keyboard=True,
                    one_time_keyboard=True
                )
            )
            
            # Store sides in context
            context.user_data['available_sides'] = sides
            
            return ConversationState.SELECT_COMPLIMENT_SIDE
            
        except Exception as e:
            logger.error(f"Error fetching sides: {e}")
            await update.message.reply_text(
                "حدث خطأ في جلب الخيارات. يرجى المحاولة مرة أخرى.",
                reply_markup=ReplyKeyboardMarkup(
                    keyboard=[["▶️ الرجوع"]],
                    resize_keyboard=True,
                    one_time_keyboard=True
                )
            )
            return ConversationState.SELECT_REQUEST_TYPE
            
    async def handle_side_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> ConversationState:
        """Handle side selection"""
        text = update.message.text
        
        if text == "▶️ الرجوع":
            return ConversationState.SELECT_REQUEST_TYPE
        elif text == "⏩ العودةإلى القائمة الرئيسية":
            return ConversationState.MAIN_MENU
            
        # Find selected side
        available_sides = context.user_data.get('available_sides', [])
        selected_side = None
        
        for side in available_sides:
            if side.get('name') == text:
                selected_side = side
                break
                
        if not selected_side:
            await update.message.reply_text(
                "يرجى اختيار جانب صحيح.",
                reply_markup=ReplyKeyboardMarkup(
                    keyboard=[["▶️ الرجوع"]],
                    resize_keyboard=True,
                    one_time_keyboard=True
                )
            )
            return ConversationState.SELECT_COMPLIMENT_SIDE
            
        # Store selected side
        context.user_data['selected_side_id'] = selected_side.get('id')
        
        # Check if side has children
        if selected_side.get('has_children', False):
            return await self._show_child_sides(update, context, selected_side.get('id'))
        else:
            return await self._show_subjects(update, context, selected_side.get('id'))
            
    async def _show_child_sides(self, update: Update, context: ContextTypes.DEFAULT_TYPE, parent_id: int) -> ConversationState:
        """Show child sides for selection"""
        try:
            children_data = await self.api_service.get_side_children(parent_id)
            
            if not children_data.get('data'):
                return await self._show_subjects(update, context, parent_id)
                
            children = children_data['data']
            keyboard = []
            
            for child in children:
                keyboard.append([child.get('name', 'غير محدد')])
                
            keyboard.append(["▶️ الرجوع"])
            
            await update.message.reply_text(
                "اختر الجانب الفرعي:",
                reply_markup=ReplyKeyboardMarkup(
                    keyboard=keyboard,
                    resize_keyboard=True,
                    one_time_keyboard=True
                )
            )
            
            context.user_data['child_sides'] = children
            return ConversationState.SELECT_COMPLIMENT_SIDE
            
        except Exception as e:
            logger.error(f"Error fetching child sides: {e}")
            return await self._show_subjects(update, context, parent_id)
            
    async def _show_subjects(self, update: Update, context: ContextTypes.DEFAULT_TYPE, side_id: int) -> ConversationState:
        """Show subjects for the selected side"""
        try:
            request_type_id = context.user_data.get('request_type_id')
            subjects_data = await self.api_service.get_request_type_subjects(request_type_id, side_id)
            
            if not subjects_data.get('data'):
                await update.message.reply_text(
                    "لا توجد مواضيع متاحة لهذا الجانب.",
                    reply_markup=ReplyKeyboardMarkup(
                        keyboard=[["▶️ الرجوع"]],
                        resize_keyboard=True,
                        one_time_keyboard=True
                    )
                )
                return ConversationState.SELECT_COMPLIMENT_SIDE
                
            subjects = subjects_data['data']
            keyboard = []
            
            for subject in subjects:
                keyboard.append([subject.get('name', 'غير محدد')])
                
            keyboard.append(["▶️ الرجوع"])
            
            await update.message.reply_text(
                "اختر الموضوع:",
                reply_markup=ReplyKeyboardMarkup(
                    keyboard=keyboard,
                    resize_keyboard=True,
                    one_time_keyboard=True
                )
            )
            
            context.user_data['available_subjects'] = subjects
            return ConversationState.SELECT_SUBJECT
            
        except Exception as e:
            logger.error(f"Error fetching subjects: {e}")
            await update.message.reply_text(
                "حدث خطأ في جلب المواضيع. يرجى المحاولة مرة أخرى.",
                reply_markup=ReplyKeyboardMarkup(
                    keyboard=[["▶️ الرجوع"]],
                    resize_keyboard=True,
                    one_time_keyboard=True
                )
            )
            return ConversationState.SELECT_COMPLIMENT_SIDE
            
    async def handle_subject_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> ConversationState:
        """Handle subject selection"""
        text = update.message.text
        
        if text == "▶️ الرجوع":
            return ConversationState.SELECT_COMPLIMENT_SIDE
            
        # Find selected subject
        available_subjects = context.user_data.get('available_subjects', [])
        selected_subject = None
        
        for subject in available_subjects:
            if subject.get('name') == text:
                selected_subject = subject
                break
                
        if not selected_subject:
            await update.message.reply_text(
                "يرجى اختيار موضوع صحيح.",
                reply_markup=ReplyKeyboardMarkup(
                    keyboard=[["▶️ الرجوع"]],
                    resize_keyboard=True,
                    one_time_keyboard=True
                )
            )
            return ConversationState.SELECT_SUBJECT
            
        # Store selected subject
        context.user_data['selected_subject_id'] = selected_subject.get('id')
        
        # Check if subject requires additional selection
        if selected_subject.get('requires_additional_selection', False):
            return await self._show_additional_selection(update, context)
        else:
            return await self._load_form(update, context)
            
    async def _show_additional_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> ConversationState:
        """Show additional selection options if needed"""
        # This would show additional options like service categories, etc.
        keyboard = [["خيار 1"], ["خيار 2"], ["خيار 3"], ["▶️ الرجوع"]]
        
        await update.message.reply_text(
            "اختر الخيار الإضافي:",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=keyboard,
                resize_keyboard=True,
                one_time_keyboard=True
            )
        )
        
        return ConversationState.SELECT_OTHER_SUBJECT
        
    async def _load_form(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> ConversationState:
        """Load form for the selected request"""
        try:
            request_type_id = context.user_data.get('request_type_id')
            subject_id = context.user_data.get('selected_subject_id')
            side_id = context.user_data.get('selected_side_id')
            
            # Get form data from API
            form_data = await self.api_service.get_form_data(
                request_type_id=request_type_id,
                request_subject_id=subject_id,
                side_id=side_id
            )
            
            if not form_data.get('data'):
                await update.message.reply_text(
                    "لا يوجد نموذج متاح لهذا الطلب.",
                    reply_markup=ReplyKeyboardMarkup(
                        keyboard=[["▶️ الرجوع"]],
                        resize_keyboard=True,
                        one_time_keyboard=True
                    )
                )
                return ConversationState.SELECT_SUBJECT
                
            # Create form object (you'll need to implement this based on your form model)
            # form = DynamicForm(form_data['data'])
            # context.user_data['form'] = form
            
            await update.message.reply_text(
                "تم تحميل النموذج. يرجى إدخال البيانات المطلوبة.",
                reply_markup=ReplyKeyboardMarkup(
                    keyboard=[["بدء تعبئة النموذج"], ["▶️ الرجوع"]],
                    resize_keyboard=True,
                    one_time_keyboard=True
                )
            )
            
            return ConversationState.FILL_FORM
            
        except Exception as e:
            logger.error(f"Error loading form: {e}")
            await update.message.reply_text(
                "حدث خطأ في تحميل النموذج. يرجى المحاولة مرة أخرى.",
                reply_markup=ReplyKeyboardMarkup(
                    keyboard=[["▶️ الرجوع"]],
                    resize_keyboard=True,
                    one_time_keyboard=True
                )
            )
            return ConversationState.SELECT_SUBJECT