import logging
from telegram.ext import (
    Application, ContextTypes, CommandHandler, MessageHandler, 
    filters, ConversationHandler, CallbackQueryHandler
)
from telegram import (
    KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update,
    InlineKeyboardButton, InlineKeyboardMarkup
)
from datetime import datetime, timedelta
from config import (
    TOKEN, SELECT_REQUEST_TYPE, SELECT_COMPLAINT_TYPE, COLLECT_FORM_FIELD, 
    SELECT_SUBJECT, FILL_FORM, MAIN_MENU, SERVICE_MENU, CONFIRM_SUBMISSION, 
    ENTER_MOBILE, ENTER_OTP, SELECT_REQUEST_NUMBER, SELECT_SERVICE_HIERARCHY, 
    SELECT_SERVICE_CATEGORY, SELECT_OTHER_SUBJECT, SELECT_COMPLAINT_SUBJECT, 
    SELECT_SERVICE, SELECT_COMPLIMENT_SIDE, SELECT_TIME_AM_PM
)
from services.api_service import ApiService
from forms.form_model import FormAttribute, FormDocument, DynamicForm
from forms.complaint_form import ComplaintForm
import re
from typing import List, Union, Optional, Dict, Any
import asyncio
import io
import httpx

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Constants
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

MAIN_MENU_BUTTON = "⏩ العودةإلى القائمة الرئيسية"
BACK_BUTTON = "▶️ الرجوع"
NEXT_BUTTON = "التالي"
CONFIRM_BUTTON = "تأكيد"

# Global variables
api_service: Optional[ApiService] = None
project_settings: Optional[Dict[str, Any]] = None
MOBILE_PREFIX: Optional[str] = None
MOBILE_LENGTH: int = 8
MOBILE_CODE: str = '09'
USERNAME_HINT: Optional[str] = None

class BotState:
    """Centralized bot state management"""
    
    def __init__(self):
        self.api_service: Optional[ApiService] = None
        self.project_settings: Optional[Dict[str, Any]] = None
        self.mobile_prefix: Optional[str] = None
        self.username_hint: Optional[str] = None
    
    async def initialize(self):
        """Initialize bot state"""
        try:
            self.api_service = ApiService()
            self.project_settings = await self.api_service.initialize_urls()
            self.mobile_prefix = f"+{self.project_settings.get('COUNTRY_CODE', '963')}"
            self.username_hint = self.project_settings.get('USERNAME_HINT', '## ### ####')
            
            # Update global variables for backward compatibility
            global api_service, project_settings, MOBILE_PREFIX, USERNAME_HINT
            api_service = self.api_service
            project_settings = self.project_settings
            MOBILE_PREFIX = self.mobile_prefix
            USERNAME_HINT = self.username_hint
            
            logger.info("Bot state initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize bot state: {str(e)}")
            return False

# Global bot state instance
bot_state = BotState()

async def initialize_bot():
    """Initialize bot components"""
    return await bot_state.initialize()

def update_last_activity(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Update last activity timestamp"""
    if context and hasattr(context, 'user_data'):
        context.user_data['last_activity'] = datetime.now()

def is_token_valid(context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if user token is still valid"""
    if not context or not hasattr(context, 'user_data'):
        return False
    
    last_activity = context.user_data.get('last_activity')
    if not last_activity:
        return False
    
    if datetime.now() - last_activity > timedelta(hours=1):
        context.user_data['authenticated'] = False
        context.user_data.pop('auth_token', None)
        context.user_data.pop('last_activity', None)
        return False
    
    return True

async def create_reply_keyboard(
    buttons: List[List[str]], 
    include_back: bool = True, 
    include_main_menu: bool = True, 
    one_time: bool = True
) -> ReplyKeyboardMarkup:
    """Create a reply keyboard with consistent button placement"""
    keyboard = [row[:] for row in buttons]
    
    # Remove existing navigation buttons
    for row in keyboard:
        if BACK_BUTTON in row:
            row.remove(BACK_BUTTON)
        if MAIN_MENU_BUTTON in row:
            row.remove(MAIN_MENU_BUTTON)
    
    # Filter out empty rows
    keyboard = [row for row in keyboard if row]
    
    # Add back button if needed
    if include_back and any(NEXT_BUTTON in row for row in keyboard):
        for row in keyboard:
            if NEXT_BUTTON in row and BACK_BUTTON not in row:
                row.insert(1, BACK_BUTTON)
                break
    elif include_back:
        if include_main_menu:
            keyboard.append([BACK_BUTTON, MAIN_MENU_BUTTON])
        else:
            keyboard.append([BACK_BUTTON])
    
    # Add main menu button if needed
    if include_main_menu and not any(MAIN_MENU_BUTTON in row for row in keyboard):
        keyboard.append([MAIN_MENU_BUTTON])
    
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=one_time
    )

async def send_error_message(
    update: Update, 
    message: str, 
    field: Optional[Union[FormAttribute, FormDocument]] = None, 
    keyboard_buttons: Optional[List[List[str]]] = None
) -> None:
    """Send error message with appropriate keyboard"""
    if field and hasattr(field, 'example') and field.example:
        message += f"\nمثال: {field.example}"
    
    keyboard = keyboard_buttons or [[BACK_BUTTON, MAIN_MENU_BUTTON]]
    await update.message.reply_text(
        message,
        reply_markup=await create_reply_keyboard(keyboard, include_back=True, include_main_menu=True)
    )

def get_greeting() -> str:
    """Get appropriate greeting based on current time"""
    current_hour = datetime.now().hour
    if 5 <= current_hour < 12:
        return "صباح الخير"
    elif 12 <= current_hour < 17:
        return "مساء الخير"
    else:
        return "مساء الخير"

def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Get main menu keyboard"""
    keyboard = [[option] for option in MAIN_MENU_OPTIONS]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=True
    )

def get_service_menu_keyboard() -> ReplyKeyboardMarkup:
    """Get service menu keyboard"""
    keyboard = [
        ["تقديم طلب"],
        ["طلباتي"]
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=True
    )

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, message: Optional[str] = None) -> None:
    """Show main menu with optional message"""
    # Preserve authentication data
    auth_data = {
        'authenticated': context.user_data.get('authenticated', False),
        'auth_token': context.user_data.get('auth_token', None),
        'file_metadata': context.user_data.get('file_metadata', {})
    }
    
    # Clear user data but preserve auth
    context.user_data.clear()
    context.user_data.update(auth_data)
    
    # Remove request-related data
    context.user_data.pop('requests', None)
    context.user_data.pop('requests_page', None)
    
    default_message = "☑️ YourVoiceSyBot v1.0.0"
    display_message = message or default_message
    
    await update.message.reply_text(
        display_message,
        reply_markup=get_main_menu_keyboard()
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /start command"""
    try:
        # Clear any existing user data
        context.user_data.clear()
        
        # Get user info
        user = update.effective_user
        user_name = user.first_name if user.first_name else "مستخدم"
        message = f"{get_greeting()} {user_name} 👋\n أهلاً بك في بوت الشكاوى. سأساعدك في تقديم طلبك في منصة صوتك."
        
        # Set initial state
        context.user_data['authenticated'] = True
        
        # Get user info from API if available
        if api_service:
            try:
                user_info = await api_service.user_info()
                logger.info(f"User info fetched: {user_info}")
            except Exception as e:
                logger.error(f"Failed to fetch user info: {str(e)}")
        
        update_last_activity(context)
        await show_main_menu(update, context, message)
        return MAIN_MENU
        
    except Exception as e:
        logger.error(f"Error in start command: {str(e)}", exc_info=True)
        await update.message.reply_text("حدث خطأ غير متوقع. حاول مرة أخرى.")
        return MAIN_MENU

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle main menu interactions"""
    try:
        update_last_activity(context)
        user_input = update.message.text.strip()
        
        logger.debug(f"Main menu selection: {user_input}")
        logger.debug(f"Context user_data before processing: {context.user_data}")
        
        # Set current conversation state
        context.user_data['conversation_state'] = MAIN_MENU
        
        # Handle menu options
        if user_input in MAIN_MENU_RESPONSES:
            await show_main_menu(update, context, message=MAIN_MENU_RESPONSES[user_input])
            return MAIN_MENU
        
        # Handle service access
        elif user_input == "سمعنا صوتك":
            is_authenticated = context.user_data.get('authenticated', False)
            logger.info(f"User authenticated: {is_authenticated}")
            
            if is_authenticated:
                logger.info("Transitioning to SERVICE_MENU")
                await update.message.reply_text(
                    "يرجى اختيار الخدمة",
                    reply_markup=get_service_menu_keyboard()
                )
                context.user_data['conversation_state'] = SERVICE_MENU
                return SERVICE_MENU
            else:
                logger.info("User not authenticated, requesting mobile number")
                # Clear authentication data
                context.user_data.pop('authenticated', None)
                context.user_data.pop('auth_token', None)
                context.user_data.pop('mobile', None)
                
                await update.message.reply_text(
                    f"يرجى تسجيل الدخول أولاً. أدخل رقم هاتفك المحمول (مثال: {MOBILE_PREFIX}9xxxxxxxx أو 09xxxxxxxx):",
                    reply_markup=ReplyKeyboardRemove()
                )
                context.user_data['conversation_state'] = ENTER_MOBILE
                return ENTER_MOBILE
        
        # Handle invalid input
        else:
            await show_main_menu(update, context, message="يرجى اختيار خيار من القائمة.")
            return MAIN_MENU
            
    except Exception as e:
        logger.error(f"Exception in main_menu: {str(e)}", exc_info=True)
        await update.message.reply_text("حدث خطأ غير متوقع. حاول مرة أخرى.")
        return MAIN_MENU

async def service_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle service menu interactions"""
    try:
        update_last_activity(context)
        user_input = update.message.text.strip()
        
        logger.debug(f"Service menu selection: {user_input}")
        
        # Handle navigation buttons
        if user_input == MAIN_MENU_BUTTON:
            await show_main_menu(update, context, message="☑️ YourVoiceSyBot v1.0.0")
            return MAIN_MENU
        
        # Handle service options
        if user_input == "تقديم طلب":
            try:
                # Initialize form
                context.user_data['form'] = ComplaintForm()
                context.user_data['side_hierarchy_path'] = []
                context.user_data['is_complaint_path'] = True
                
                # Get parent sides
                response = await api_service.get_parent_sides()
                logger.debug(f"Parent sides response: {response}")
                
                sides = response.get('sides', [])
                if not sides:
                    await update.message.reply_text(
                        "عذراً، لا توجد جهات متاحة حالياً.",
                        reply_markup=ReplyKeyboardRemove()
                    )
                    return ConversationHandler.END
                
                context.user_data['sides_data'] = sides
                keyboard = [[item['name'] for item in sides[i:i + 2]] for i in range(0, len(sides), 2)]
                
                if any(not item.get('disable_request', True) for item in sides):
                    keyboard.append(['تأكيد'])
                
                await update.message.reply_text(
                    'يرجى اختيار الجهة:',
                    reply_markup=await create_reply_keyboard(keyboard)
                )
                
                context.user_data['conversation_state'] = SELECT_COMPLIMENT_SIDE
                return SELECT_COMPLIMENT_SIDE
                
            except Exception as e:
                logger.error(f"Error fetching corporate hierarchy: {str(e)}", exc_info=True)
                await update.message.reply_text(
                    "حدث خطأ أثناء جلب الجهات. يرجى المحاولة لاحقاً.",
                    reply_markup=get_service_menu_keyboard()
                )
                context.user_data['conversation_state'] = SERVICE_MENU
                return SERVICE_MENU
        
        elif user_input == "طلباتي":
            context.user_data['requests_page'] = 0
            return await display_user_requests(update, context)
        
        # Handle pagination
        else:
            requests = context.user_data.get('requests', [])
            if user_input == "الصفحة السابقة":
                context.user_data['requests_page'] = max(context.user_data.get('requests_page', 0) - 1, 0)
                return await display_user_requests(update, context)
            elif user_input == "الصفحة التالية":
                total_pages = (len(requests) + 5 - 1) // 5
                context.user_data['requests_page'] = min(
                    context.user_data.get('requests_page', 0) + 1, 
                    total_pages - 1
                )
                return await display_user_requests(update, context)
            
            # Invalid input
            await update.message.reply_text(
                "يرجى اختيار خيار من القائمة.",
                reply_markup=get_service_menu_keyboard()
            )
            context.user_data['conversation_state'] = SERVICE_MENU
            return SERVICE_MENU
            
    except Exception as e:
        logger.error(f"Error in service_menu: {str(e)}", exc_info=True)
        await update.message.reply_text("حدث خطأ غير متوقع. حاول مرة أخرى.")
        return SERVICE_MENU

async def display_user_requests(update: Update, context: ContextTypes.DEFAULT_TYPE, items_per_page: int = 5) -> int:
    """Display user requests with pagination"""
    try:
        if 'requests' not in context.user_data:
            try:
                response = await api_service.get_user_requests()
                logger.debug(f"User requests response: {response}")
                
                requests = response.get('data', [])
                if not requests:
                    await update.message.reply_text(
                        "لم يتم العثور على طلبات سابقة.",
                        reply_markup=get_service_menu_keyboard()
                    )
                    context.user_data['conversation_state'] = SERVICE_MENU
                    return SERVICE_MENU
                
                context.user_data['requests'] = requests
                
            except Exception as e:
                logger.error(f"Error fetching user requests: {str(e)}")
                await update.message.reply_text(
                    "حدث خطأ أثناء جلب الطلبات. يرجى المحاولة لاحقاً.",
                    reply_markup=get_service_menu_keyboard()
                )
                context.user_data['conversation_state'] = SERVICE_MENU
                return SERVICE_MENU
        else:
            requests = context.user_data['requests']
        
        # Pagination logic
        current_page = context.user_data.get('requests_page', 0)
        total_pages = (len(requests) + items_per_page - 1) // items_per_page
        start_idx = current_page * items_per_page
        end_idx = min(start_idx + items_per_page, len(requests))
        page_requests = requests[start_idx:end_idx]
        
        # Build message
        message = f"طلباتك (الصفحة {current_page + 1} من {total_pages}):\n"
        for req in page_requests:
            request_number = req.get('request_number', 'غير محدد')
            request_type = req.get('request_type', 'غير محدد')
            request_date = req.get('request_date', 'غير محدد')
            request_time = req.get('request_time', 'غير محدد')
            request_status = req.get('request_status', 'غير محدد')
            
            message += (
                f"رقم الطلب: {request_number}, النوع: {request_type}\n"
                f"التاريخ: {request_date}, الوقت: {request_time}\n"
                f"الحالة: {request_status}\n"
                "----------------------------------------------------------------------------------\n"
            )
        
        # Build keyboard
        keyboard = [[str(req['request_number'])] for req in page_requests]
        
        # Navigation buttons
        nav_buttons = []
        if current_page > 0:
            nav_buttons.append("الصفحة السابقة")
        if current_page < total_pages - 1:
            nav_buttons.append("الصفحة التالية")
        
        if nav_buttons:
            keyboard.append(nav_buttons)
        
        keyboard.append([BACK_BUTTON, MAIN_MENU_BUTTON])
        
        reply_markup = ReplyKeyboardMarkup(
            keyboard=keyboard,
            resize_keyboard=True,
            one_time_keyboard=True
        )
        
        await update.message.reply_text(
            message + "\nاختر رقم الطلب لعرض التفاصيل، أو استخدم الأزرار للتنقل بين الصفحات:",
            reply_markup=reply_markup
        )
        
        context.user_data['requests_page'] = current_page
        context.user_data['conversation_state'] = SELECT_REQUEST_NUMBER
        return SELECT_REQUEST_NUMBER
        
    except Exception as e:
        logger.error(f"Error in display_user_requests: {str(e)}", exc_info=True)
        await update.message.reply_text("حدث خطأ أثناء عرض الطلبات. يرجى المحاولة لاحقاً.")
        return SERVICE_MENU

async def enter_mobile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle mobile number input"""
    try:
        mobile = update.message.text.strip()
        logger.debug(f"Mobile input received: {mobile}")
        
        if mobile == MAIN_MENU_BUTTON:
            await show_main_menu(update, context, message="☑️ YourVoiceSyBot v1.0.0")
            return MAIN_MENU
        
        # Validate mobile format
        valid_pattern = rf'^(?:{re.escape(MOBILE_PREFIX)}\d{{{MOBILE_LENGTH + 1}}}|0\d{{{MOBILE_LENGTH + 1}}})$'
        if not re.match(valid_pattern, mobile):
            await update.message.reply_text(
                f"رقم الهاتف غير صالح. يرجى إدخال رقم هاتف بالصيغة الصحيحة (مثال: {MOBILE_PREFIX}9xxxxxxxx أو 09xxxxxxxx):",
                reply_markup=ReplyKeyboardMarkup([[BACK_BUTTON, MAIN_MENU_BUTTON]], resize_keyboard=True)
            )
            return ENTER_MOBILE
        
        # Format mobile number
        formatted_mobile = convert_mobile_format(mobile)
        if formatted_mobile == mobile:
            await update.message.reply_text(
                f"رقم الهاتف غير صالح. يجب أن يبدأ الرقم بـ '9' بعد رمز الدولة (مثال: {MOBILE_PREFIX}9xxxxxxxx أو 09xxxxxxxx):",
                reply_markup=ReplyKeyboardMarkup([[BACK_BUTTON, MAIN_MENU_BUTTON]], resize_keyboard=True)
            )
            return ENTER_MOBILE
        
        # Request OTP
        try:
            response = await api_service.request_otp(formatted_mobile)
            if response.get("success"):
                context.user_data['mobile'] = formatted_mobile
                await update.message.reply_text(
                    "تم إرسال رمز OTP إلى هاتفك. يرجى إدخال الرمز (4 أرقام، مثال: 1234):",
                    reply_markup=ReplyKeyboardMarkup([[BACK_BUTTON, MAIN_MENU_BUTTON]], resize_keyboard=True)
                )
                return ENTER_OTP
            else:
                await update.message.reply_text(
                    f"حدث خطأ أثناء طلب OTP. يرجى إدخال رقم هاتفك مرة أخرى (مثال: {MOBILE_PREFIX}9xxxxxxxx أو 09xxxxxxxx):",
                    reply_markup=ReplyKeyboardMarkup([[BACK_BUTTON, MAIN_MENU_BUTTON]], resize_keyboard=True)
                )
                return ENTER_MOBILE
                
        except Exception as e:
            logger.error(f"Failed to request OTP for {formatted_mobile}: {str(e)}")
            await update.message.reply_text(
                f"حدث خطأ أثناء طلب OTP. يرجى إدخال رقم هاتفك مرة أخرى (مثال: {MOBILE_PREFIX}9xxxxxxxx أو 09xxxxxxxx):",
                reply_markup=ReplyKeyboardMarkup([[BACK_BUTTON, MAIN_MENU_BUTTON]], resize_keyboard=True)
            )
            return ENTER_MOBILE
            
    except Exception as e:
        logger.error(f"Error in enter_mobile: {str(e)}", exc_info=True)
        await update.message.reply_text("حدث خطأ غير متوقع. حاول مرة أخرى.")
        return ENTER_MOBILE

def convert_mobile_format(mobile: str) -> str:
    """Convert mobile number to proper format"""
    try:
        cleaned = ''.join(filter(str.isdigit, mobile))
        expected_prefix = MOBILE_PREFIX.lstrip('+') if MOBILE_PREFIX else '963'
        expected_length = MOBILE_LENGTH + 1
        
        if cleaned.startswith(expected_prefix):
            digits = cleaned[len(expected_prefix):]
        elif cleaned.startswith('0'):
            digits = cleaned[1:]
        else:
            logger.warning(f"Invalid mobile number format: {mobile}")
            return mobile
        
        if len(digits) != expected_length:
            logger.warning(f"Invalid mobile number length: expected {expected_length} digits, got {len(digits)}")
            return mobile
        
        if not digits.startswith('9'):
            logger.warning(f"Mobile number must start with '9' after country code: {digits}")
            return mobile
        
        # Format according to username hint
        if USERNAME_HINT:
            formatted = ""
            digit_index = 0
            for char in USERNAME_HINT:
                if char == '#':
                    if digit_index < len(digits):
                        formatted += digits[digit_index]
                        digit_index += 1
                    else:
                        break
                else:
                    formatted += char
        else:
            formatted = digits
        
        return f"{MOBILE_PREFIX} {formatted}" if MOBILE_PREFIX else f"+963 {formatted}"
        
    except Exception as e:
        logger.error(f"Error converting mobile format: {str(e)}")
        return mobile

async def enter_otp(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle OTP input"""
    try:
        otp = update.message.text.strip()
        
        if not re.match(r'^\d{4}$', otp):
            await update.message.reply_text(
                "رمز OTP غير صالح. يرجى إدخال رمز مكون من 4 أرقام (مثال: 1234):"
            )
            return ENTER_OTP
        
        mobile = context.user_data.get('mobile')
        if not mobile:
            logger.error("No mobile number found in user_data")
            await update.message.reply_text(
                f"خطأ: رقم الهاتف غير موجود. يرجى إدخال رقم هاتفك مرة أخرى (مثال: {MOBILE_PREFIX}{MOBILE_CODE}xxxxxxxx):"
            )
            return ENTER_MOBILE
        
        # Login with OTP
        try:
            response = await api_service.login_otp(mobile, otp)
            context.user_data['authenticated'] = True
            context.user_data['auth_token'] = response.get('access_token')
            
            await update.message.reply_text(
                "تم تسجيل الدخول بنجاح! يرجى اختيار الخدمة",
                reply_markup=get_service_menu_keyboard()
            )
            return SERVICE_MENU
            
        except Exception as e:
            logger.error(f"Failed to login with OTP for {mobile}: {str(e)}")
            await update.message.reply_text(
                f"رمز OTP غير صحيح أو حدث خطأ. يرجى إدخال رقم هاتفك مرة أخرى (مثال: {MOBILE_PREFIX}{MOBILE_CODE}xxxxxxxx):"
            )
            context.user_data.pop('mobile', None)
            return ENTER_MOBILE
            
    except Exception as e:
        logger.error(f"Error in enter_otp: {str(e)}", exc_info=True)
        await update.message.reply_text("حدث خطأ غير متوقع. حاول مرة أخرى.")
        return ENTER_OTP

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /cancel command"""
    try:
        await update.message.reply_text(
            "تم إلغاء العملية. يمكنك البدء من جديد باستخدام /start.",
            reply_markup=get_main_menu_keyboard()
        )
        context.user_data.clear()
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Error in cancel command: {str(e)}", exc_info=True)
        return ConversationHandler.END

async def main():
    """Main bot function"""
    try:
        # Initialize bot
        logger.info("Initializing bot...")
        if not await initialize_bot():
            logger.error("Failed to initialize bot")
            return
        
        logger.info("Bot initialization complete.")
        
        # Build application
        application = Application.builder().token(TOKEN).build()
        
        # Set up conversation handler
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', start)],
            states={
                MAIN_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, main_menu)],
                SERVICE_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, service_menu)],
                ENTER_MOBILE: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_mobile)],
                ENTER_OTP: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_otp)],
                SELECT_REQUEST_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_request_type)],
                SELECT_COMPLAINT_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_subject)],
                SELECT_COMPLIMENT_SIDE: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_compliment_side)],
                FILL_FORM: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, fill_form),
                    MessageHandler(filters.ATTACHMENT, fill_form)
                ],
                SELECT_SERVICE_CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_service_category)],
                COLLECT_FORM_FIELD: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_form_field)],
                CONFIRM_SUBMISSION: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_submission)],
                SELECT_REQUEST_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_request_number)],
                SELECT_SERVICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_service)],
                SELECT_SUBJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_subject)],
                SELECT_OTHER_SUBJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_other_subject)],
                SELECT_TIME_AM_PM: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_time_am_pm)],
            },
            fallbacks=[CommandHandler('cancel', cancel)]
        )
        
        application.add_handler(conv_handler)
        
        # Add callback query handler for file viewing
        application.add_handler(CallbackQueryHandler(handle_view_file, pattern=r"^view_files:"))
        
        # Start bot
        logger.info("Starting polling...")
        await application.initialize()
        await application.start()
        await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        logger.info("Bot is polling...")
        
        # Keep running until interrupted
        try:
            while True:
                await asyncio.sleep(3600)
        except KeyboardInterrupt:
            logger.info("Shutting down bot...")
            await application.updater.stop()
            await application.stop()
            await application.shutdown()
            logger.info("Bot stopped.")
            
    except Exception as e:
        logger.error(f"Failed to run bot: {str(e)}", exc_info=True)
        raise

if __name__ == '__main__':
    asyncio.run(main())
