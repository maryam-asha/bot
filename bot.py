import logging
from telegram.ext import Application,ContextTypes, CommandHandler, MessageHandler, filters, ConversationHandler, CallbackQueryHandler
from telegram import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from datetime import datetime, timedelta
from services.api_service import ApiService
from forms.form_model import FormAttribute, FormDocument, DynamicForm
from form_handler_improved import ImprovedFormHandler
from form_file_handler import FormFileHandler, FormLocationHandler
from form_error_handler import FormErrorHandler, FormDataSanitizer
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from handlers.base_handler import BaseHandler
from handlers.main_menu_handler import MainMenuHandler
from keyboards.base_keyboard import BaseKeyboard
from config.conversation_states import ConversationState, get_previous_state
from config.settings import settings
import re
from typing import List, Union
import asyncio
import io
import httpx
import json
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


api_service = None
project_settings = None
MOBILE_PREFIX =f"+{settings.country_code}"
MOBILE_LENGTH = settings.mobile_length
MOBILE_CODE = settings.mobile_code
USERNAME_HINT = settings.username_hint
MAIN_MENU_BUTTON = "⏩ العودةإلى القائمة الرئيسية"
keyboard = BaseKeyboard()

MAIN_MENU_OPTIONS = ["حول المنصة", "حول الوزارة", "حول الشركة المطورة", "سمعنا صوتك"]
MAIN_MENU_RESPONSES = {
    "حول المنصة": "منصة صوتك هي المنصة الأولى للمواطنين للتعبير عن آرائهم ومقترحاتهم وتقديم شكاويهم في كل المواضيع والخدمات والجهات العاملة تحت وزارة التقانة والاتصالات للجمهورية العربية السورية وقريباً في جميع الوزارات",
    "حول الوزارة": "تتولى وزارة الاتصالات وتقانة المعلومات في الجمهورية العربية السورية بموجب قواعد تنظيمها مهام متعددة تشمل: تنفيذ السياسات العامة في قطاعات الاتصالات والبريد وتقانة المعلومات، تنظيم وتطوير هذه القطاعات، دعم صناعة البرمجيات والخدمات الرقمية، تشجيع الاستثمار والشراكات بين القطاعين العام والخاص، وضع الخطط اللازمة للتحول الرقمي وضمان أمن المعلومات، المشاركة في المشاريع الدولية والإقليمية، بناء القدرات الفنية والعلمية عبر التدريب ودعم البحث العلمي، ورفع الوعي بأهمية الاتصالات وتقانة المعلومات في التنمية الاقتصادية والاجتماعية",
    "حول الشركة المطورة": "مجموعة أوتوماتا4 هي شركة إقليمية مكرسة لتقديم حلول وخدمات استشارية مخصصة عالية الجودة لتكنولوجيا المعلومات..."
}
async def initialize_bot():
    global api_service, form_handler, file_handler, location_handler, error_handler
    api_service = ApiService()
    project_settings = await api_service.initialize_urls()
    
    settings.base_url = project_settings.get("BASE_URL", settings.base_url)
    settings.image_base_url = project_settings.get("IMAGE_BASE_URL", settings.image_base_url)
    settings.country_code = project_settings.get("COUNTRY_CODE", settings.country_code)
    settings.username_hint = project_settings.get("USERNAME_HINT", settings.username_hint)
    settings.mobile_length = project_settings.get("MOBILE_LENGTH", settings.mobile_length)
    settings.mobile_code = project_settings.get("MOBILE_CODE", settings.mobile_code)
    
    # إنشاء المعالجات المحسنة
    form_handler = ImprovedFormHandler(api_service)
    file_handler = FormFileHandler(api_service)
    location_handler = FormLocationHandler(api_service)
    error_handler = FormErrorHandler()
    
    # ربط المعالجات معاً
    form_handler.set_handlers(file_handler, location_handler, error_handler)
    
    logger.info("Enhanced form handlers initialized successfully")

async def create_reply_keyboard(buttons: List[List[str]], include_back=True, include_main_menu=True, one_time=True) -> ReplyKeyboardMarkup:
    keyboard = [row[:] for row in buttons]
    for row in keyboard:
        if "▶️ الرجوع" in row:
            row.remove("▶️ الرجوع")
        if MAIN_MENU_BUTTON in row:
            row.remove(MAIN_MENU_BUTTON)
    keyboard = [row for row in keyboard if row]  

    if include_back and any("التالي" in row for row in keyboard):
        for row in keyboard:
            if "التالي" in row and "▶️ الرجوع" not in row:
                row.insert(1, "▶️ الرجوع")
                break
    elif include_back:
        if include_main_menu:
            keyboard.append(["▶️ الرجوع", MAIN_MENU_BUTTON])
        else:
            keyboard.append(["▶️ الرجوع"])

    if include_main_menu and not any(MAIN_MENU_BUTTON in row for row in keyboard):
        keyboard.append([MAIN_MENU_BUTTON])

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=one_time
    )


async def send_error_message(update: Update, message: str, field=None, keyboard_buttons: List[List[str]] = None) -> None:
    keyboard = keyboard_buttons or [['▶️ الرجوع', MAIN_MENU_BUTTON]]
    await update.message.reply_text(
        message,
        reply_markup=await create_reply_keyboard(keyboard, include_back=True, include_main_menu=True)
    )


async def handle_back(update: Update, context, current_state: int) -> int:
    logger.debug(f"Handling back from state {current_state}")

    back_state_map = {
        ConversationState.SELECT_COMPLIMENT_SIDE: ConversationState.SERVICE_MENU,
        ConversationState.SELECT_REQUEST_TYPE: ConversationState.SELECT_COMPLIMENT_SIDE,
        ConversationState.SELECT_SUBJECT: ConversationState.SELECT_REQUEST_TYPE,
        ConversationState.SELECT_OTHER_SUBJECT: ConversationState.SELECT_SUBJECT,
        ConversationState.SELECT_SERVICE_CATEGORY: ConversationState.SELECT_SUBJECT,
        ConversationState.SELECT_SERVICE: ConversationState.SELECT_SERVICE_CATEGORY,
        ConversationState.FILL_FORM: ConversationState.SELECT_SUBJECT,  
        ConversationState.COLLECT_FORM_FIELD: ConversationState.FILL_FORM,
        ConversationState.CONFIRM_SUBMISSION: ConversationState.COLLECT_FORM_FIELD,
        ConversationState.SELECT_REQUEST_NUMBER: ConversationState.SERVICE_MENU,
        ConversationState.ENTER_OTP: ConversationState.ENTER_MOBILE,
        ConversationState.ENTER_MOBILE: ConversationState.SERVICE_MENU,
        ConversationState.SELECT_TIME_AM_PM: ConversationState.FILL_FORM
    }

    prev_state = back_state_map.get(current_state, ConversationState.MAIN_MENU)
    logger.info(f"previous state {prev_state}")
    # الآن نعيد عرض الرسالة السابقة حسب prev_state
    if prev_state == ConversationState.MAIN_MENU:
        await show_main_menu(update, context, message="☑️ YourVoiceSyBot v1.0.0")
    elif prev_state == ConversationState.SERVICE_MENU:
        await update.message.reply_text("يرجى اختيار الخدمة:", reply_markup=get_service_menu_keyboard())
    elif prev_state == ConversationState.SELECT_COMPLIMENT_SIDE:
        sides = context.user_data.get('sides_data', [])
        keyboard = [[item['name'] for item in sides[i:i+2]] for i in range(0, len(sides), 2)]
        if any(not item.get('disable_request', True) for item in sides):
            keyboard.append(['تأكيد'])
        await update.message.reply_text("يرجى اختيار الجهة:", reply_markup=await create_reply_keyboard(keyboard))
    elif prev_state == ConversationState.SELECT_REQUEST_TYPE:
        request_types = [item['name'] for item in context.user_data.get('api_data', {}).get('request_types', [])]
        keyboard = [request_types[i:i+2] for i in range(0, len(request_types), 2)]
        await update.message.reply_text("يرجى اختيار نوع الطلب:", reply_markup=await create_reply_keyboard(keyboard))
    elif prev_state == ConversationState.SELECT_SUBJECT:
        subjects = context.user_data.get('api_data', {}).get('complaint_subjects', [])
        keyboard = [[item['name'] for item in subjects[i:i+2]] for i in range(0, len(subjects), 2)]
        await update.message.reply_text("يرجى اختيار موضوع الشكوى:", reply_markup=await create_reply_keyboard(keyboard))
    elif prev_state == ConversationState.SELECT_SERVICE_CATEGORY:
        categories = context.user_data.get('service_categories', [])
        keyboard = [[cat['text'] for cat in categories[i:i+2]] for i in range(0, len(categories), 2)]
        await update.message.reply_text("يرجى اختيار فئة الخدمة:", reply_markup=await create_reply_keyboard(keyboard))
    elif prev_state == ConversationState.SELECT_SERVICE:
        services = context.user_data.get('services', [])
        keyboard = [[serv['text'] for serv in services[i:i+2]] for i in range(0, len(services), 2)]
        await update.message.reply_text("يرجى اختيار الخدمة:", reply_markup=await create_reply_keyboard(keyboard))
    elif prev_state == ConversationState.FILL_FORM:
        form = context.user_data.get('form')
        if form:
            field = form.get_current_field(context)
            if field:
                return await show_form_field(update, context, field)
    elif prev_state == ConversationState.COLLECT_FORM_FIELD:
        return await show_form_summary(update, context)
    elif prev_state == ConversationState.CONFIRM_SUBMISSION:
        logger.info(f"previous state  in CONFIRM_SUBMISSION {prev_state}")
        form = context.user_data.get('form')
        history = context.user_data.get('form_field_history', [])
        if form and history:
            last_field = history[-1]  
            return await show_form_field(update, context, last_field)
        else:
            return await show_form_summary(update, context)

    return prev_state

async def back_from_fill_form(update: Update, context, form):
    await update.message.reply_text("Returning from fill form.")
    return ConversationState.FILL_FORM

async def handle_back_navigation(update: Update, context):
    await update.message.reply_text("Handling back navigation.")
    return ConversationState.SELECT_SUBJECT

async def back_from_collect_form_field(update: Update, context, form):
    await update.message.reply_text("Returning from collect form field.")
    return ConversationState.COLLECT_FORM_FIELD

async def back_from_service_category(update: Update, context):
    await update.message.reply_text("Returning from service category.")
    return ConversationState.SELECT_SERVICE_CATEGORY

async def back_from_service(update: Update, context):
    await update.message.reply_text("Returning from service.")
    return ConversationState.SELECT_SERVICE

async def back_from_compliment_side(update: Update, context):
    await update.message.reply_text("Returning from compliment side.")
    return ConversationState.SELECT_COMPLIMENT_SIDE

def update_last_activity(context):
    context.user_data['last_activity'] = datetime.now()

async def show_main_menu(update: Update, context, message: str):
    keyboard = [[option] for option in MAIN_MENU_OPTIONS]
    await update.message.reply_text(
        message,
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    )

def get_service_menu_keyboard():
    keyboard = [
        ["تقديم طلب"],
        ["طلباتي"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

async def display_user_requests(update: Update, context , items_per_page: int = 5) -> int:
    if 'requests' not in context.user_data:
        try:
            response = await api_service.get_user_requests()
            print(f"=== DEBUG: display user requests: {response} ===")
            requests = response.get('data', [])
            if not requests:
                await update.message.reply_text(
                    "لم يتم العثور على طلبات سابقة.",
                    reply_markup=get_service_menu_keyboard()
                )
                context.user_data['conversation_state'] = ConversationState.SERVICE_MENU
                return ConversationState.SERVICE_MENU
            context.user_data['requests'] = requests
        except Exception as e:
            logger.error(f"Error fetching user requests: {str(e)}")
            await update.message.reply_text(
                "حدث خطأ أثناء جلب الطلبات. يرجى المحاولة لاحقاً.",
                reply_markup=get_service_menu_keyboard()
            )
            context.user_data['conversation_state'] = ConversationState.SERVICE_MENU
            return ConversationState.SERVICE_MENU
    else:
        requests = context.user_data['requests']

    current_page = context.user_data.get('requests_page', 0)
    total_pages = (len(requests) + items_per_page - 1) // items_per_page
    start_idx = current_page * items_per_page
    end_idx = min(start_idx + items_per_page, len(requests))
    page_requests = requests[start_idx:end_idx]

    message = f"طلباتك (الصفحة {current_page + 1} من {total_pages}):\n"
    for req in page_requests:
        request_number = req.get('request_number')
        request_type = req.get('request_type')
        request_date = req.get('request_date')
        request_time = req.get('request_time')
        request_status = req.get('request_status')
        message += f"رقم الطلب: {request_number}, النوع: {request_type}\n" \
                   f"التاريخ: {request_date}, الوقت: {request_time}\n" \
                   f"الحالة: {request_status}\n" \
                   "----------------------------------------------------------------------------------\n"

    keyboard = [[str(req['request_number'])] for req in page_requests]
    nav_buttons = []
    if current_page > 0:
        nav_buttons.append("الصفحة السابقة")
    if current_page < total_pages - 1:
        nav_buttons.append("الصفحة التالية")
    if nav_buttons:
        keyboard.append(nav_buttons)
    keyboard.append(['▶️ الرجوع', MAIN_MENU_BUTTON])

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
    context.user_data['conversation_state'] = ConversationState.SELECT_REQUEST_NUMBER
    return ConversationState.SELECT_REQUEST_NUMBER


def get_greeting():
    current_hour = datetime.now().hour
    if 5 <= current_hour < 12:
        return "صباح الخير"
    elif 12 <= current_hour < 17:
        return "مساء الخير"
    else:
        return "مساء الخير"
    
async def start(update: Update, context) -> int:
    context.user_data.clear()
    user = update.effective_user
    user_name = user.first_name if user.first_name else "مستخدم"
    message = f"{get_greeting()} {user_name} 👋\n أهلاً بك في بوت الشكاوى. سأساعدك في تقديم طلبك في منصة صوتك."
    context.user_data['authenticated'] = True

    try:
            user_info = await api_service.user_info()
            logger.info(f"User info fetched: {user_info}")
    except Exception as e:
            logger.error(f"Failed to fetch user info: {str(e)}")
    update_last_activity(context)
    await show_main_menu(update, context, message)
    return ConversationState.MAIN_MENU

async def main_menu(update: Update, context) -> int:
    update_last_activity(context)
    user_input = update.message.text
    print(f"=== DEBUG: Main menu selection: {user_input} ===")
    print(f"Context user_data before processing: {context.user_data}")
    try:
        context.user_data['conversation_state'] = ConversationState.MAIN_MENU
        if user_input in MAIN_MENU_RESPONSES:
            await show_main_menu(update, context, message=MAIN_MENU_RESPONSES[user_input])
            return ConversationState.MAIN_MENU
        elif user_input == "سمعنا صوتك":
            is_authenticated = context.user_data.get('authenticated')
            logger.info(f"User authenticated: {is_authenticated}")
            if is_authenticated:
                logger.info("Transitioning to SERVICE_MENU")
                await update.message.reply_text(
                        "يرجى اختيار الخدمة",
                        reply_markup=get_service_menu_keyboard()
                )
                context.user_data['conversation_state'] = ConversationState.SERVICE_MENU
                return ConversationState.SERVICE_MENU
            else:
                logger.info("User not authenticated, requesting mobile number")
                context.user_data.pop('authenticated', None)
                context.user_data.pop('auth_token', None)
                context.user_data.pop('mobile', None)
                await update.message.reply_text(
                        f"يرجى تسجيل الدخول أولاً. أدخل رقم هاتفك المحمول (مثال: {MOBILE_PREFIX}9xxxxxxxx أو 09xxxxxxxx):",
                        reply_markup=ReplyKeyboardRemove()
                    )
               
                context.user_data['conversation_state'] = ConversationState.ENTER_MOBILE
                return ConversationState.ENTER_MOBILE
        else:
            await show_main_menu(update, context, message="يرجى اختيار خيار من القائمة.")
            return ConversationState.MAIN_MENU
    except Exception as e:
        logger.error(f"Exception in main_menu: {str(e)}", exc_info=True)
        await update.message.reply_text("حدث خطأ غير متوقع. حاول مرة أخرى.")
        return ConversationState.MAIN_MENU

async def service_menu(update: Update, context) -> int:
    update_last_activity(context)
    user_input = update.message.text
    print(f"=== DEBUG: Service menu selection: {user_input} ===")
    print(f"Received text in service_menu: '{update.message.text}'")
    if user_input == MAIN_MENU_BUTTON:
        await show_main_menu(update, context, message="☑️ YourVoiceSyBot v1.0.0")
        return ConversationState.MAIN_MENU
    if user_input == "تقديم طلب":
        try:
            response = await api_service.get_parent_sides()
            print(f"=== DEBUG:Complaint Form: {response} ===")
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
            context.user_data['conversation_state'] = ConversationState.SELECT_COMPLIMENT_SIDE
            return ConversationState.SELECT_COMPLIMENT_SIDE
        except Exception as e:
            logger.error(f"Error fetching corporate hierarchy: {str(e)}", exc_info=True)
            await update.message.reply_text(
                "حدث خطأ أثناء جلب الجهات. يرجى المحاولة لاحقاً.",
                reply_markup=get_service_menu_keyboard()
            )
            context.user_data['conversation_state'] = ConversationState.SERVICE_MENU
            return ConversationState.SERVICE_MENU
    elif user_input == "طلباتي":
        context.user_data['requests_page'] = 0
        return await display_user_requests(update, context)
    else:
        requests = context.user_data.get('requests', [])
        if user_input == "الصفحة السابقة":
            context.user_data['requests_page'] = max(context.user_data.get('requests_page', 0) - 1, 0)
            return await display_user_requests(update, context)
        elif user_input == "الصفحة التالية":
            total_pages = (len(requests) + 5 - 1) // 5
            context.user_data['requests_page'] = min(context.user_data.get('requests_page', 0) + 1, total_pages - 1)
            return await display_user_requests(update, context)
        await update.message.reply_text(
            "يرجى اختيار خيار من القائمة.",
            reply_markup=get_service_menu_keyboard()
        )
        context.user_data['conversation_state'] = ConversationState.SERVICE_MENU
        return ConversationState.SERVICE_MENU

async def enter_mobile(update: Update, context) -> int:
    logger.debug("Entered enter_mobile")
    await update.message.reply_text("Mobile received. Proceeding to OTP.")
    return ConversationState.ENTER_OTP

async def enter_otp(update: Update, context) -> int:
    logger.debug("Entered enter_otp")
    context.user_data['authenticated'] = True
    await update.message.reply_text("OTP accepted. Returning to service menu.")
    return ConversationState.SERVICE_MENU


async def select_request_type(update: Update, context) -> int:
    update_last_activity(context)
    user_input = update.message.text
    logger.info(f"=== DEBUG: Request type selection: {user_input} ===")
    
    if user_input == '▶️ الرجوع':
        return await handle_back(update, context, ConversationState.SELECT_REQUEST_TYPE)
    if user_input == MAIN_MENU_BUTTON:
        await show_main_menu(update, context, message="☑️ YourVoiceSyBot v1.0.0")
        return ConversationState.MAIN_MENU
    
    request_types = context.user_data.get('api_data', {}).get('request_types', [])
    selected_request_type = next((item for item in request_types if item['name'] == user_input), None)
    
    if not selected_request_type:
        keyboard = [[item['name'] for item in request_types[i:i + 2]] for i in range(0, len(request_types), 2)]
        await send_error_message(
            update,
            'يرجى اختيار نوع طلب صالح.',
            keyboard_buttons=keyboard
        )
        return ConversationState.SELECT_REQUEST_TYPE
    
    context.user_data['request_type'] = {
        'id': selected_request_type['id'],
        'name': user_input
    }
    
    try:
        response = await api_service.get_request_type_subjects(
            request_type_id=selected_request_type['id'],
            side_id=context.user_data['side_id']
        )
        subjects = response.get('data', [])
        if not subjects:
            await send_error_message(update, 'لا توجد مواضيع شكوى متاحة.')
            return ConversationState.SERVICE_MENU
        
        context.user_data['api_data']['complaint_subjects'] = subjects
        context.user_data['service_subject_code'] = response.get('service_subject_code')
        context.user_data['other_subject_code'] = response.get('other_subject_code')
        
        keyboard = [[item['name'] for item in subjects[i:i + 2]] for i in range(0, len(subjects), 2)]
        await update.message.reply_text(
            f"تم اختيار: {user_input}\nيرجى اختيار موضوع الشكوى:",
            reply_markup=await create_reply_keyboard(keyboard)
        )
        logger.info(f"=== DEBUG: Request type select_request_type: {keyboard} ===")
        return ConversationState.SELECT_SUBJECT
    except Exception as e:
        logger.error(f"Error fetching complaint subjects: {str(e)}")
        await send_error_message(update, f"خطأ في جلب مواضيع الشكوى: {str(e)}")
        return ConversationState.SERVICE_MENU

  
async def select_compliment_side(update: Update, context) -> int:
    update_last_activity(context)
    selected_text = update.message.text
    if selected_text == '▶️ الرجوع':
        return await handle_back(update, context, ConversationState.SELECT_COMPLIMENT_SIDE)
    if selected_text == MAIN_MENU_BUTTON:
        await show_main_menu(update, context, message="☑️ YourVoiceSyBot v1.0.0")
        return ConversationState.MAIN_MENU

    sides = context.user_data.get('sides_data', [])
    if not sides:
        logger.error("No sides_data available")
        await send_error_message(update, "لا توجد بيانات جهات متاحة. يرجى المحاولة لاحقاً.")
        return ConversationState.SERVICE_MENU

    if selected_text == 'تأكيد':
        side_hierarchy_path = context.user_data.get('side_hierarchy_path', [])
        if not side_hierarchy_path:
            keyboard = [[item['name'] for item in sides[i:i + 2]] for i in range(0, len(sides), 2)]
            keyboard.append(['تأكيد'])
            await send_error_message(
                update,
                'يرجى اختيار جهة واحدة على الأقل قبل التأكيد.',
                keyboard_buttons=keyboard
            )
            return ConversationState.SELECT_COMPLIMENT_SIDE
        last_side = side_hierarchy_path[-1]
        can_submit = not last_side.get('disable_request', False)
        if not can_submit or (last_side.get('stop_level', False) and not any(child.get('disable_request', False) for child in sides)):
            await send_error_message(
                update,
                'لا يمكن تقديم طلب لهذه الجهة.',
                keyboard_buttons=[[item['name'] for item in sides[i:i + 2]] for i in range(0, len(sides), 2)] + [['تأكيد']]
            )
            return ConversationState.SELECT_COMPLIMENT_SIDE
        context.user_data['side_id'] = last_side['value']
        try:
            response = await api_service.get_request_type(side_id=last_side['value'])
            request_types = response.get('data', [])
            if not request_types:
                await send_error_message(update, 'لا توجد أنواع طلبات متاحة.')
                return ConversationState.SERVICE_MENU
            context.user_data['api_data'] = {'request_types': request_types}
            keyboard = [[item['name'] for item in request_types[i:i + 2]] for i in range(0, len(request_types), 2)]
            await update.message.reply_text(
                'يرجى اختيار نوع الطلب:',
                reply_markup=await create_reply_keyboard(keyboard)
            )
            return ConversationState.SELECT_REQUEST_TYPE
        except Exception as e:
            logger.error(f"Error fetching request types: {str(e)}")
            await send_error_message(update, "حدث خطأ في جلب أنواع الطلبات.")
            return ConversationState.SERVICE_MENU

    selected_side = next((item for item in sides if item['name'] == selected_text), None)
    if not selected_side:
        keyboard = [[item['name'] for item in sides[i:i + 2]] for i in range(0, len(sides), 2)]
        if any(not item.get('disable_request', True) for item in sides):
            keyboard.append(['تأكيد'])
        await send_error_message(
            update,
            'يرجى اختيار جهة صالحة.',
            keyboard_buttons=keyboard
        )
        return ConversationState.SELECT_COMPLIMENT_SIDE

    context.user_data.setdefault('side_hierarchy_path', []).append({
        'value': selected_side['id'],
        'text': selected_side['name']
    })
    try:
        response = await api_service.get_side_children(parent_id=selected_side['id'])
        children = response.get('sides', [])
        if children and not selected_side.get('stop_level', False):
            context.user_data['sides_data'] = children
            keyboard = [[item['name'] for item in children[i:i + 2]] for i in range(0, len(children), 2)]
            if not selected_side.get('disable_request', True):
                keyboard.append(['تأكيد'])
            await update.message.reply_text(
                'يرجى اختيار الجهة الفرعية:',
                reply_markup=await create_reply_keyboard(keyboard)
            )
            return ConversationState.SELECT_COMPLIMENT_SIDE
        else:
            if selected_side.get('disable_request', True):
                await send_error_message(
                    update,
                    'لا يمكن تقديم طلب لهذه الجهة.',
                    keyboard_buttons=[[item['name'] for item in sides[i:i + 2]] for i in range(0, len(sides), 2)] + [['تأكيد']]
                )
                return ConversationState.SELECT_COMPLIMENT_SIDE
            context.user_data['side_id'] = selected_side['id']
            try:
                response = await api_service.get_request_type(side_id=selected_side['id'])
                request_types = response.get('data', [])
                if not request_types:
                    await send_error_message(update, 'لا توجد أنواع طلبات متاحة.')
                    return ConversationState.SERVICE_MENU
                context.user_data['api_data'] = {'request_types': request_types}
                keyboard = [[item['name'] for item in request_types[i:i + 2]] for i in range(0, len(request_types), 2)]
                await update.message.reply_text(
                    'يرجى اختيار نوع الطلب:',
                    reply_markup=await create_reply_keyboard(keyboard)
                )
                return ConversationState.SELECT_REQUEST_TYPE
            except Exception as e:
                logger.error(f"Error fetching request types: {str(e)}")
                await send_error_message(update, "حدث خطأ في جلب أنواع الطلبات.")
                return ConversationState.SERVICE_MENU
    except Exception as e:
        logger.error(f"Error fetching side children: {str(e)}")
        await send_error_message(update, "حدث خطأ في جلب بيانات الجهات الفرعية.")
        return ConversationState.SERVICE_MENU


async def fill_form(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة محسنة لملء النموذج"""
    try:
        # استخدام المعالج المحسن
        return await form_handler.handle_field_input(update, context)
    except Exception as e:
        logger.error(f"Error in improved form handler: {str(e)}")
        # استخدام معالج الأخطاء المحسن
        if error_handler:
            return await error_handler.handle_validation_error(
                update, context, None, f"حدث خطأ: {str(e)}"
            )
        else:
            await update.message.reply_text("حدث خطأ غير متوقع. حاول مرة أخرى.")
            return ConversationState.MAIN_MENU




async def create_location_keyboard(include_back=True, include_main_menu=True):
    keyboard = [[KeyboardButton("📍 مشاركة الموقع", request_location=True)]]
    if include_back:
        keyboard.append(["▶️ الرجوع"])
    if include_main_menu:
        keyboard.append([MAIN_MENU_BUTTON])
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=True
    )

async def handle_location(update: Update, context) -> int:
    logger.info("handle_location function called")
    form = context.user_data.get('form')
    field = context.user_data['current_form_field']
    
    location = update.message.location
    lat = location.latitude
    lng = location.longitude

    # Add this line to log/print the received values
    logger.info(f"Received field{lat}, longitude={lng}  ,,{field}")

    value = json.dumps({"lat": lat, "lng": lng})

    is_valid, error = field.validate(value)
    if not is_valid:
        await send_error_message(update, error)
        return ConversationState.FILL_FORM

    form.data[str(field.id)] = value
    context.user_data['form_field_history'].append(field.id)

    next_field = form.get_next_field(context)
    if next_field:
        return await show_form_field(update, context, next_field)
    else:
        return await show_form_summary(update, context)
    

    
async def go_back_to_previous_field(update: Update, context, form) -> int:
    """Go back to the previous form field"""
    field_history = context.user_data.get('form_field_history', [])
    
    if not field_history:
        # No previous fields, go back to subject selection
        await update.message.reply_text("العودة إلى اختيار الموضوع...")
        return ConversationState.SELECT_SUBJECT
    
    # Get previous field
    previous_field = field_history.pop()
    context.user_data['current_form_field'] = previous_field
    
    # Remove the current field's data if it exists
    if hasattr(previous_field, 'id'):
        form.data.pop(str(previous_field.id), None)
        form.document_data.pop(previous_field.id, None)
    
    # Show the previous field
    await show_form_field(update, context, previous_field)
    return ConversationState.FILL_FORM



async def move_to_next_field(update: Update, context, form) -> int:
    """Move to the next form field"""
    # Add current field to history for back navigation
    current_field = context.user_data.get('current_form_field')
    if current_field:
        field_history = context.user_data.get('form_field_history', [])
        field_history.append(current_field)
        context.user_data['form_field_history'] = field_history

    # Get next field
    next_field = form.get_next_field(context)
    if next_field:
        context.user_data['current_form_field'] = next_field
        await show_form_field(update, context, next_field)
        return ConversationState.FILL_FORM
    else:
        form_data = form.to_dict()
        if 'request_type' in context.user_data:
            form_data['request_type_id'] = context.user_data['request_type']['id']
        if 'selected_complaint_subject' in context.user_data:
            form_data['complaint_subject_id'] = context.user_data['selected_complaint_subject']['id']
        if 'selected_category' in context.user_data:
            form_data['complaint_service_id'] = context.user_data['selected_category']['value']
        if 'side_id' in context.user_data:
            form_data['side_id'] = context.user_data['side_id']
        if 'selected_other_subject' in context.user_data:
            form_data['other_subject_id'] = context.user_data['selected_other_subject']['id']
        
        context.user_data["form_data_for_submission"] = form_data

        return await show_form_summary(update, context)

def convert_mobile_format(mobile: str) -> str:
    cleaned = ''.join(filter(str.isdigit, mobile))
    expected_prefix = MOBILE_PREFIX.lstrip('+')
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
    
    return f"{MOBILE_PREFIX} {formatted}"
 

async def collect_form_field(update: Update, context) -> int:
    logger.debug("Entered collect_form_field")
    await update.message.reply_text("Field collected.")
    return ConversationState.CONFIRM_SUBMISSION


async def confirm_submission(update: Update, context) -> int:
    update_last_activity(context)
    if update.message.text == '▶️ الرجوع':
        form = context.user_data.get("form")
        history = context.user_data.get("form_field_history")
        if form and history:
            last_field = history[-1]  
            return await show_form_field(update, context, last_field)
        else:
            return await show_form_summary(update, context)
    if update.message.text == MAIN_MENU_BUTTON:
        await show_main_menu(update, context, message="☑️ YourVoiceSyBot v1.0.0")
        return ConversationState.MAIN_MENU

    if update.message.text != 'تأكيد الإرسال':
        await update.message.reply_text(
            "يرجى الضغط على 'تأكيد الإرسال' لتأكيد الإرسال أو '▶️ الرجوع' للتعديل.",
            reply_markup=await create_reply_keyboard([['تأكيد الإرسال'], ['▶️ الرجوع', MAIN_MENU_BUTTON]])
        )
        return ConversationState.CONFIRM_SUBMISSION

    form = context.user_data.get('form')
    if not form:
        await update.message.reply_text('حدث خطأ في النموذج. يرجى المحاولة مرة أخرى.')
        return ConversationHandler.END

    form_data = context.user_data.get('form_data_for_submission', {})
    if not form_data:
        await update.message.reply_text('حدث خطأ في بيانات النموذج. يرجى المحاولة مرة أخرى.')
        return ConversationHandler.END

    try:
        response = await api_service.submit_complaint(form_data)
        request_number = response.get('request_number')
       
        await update.message.reply_text(
            f"تم تسجيل الشكوى بنجاح. الطلب الخاص بكم أخذ الرقم {request_number}",
            reply_markup=get_main_menu_keyboard()
        )   
        for key in [
            "form", "form_data_for_submission", "side_id",
            "request_type", "selected_complaint_subject",
            "selected_category", "selected_other_subject",
            "current_form_field", "form_field_history"
        ]:
         context.user_data.pop(key, None)
        context.user_data['conversation_state'] = ConversationState.MAIN_MENU
        return ConversationState.MAIN_MENU

    except Exception as e:
        logger.error(f"Error submitting complaint: {str(e)}")
        await update.message.reply_text(
            "حدث خطأ أثناء إرسال الطلب. يرجى المحاولة لاحقاً.",
            reply_markup=await create_reply_keyboard([['▶️ الرجوع', MAIN_MENU_BUTTON]])
        )
        return ConversationState.CONFIRM_SUBMISSION


async def select_request_number(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_input = update.message.text
    logger.debug(f"=== DEBUG: Request number selection: {user_input} ===")

    if user_input == "▶️ الرجوع":
        return await handle_back(update, context, select_request_number)
    if user_input == MAIN_MENU_BUTTON:
        await show_main_menu(update, context, message="☑️ YourVoiceSyBot v1.0.0")
        return ConversationState.MAIN_MENU
    if user_input in ["الصفحة السابقة", "الصفحة التالية"]:
        requests = context.user_data.get('requests', [])
        if user_input == "الصفحة السابقة":
            context.user_data['requests_page'] = max(context.user_data.get('requests_page', 0) - 1, 0)
        elif user_input == "الصفحة التالية":
            total_pages = (len(requests) + 5 - 1) // 5
            context.user_data['requests_page'] = min(
                context.user_data.get('requests_page', 0) + 1, total_pages - 1
            )
        return await display_user_requests(update, context)

    requests = context.user_data.get('requests', [])
    selected_request = next((req for req in requests if str(req['request_number']) == user_input), None)

    if not selected_request:
        await update.message.reply_text(
            "يرجى اختيار رقم طلب صالح.",
            reply_markup=get_service_menu_keyboard()
        )
        return ConversationState.SERVICE_MENU

    try:
        request_number = selected_request['request_number']
        response = await api_service.get_user_request_info(request_number)
        request_info = response

        # -------------------------
        # Build request details text
        # -------------------------
        message = f"تفاصيل الطلب رقم {request_number}:\n\n"
        message += "📋 معلومات الطلب:\n"
        for group in request_info.get('groups', []):
            message += f"**{group['name']}**\n"
            for attr in group.get('attributes', []):
                message += f"- {attr['name']}: {attr['value']}\n"
            message += "\n"

        message += "📅 سجل الحالة:\n"
        for cycle in request_info.get('request_cycles', []):
            message += f"الحالة : {cycle['status_name']}\n"
            message += f"التاريخ : {cycle['date']} | {cycle['time']}\n"
            if cycle['side']:
                message += f"الجهة : {cycle['side']}\n"
            if cycle['citizen_notes']:
                message += f"الملاحظات : {cycle['citizen_notes']}\n"
            if cycle['reject_reason']:
                message += f"اسباب الرفض : {cycle['reject_reason']}\n"
            message += f"---------------------------------------------------\n"
        # -------------------------
        # Handle attachments
        # -------------------------
        message += "📎 المرفقات:\n"
        documents = request_info.get('documents', [])
        context.user_data['file_metadata'] = context.user_data.get('file_metadata', {})

        inline_keyboard = []
        doc_groups = {}
        for doc in documents:
            doc_name = doc['documents_type_name']
            doc_id = str(doc['documents_type_id'])
            if doc_name not in doc_groups:
                doc_groups[doc_name] = {'file_ids': [], 'doc_id': doc_id}
            for file in doc.get('values', []):
                file_id = str(file['file_id'])
                file_path = file['file_path']
                mime_type = file.get('mime_type', 'application/octet-stream')
                file_name = file.get('file_name', file_path.split('/')[-1])
                context.user_data['file_metadata'][file_id] = {
                    'file_path': file_path,
                    'mime_type': mime_type,
                    'documents_type_name': doc_name,
                    'file_name': file_name
                }
                doc_groups[doc_name]['file_ids'].append(file_id)

        for doc_name, info in sorted(doc_groups.items()):
            file_ids = info['file_ids']
            if file_ids:
                callback_data = f"view_files:{','.join(file_ids)}"
                inline_keyboard.append([
                    InlineKeyboardButton(
                        text=f" عرض {doc_name} ({len(file_ids)} ملف)",
                        callback_data=callback_data
                    )
                ])
            else:
                message += f"- {doc_name}: لا توجد مرفقات\n"

        if not documents:
            message += "لاتوجد مرفقات\n"
        # -------------------------
        # Pagination keyboard
        # -------------------------
        current_page = context.user_data.get('requests_page', 0)
        items_per_page = 5
        start_idx = current_page * items_per_page
        end_idx = min(start_idx + items_per_page, len(requests))
        page_requests = requests[start_idx:end_idx]

        reply_keyboard = [[str(req['request_number'])] for req in page_requests]
        nav_buttons = []
        total_pages = (len(requests) + items_per_page - 1) // items_per_page
        if current_page > 0:
            nav_buttons.append("الصفحة السابقة")
        if current_page < total_pages - 1:
            nav_buttons.append("الصفحة التالية")
        if nav_buttons:
            reply_keyboard.append(nav_buttons)
        reply_keyboard.append(['▶️ الرجوع', MAIN_MENU_BUTTON])

        # -------------------------
        # Send everything in one message
        # -------------------------
        reply_markup = InlineKeyboardMarkup(inline_keyboard) if inline_keyboard else None

        await update.message.reply_text(
            message,
            parse_mode='Markdown',
            reply_markup=reply_markup,
            disable_web_page_preview=True
        )

        return ConversationState.SELECT_REQUEST_NUMBER

    except Exception as e:
        logger.error(f"Error fetching request info for {user_input}: {str(e)}")
        await update.message.reply_text(
            "حدث خطأ أثناء جلب تفاصيل الطلب. يرجى المحاولة لاحقاً.",
            reply_markup=get_service_menu_keyboard()
        )
        return ConversationState.SERVICE_MENU

async def handle_view_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.debug(f"handle_view_file called with update: {update}")
    query = update.callback_query
    if not query:
        logger.error("No callback_query found in update")
        return

    await query.answer()
    logger.debug(f"Callback data received: {query.data}")

    try:
        if not query.data.startswith(("view_file:", "view_files:")):
            logger.error(f"Invalid callback data format: {query.data}")
            await query.message.reply_text("خطأ: بيانات غير صالحة.")
            return

        # Extract file IDs
        if query.data.startswith("view_file:"):
            file_ids = [query.data.split(":", 1)[1]]
        else:
            file_id_str = query.data.split(":", 1)[1]
            file_ids = file_id_str.split(",") if file_id_str else []

        if not file_ids:
            logger.error("No file IDs found in callback data")
            await query.message.reply_text("خطأ: لا توجد ملفات لعرضها.")
            return

        file_number = 1
        for file_id in file_ids:
            if not file_id:
                continue

            # Retrieve metadata
            file_metadata = context.user_data.get("file_metadata", {}).get(file_id)
            if not file_metadata:
                await query.message.reply_text(f"خطأ: بيانات الملف غير موجودة (ID: {file_id}).")
                continue

            file_path = file_metadata["file_path"]
            mime_type = file_metadata.get("mime_type", "application/octet-stream")
            doc_name = file_metadata.get("documents_type_name", "مرفق")
            file_name = file_metadata.get("file_name", file_path.split("/")[-1])
            caption = f"{doc_name} الملف رقم ({file_number})"
            file_url = f"{settings.image_base_url}{file_path}"

            logger.debug(f"Fetching file: {file_url}, MIME type: {mime_type}, Caption: {caption}")

            headers = {
                "Accept": "image/*,application/pdf,application/octet-stream",
                "Authorization": api_service.headers.get("Authorization", "")
            }

            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(file_url, headers=headers)
                    response.raise_for_status()
                    content_type = response.headers.get("content-type", "").lower()
                    effective_mime_type = mime_type if mime_type != "application/octet-stream" else content_type
                    file_data = response.content

                # size checks
                if len(file_data) > 10 * 1024 * 1024 and effective_mime_type.startswith("image/"):
                    await query.message.reply_text(f"خطأ: الصورة كبيرة جدًا ({caption}).")
                    continue
                if len(file_data) > 50 * 1024 * 1024:
                    await query.message.reply_text(f"خطأ: المستند كبير جدًا ({caption}).")
                    continue

                # wrap as file-like
                file_bytes = io.BytesIO(file_data)
                file_bytes.name = file_name

                if effective_mime_type.startswith("image/"):
                    await query.message.reply_photo(file_bytes, caption=caption)
                else:
                    await query.message.reply_document(file_bytes, filename=file_name, caption=caption)

                logger.debug(f"Successfully sent file: {file_id} with caption: {caption}")

            except httpx.HTTPError as e:
                logger.error(f"HTTP error fetching file: {str(e)}")
                await query.message.reply_text(f"فشل في جلب المرفق: {caption}")
            except Exception as e:
                logger.error(f"Unexpected error in handle_view_file: {str(e)}")
                await query.message.reply_text(f"حدث خطأ غير متوقع أثناء إرسال المرفق: {caption}")

            file_number += 1
    except Exception as e:
                logger.error(f"Unexpected error in handle_view_file: {str(e)}")

async def select_subject(update: Update, context) -> int:
    update_last_activity(context)
    selected_text = update.message.text
    logger.debug(f"=== DEBUG: Subject selection: {selected_text} ===")
    
    if selected_text == '▶️ الرجوع':
        return await handle_back(update, context, ConversationState.SELECT_SUBJECT)
    if selected_text == MAIN_MENU_BUTTON:
        await show_main_menu(update, context, message="☑️ YourVoiceSyBot v1.0.0")
        return ConversationState.MAIN_MENU
    
    subjects = context.user_data.get('api_data', {}).get('complaint_subjects', [])
    selected_subject = next((item for item in subjects if item['name'] == selected_text), None)
    
    if not selected_subject:
        keyboard = [[item['name'] for item in subjects[i:i + 2]] for i in range(0, len(subjects), 2)]
        await send_error_message(
            update,
            'يرجى اختيار موضوع شكوى صالح.',
            keyboard_buttons=keyboard
        )
        return ConversationState.SELECT_SUBJECT
    
    context.user_data['selected_complaint_subject'] = {
        'id': selected_subject['id'],
        'name': selected_text
    }
    
    try:
        service_subject_code = context.user_data.get('service_subject_code')
        other_subject_code = context.user_data.get('other_subject_code')
        
        if selected_subject['code'] == service_subject_code:
            response = await api_service.get_service_categories(
                request_type_id=context.user_data['request_type']['id'],
                side_id=context.user_data['side_id']
            )
            categories = response.get('data', [])
            if not categories:
                await send_error_message(update, 'لا توجد فئات خدمات متاحة.')
                return ConversationState.SELECT_SUBJECT
            
            context.user_data['service_categories'] = categories  # حفظ الفئات
            
            keyboard = [[cat['text'] for cat in categories[i:i + 2]] for i in range(0, len(categories), 2)]
            await update.message.reply_text(
                'يرجى اختيار فئة الخدمة:',
                reply_markup=await create_reply_keyboard(keyboard)
            )
            context.user_data['selected_subject_id'] = selected_subject['id']
            return ConversationState.SELECT_SERVICE_CATEGORY
        
        elif selected_subject['code'] == other_subject_code:
            response = await api_service.get_other_request_type_subjects(
                request_type_id=context.user_data['request_type']['id'],
                side_id=context.user_data['side_id']
            )
            other_subjects = response.get('data', [])
            if not other_subjects:
                await send_error_message(update, 'لا توجد مواضيع أخرى متاحة.')
                return ConversationState.SELECT_SUBJECT
            
            keyboard = [[subj['name'] for subj in other_subjects[i:i + 2]] for i in range(0, len(other_subjects), 2)]
            await update.message.reply_text(
                'يرجى اختيار الموضوع الآخر:',
                reply_markup=await create_reply_keyboard(keyboard)
            )
            context.user_data['selected_subject_id'] = selected_subject['id']
            return ConversationState.SELECT_OTHER_SUBJECT
        
        else:
            try:
                # جلب النموذج
                response = await api_service.get_form_data(
                    request_type_id=context.user_data['request_type']['id'],
                    request_subject_id=selected_subject['id']
                )
                
                form = DynamicForm.from_dict(response)
                
                # بدء النموذج المحسن
                return await form_handler.start_form_filling(update, context, form)
                
            except Exception as e:
                logger.error(f"Error starting form: {str(e)}")
                return await error_handler.handle_validation_error(
                    update, context, None, f"خطأ في بدء النموذج: {str(e)}"
                )
    except Exception as e:
        logger.error(f"Error processing subject selection: {str(e)}")
        await send_error_message(update, f"خطأ في معالجة الموضوع: {str(e)}")
        return ConversationState.SERVICE_MENU

async def select_service_category(update: Update, context) -> int:
    update_last_activity(context)
    selected_text = update.message.text
    logger.debug(f"=== DEBUG: Service category selection: {selected_text} ===")
    
    if selected_text == '▶️ الرجوع':
        return await handle_back(update, context, ConversationState.SELECT_SERVICE_CATEGORY)
    if selected_text == MAIN_MENU_BUTTON:
        await show_main_menu(update, context, message="☑️ YourVoiceSyBot v1.0.0")
        return ConversationState.MAIN_MENU
    
    categories = context.user_data.get('service_categories', [])
    selected_category = next((cat for cat in categories if cat['text'] == selected_text), None)
    
    if not selected_category:
        keyboard = [[cat['text'] for cat in categories[i:i + 2]] for i in range(0, len(categories), 2)]
        await send_error_message(
            update,
            'يرجى اختيار فئة خدمة صالحة.',
            keyboard_buttons=keyboard
        )
        return ConversationState.SELECT_SERVICE_CATEGORY
    
    context.user_data['selected_category_id'] = selected_category['value']
    
    try:
        response = await api_service.get_services_for_category(
            category_id=selected_category['value'],
            request_type_id=context.user_data['request_type']['id']
        )
        services = response.get('data', [])
        if not services:
            await send_error_message(update, 'لا توجد خدمات متاحة لهذه الفئة.')
            return ConversationState.SELECT_SERVICE_CATEGORY
        
        context.user_data['services'] = services
        
        keyboard = [[serv['text'] for serv in services[i:i + 2]] for i in range(0, len(services), 2)]
        await update.message.reply_text(
            'يرجى اختيار الخدمة:',
            reply_markup=await create_reply_keyboard(keyboard)
        )
        return ConversationState.SELECT_SERVICE
    except Exception as e:
        logger.error(f"Error fetching services for category: {str(e)}")
        await send_error_message(update, f"خطأ في جلب الخدمات: {str(e)}")
        return ConversationState.SELECT_SERVICE_CATEGORY

async def select_service(update: Update, context) -> int:
    update_last_activity(context)
    selected_text = update.message.text
    logger.debug(f"=== DEBUG: Service selection: {selected_text} ===")
    
    if selected_text == '▶️ الرجوع':
        return await handle_back(update, context, ConversationState.SELECT_SERVICE)
    if selected_text == MAIN_MENU_BUTTON:
        await show_main_menu(update, context, message="☑️ YourVoiceSyBot v1.0.0")
        return ConversationState.MAIN_MENU
    
    services = context.user_data.get('services', [])
    selected_service = next((serv for serv in services if serv['text'] == selected_text), None)
    
    if not selected_service:
        keyboard = [[serv['text'] for serv in services[i:i + 2]] for i in range(0, len(services), 2)]
        await send_error_message(
            update,
            'يرجى اختيار خدمة صالحة.',
            keyboard_buttons=keyboard
        )
        return ConversationState.SELECT_SERVICE
    
    try:
        # جلب النموذج
        response = await api_service.get_form_data(
            request_type_id=context.user_data['request_type']['id'],
            request_subject_id=context.user_data['selected_subject_id'],
            complaint_service_id=selected_service['value']
        )
        
        form = DynamicForm.from_dict(response)
        
        # بدء النموذج المحسن
        return await form_handler.start_form_filling(update, context, form)
        
    except Exception as e:
        logger.error(f"Error starting form: {str(e)}")
        return await error_handler.handle_validation_error(
            update, context, None, f"خطأ في بدء النموذج: {str(e)}"
        )

async def select_other_subject(update: Update, context) -> int:
    update_last_activity(context)
    selected_text = update.message.text
    logger.debug(f"=== DEBUG: Other subject selection: {selected_text} ===")
    
    if selected_text == '▶️ الرجوع':
        return await handle_back(update, context, ConversationState.SELECT_OTHER_SUBJECT)
    if selected_text == MAIN_MENU_BUTTON:
        await show_main_menu(update, context, message="☑️ YourVoiceSyBot v1.0.0")
        return ConversationState.MAIN_MENU
    
    try:
        response = await api_service.get_other_request_type_subjects(
            request_type_id=context.user_data['request_type']['id'],
            side_id=context.user_data['side_id']
        )
        other_subjects = response.get('data', [])
        selected_other_subject = next((item for item in other_subjects if item['name'] == selected_text), None)
        
        if not selected_other_subject:
            keyboard = [[subj['name'] for subj in other_subjects[i:i + 2]] for i in range(0, len(other_subjects), 2)]
            await send_error_message(
                update,
                'يرجى اختيار موضوع آخر صالح.',
                keyboard_buttons=keyboard
            )
            return ConversationState.SELECT_OTHER_SUBJECT
        
        context.user_data['selected_other_subject'] = {
            'id': selected_other_subject['id'],
            'name': selected_text
        }
        
        # جلب النموذج
        response = await api_service.get_form_data(
            request_type_id=context.user_data['request_type']['id'],
            request_subject_id=context.user_data['selected_subject_id'],
            other_subject_id=selected_other_subject['id'],
            side_id=context.user_data['side_id']
        )
        
        form = DynamicForm.from_dict(response)
        
        # بدء النموذج المحسن
        return await form_handler.start_form_filling(update, context, form)
    except Exception as e:
        logger.error(f"Error fetching form data for other subject: {str(e)}")
        await send_error_message(update, f"خطأ في جلب بيانات النموذج: {str(e)}")
        return ConversationState.SERVICE_MENU



async def show_form_field(update: Update, context, field: Union[FormAttribute, FormDocument]) -> int:
    logger.debug(f"Showing field: {type(field).__name__}, ID: {field.id}, Name: {field.name if isinstance(field, FormAttribute) else field.documents_type_name}")
    form = context.user_data.get('form')
    if not form:
        logger.error("No form found in user_data")
        await send_error_message(update, 'حدث خطأ في النموذج. يرجى المحاولة مرة أخرى.')
        return ConversationHandler.END
    
    # Set current field and initialize history (do this early for all fields, including map)
    context.user_data['current_form_field'] = field
    context.user_data.setdefault('form_field_history', [])  # Initialize if not present
    
    # Check if we can go back (if there are previous fields in history)
    can_go_back = bool(context.user_data['form_field_history'])
    
    if isinstance(field, FormDocument):
        message = f"يرجى رفع {field.documents_type_name}.\nالملفات المسموحة: {', '.join(field.accept_extension)}"
        keyboard = []
        current_file_ids = form.document_data.get(field.id, [])
        if field.is_multi:
            message += f"\nيمكنك رفع ملفات متعددة. (تم رفع {len(current_file_ids)} ملف{'ات' if len(current_file_ids) != 1 else ''} حتى الآن)"
            keyboard.append(['تم'])
        if not field.required and not current_file_ids:
            keyboard.append(['التالي'])
        
        # Add back button if we can go back
        if can_go_back:
            keyboard.append(['▶️ الرجوع'])
        
        await update.message.reply_text(
            message,
            reply_markup=await create_reply_keyboard(keyboard, include_back=can_go_back, include_main_menu=True)
        )
    else:
        group_name = next((group.name for group in form.groups if any(attr.id == field.id for attr in group.attributes)), "")
        if field.type_code == "switch":
            keyboard = [["نعم", "لا"]]
            if not field.required:
                keyboard.append(["التالي"])
            message = f"{group_name}\nيرجى اختيار {field.name}"
            if field.example:
                message += f"\nمثال: {field.example}"
            await update.message.reply_text(
                message,
                reply_markup=await create_reply_keyboard(keyboard)
            )
            return ConversationState.FILL_FORM
        if field.type_code in ["options", "autocomplete", "multiple_autocomplete", "multi_options"]:
            options = await field.get_autocomplete_options(api_service) if field.type_code in ["autocomplete", "multiple_autocomplete"] else field.options
            option_names = [option['name'] for option in options]
            keyboard = [option_names[i:i + 2] for i in range(0, len(option_names), 2)]
            if field.type_code in ["multiple_autocomplete", "multi_options"]:
                selected_values = field.get_selected_values()
                if selected_values:
                    keyboard.append(['تم'])
            if not field.required:
                keyboard.append(['التالي'])
            message = f"{group_name}\nيرجى اختيار {field.name}:"
            if field.example:
                message += f"\nمثال: {field.example}"
            await update.message.reply_text(
                message,
                reply_markup=await create_reply_keyboard(keyboard, one_time=True)
            )
            return ConversationState.FILL_FORM
        if field.type_code == "map":
            group_name = next((group.name for group in form.groups if any(attr.id == field.id for attr in group.attributes)), "")
            message = f"{group_name}\nيرجى مشاركة موقعك من الخريطة باستخدام الزر أدناه (لا يمكن إدخال النص يدويًا):"
            if field.example:
                message += f"\nمثال: {field.example}"
            await update.message.reply_text(
                message,
                reply_markup=await create_location_keyboard(include_back=can_go_back, include_main_menu=True)
            )
            return ConversationState.FILL_FORM
        else:
            keyboard = []
            if not field.required:
                keyboard.append(['التالي'])
            message = f"{group_name}\nيرجى إدخال {field.name}:"
            if field.example:
                message += f"\nمثال: {field.example}"
            await update.message.reply_text(
                message,
                reply_markup=await create_reply_keyboard(keyboard)
            )
    return ConversationState.FILL_FORM


async def show_form_summary(update: Update, context) -> int:
    form = context.user_data.get('form')
    if not form:
        logger.error("No form found in user_data")
        await update.message.reply_text('حدث خطأ في النموذج. يرجى المحاولة مرة أخرى.')
        return ConversationHandler.END
    
    message = "ملخص النموذج:\n\n"
    for group in form.groups:
        message += f"**{group.name}**\n"
        for attr in group.attributes:
            value = form.data.get(str(attr.id), "غير مُدخل")
            if attr.type_code == 'switch':
                if value == 'true':
                    value = 'نعم'
                elif value == 'false':
                    value = 'لا'
            if isinstance(value, list):
                value = ", ".join(str(v) for v in value)
            message += f"- {attr.name}: {value}\n"
        message += "\n"
    
    message += "📎 المرفقات:\n"
    for doc in form.document_data:
        doc_type = next((d.documents_type_name for d in form.documents if d.id == int(doc)), "غير معروف")
        file_count = len(form.document_data[doc])
        message += f"- {doc_type}: {file_count} ملف{'' if file_count == 1 else 'ات'}\n"
    
    keyboard = [['تأكيد الإرسال'], ['▶️ الرجوع', MAIN_MENU_BUTTON]]
    await update.message.reply_text(
        message,
        parse_mode='Markdown',
        reply_markup=await create_reply_keyboard(keyboard)
    )
    return ConversationState.CONFIRM_SUBMISSION



async def select_time_am_pm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    update_last_activity(context)
    am_pm = update.message.text

    if am_pm not in ['AM', 'PM']:
        await update.message.reply_text(
            "يرجى اختيار AM أو PM:",
            reply_markup=await create_reply_keyboard([['AM', 'PM'], ['▶️ الرجوع', MAIN_MENU_BUTTON]])
        )
        return ConversationState.SELECT_TIME_AM_PM

    temp_time = context.user_data.get('temp_time_input')
    field_id = context.user_data.get('pending_time_field_id')
    form = context.user_data.get('form')

    if not temp_time or not field_id or not form:
        logger.error("Missing context data for time field")
        await send_error_message(update, "حدث خطأ أثناء معالجة الوقت. يرجى المحاولة مرة أخرى.")
        return ConversationState.FILL_FORM

    try:
        full_input = f"{temp_time} {am_pm}"
        input_time = datetime.strptime(full_input, "%I:%M %p").time()

        # get field back
        field = form.get_field_by_id(field_id)
        if not field:
            logger.error(f"Field with ID {field_id} not found")
            await send_error_message(update, "حدث خطأ في النموذج. يرجى المحاولة مرة أخرى.")
            return ConversationState.FILL_FORM

        min_time_str = field.extra.get('min_time', '00:00:00')
        max_time_str = field.extra.get('max_time', '23:59:59')
        min_time = datetime.strptime(min_time_str, "%H:%M:%S").time()
        max_time = datetime.strptime(max_time_str, "%H:%M:%S").time()

        if not (min_time <= input_time <= max_time):
            period_min = field.extra.get('period_min_time', min_time.strftime("%I:%M %p"))
            period_max = field.extra.get('period_max_time', max_time.strftime("%I:%M %p"))
            await send_error_message(update, f"الوقت يجب أن يكون بين {period_min} و {period_max}.")
            return ConversationState.FILL_FORM

        # ✅ Save
        form.data[str(field.id)] = full_input
        context.user_data.pop('temp_time_input', None)
        context.user_data.pop('pending_time_field_id', None)

        # go next using the move_to_next_field helper
        return await move_to_next_field(update, context, form)

    except ValueError as e:
        logger.error(f"Time parsing error: {str(e)}")
        await send_error_message(update, "يرجى إدخال وقت صحيح بالصيغة hh:mm ")
        return ConversationState.FILL_FORM
    except Exception as e:
        logger.error(f"Unexpected error in select_time_am_pm: {str(e)}")
        await send_error_message(update, "حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى.")
        return ConversationState.FILL_FORM




async def cancel(update: Update, context) -> int:
    await update.message.reply_text(
        "تم إلغاء العملية. يمكنك البدء من جديد باستخدام /start.",
        reply_markup=get_main_menu_keyboard()
    )
    context.user_data.clear()
    return ConversationHandler.END

def get_main_menu_keyboard():
    keyboard = [[option] for option in MAIN_MENU_OPTIONS]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

async def main_menu_handler(update: Update, context) -> int:
    logger.debug("main_menu_handler called")
    # Redirect to main_menu to handle any stray text input
    return await main_menu(update, context)

async def handle_location_improved(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة محسنة للموقع"""
    try:
        # الحصول على الحقل الحالي
        progress_tracker = context.user_data.get('form_progress')
        if not progress_tracker:
            await update.message.reply_text("حدث خطأ في النموذج. يرجى المحاولة مرة أخرى.")
            return ConversationHandler.END
            
        current_field = progress_tracker.get_current_field()
        if not current_field or not hasattr(current_field, 'type_code') or current_field.type_code != 'map':
            await update.message.reply_text("هذا الحقل لا يتطلب موقع.")
            return ConversationState.FILL_FORM
            
        # استخدام معالج الموقع المحسن
        success, message, location_data = await location_handler.handle_location_input(
            update, context, current_field
        )
        
        if success:
            # حفظ البيانات
            field_state = progress_tracker.field_states[str(current_field.id)]
            field_state.set_value(location_data)
            
            # الانتقال للحقل التالي
            return await form_handler.go_to_next_field(update, context)
        else:
            await update.message.reply_text(f"❌ {message}")
            return ConversationState.FILL_FORM
            
    except Exception as e:
        logger.error(f"Error handling location: {str(e)}")
        return await error_handler.handle_validation_error(
            update, context, None, f"خطأ في معالجة الموقع: {str(e)}"
        )

async def handle_attachment_improved(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة محسنة للمرفقات"""
    try:
        # الحصول على الحقل الحالي
        progress_tracker = context.user_data.get('form_progress')
        if not progress_tracker:
            await update.message.reply_text("حدث خطأ في النموذج. يرجى المحاولة مرة أخرى.")
            return ConversationHandler.END
            
        current_field = progress_tracker.get_current_field()
        if not current_field or not isinstance(current_field, FormDocument):
            await update.message.reply_text("هذا الحقل لا يتطلب ملف.")
            return ConversationState.FILL_FORM
            
        # استخدام معالج الملفات المحسن
        success, message, file_id = await file_handler.handle_file_upload(
            update, context, current_field
        )
        
        if success:
            # حفظ البيانات
            field_state = progress_tracker.field_states[str(current_field.id)]
            field_state.add_attachment(file_id, "uploaded_file")
            
            # عرض رسالة نجاح
            await update.message.reply_text(f"✅ {message}")
            
            # إذا كان الحقل يتطلب ملف واحد، انتقل للتالي
            if not current_field.is_multi:
                return await form_handler.go_to_next_field(update, context)
            else:
                # إعادة عرض الحقل للملفات الإضافية
                return await form_handler.show_current_field(update, context)
        else:
            await update.message.reply_text(f"❌ {message}")
            return ConversationState.FILL_FORM
            
    except Exception as e:
        logger.error(f"Error handling attachment: {str(e)}")
        return await error_handler.handle_validation_error(
            update, context, None, f"خطأ في معالجة الملف: {str(e)}"
        )



async def main():
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    logger = logging.getLogger(__name__)
    
    logger.info("Initializing bot...")
    try:
        await initialize_bot()
        logger.info("Bot initialization complete.")
    except Exception as e:
        logger.error(f"Failed to initialize bot: {str(e)}")
        logger.warning("Proceeding with fallback settings...")
    
    application = Application.builder().token(settings.telegram_token).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            ConversationState.MAIN_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, main_menu)],
            ConversationState.SERVICE_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, service_menu)],
            ConversationState.ENTER_MOBILE: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_mobile)],
            ConversationState.ENTER_OTP: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_otp)],
            ConversationState.SELECT_REQUEST_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_request_type)],
            ConversationState.SELECT_COMPLAINT_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_subject)],
            ConversationState.SELECT_COMPLIMENT_SIDE: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_compliment_side)],
            ConversationState.FILL_FORM: [
                    MessageHandler(filters.LOCATION, handle_location_improved),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, fill_form),
                    MessageHandler(filters.ATTACHMENT, handle_attachment_improved),
                ],
            ConversationState.SELECT_SERVICE_CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_service_category)],
            ConversationState.COLLECT_FORM_FIELD: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_form_field)],
            ConversationState.CONFIRM_SUBMISSION: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_submission)],
            ConversationState.SELECT_REQUEST_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_request_number)],
            ConversationState.SELECT_SERVICE: [MessageHandler(filters.TEXT & ~filters.COMMAND,select_service)],
            ConversationState.SELECT_SUBJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND,select_subject)],
            ConversationState.SELECT_OTHER_SUBJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_other_subject)],
            ConversationState.SELECT_TIME_AM_PM: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_time_am_pm)],
        },
       
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    application.add_handler(conv_handler)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, main_menu_handler))
    # application.add_handler(CallbackQueryHandler(handle_view_file, pattern='^view_files?:.*$'))
    application.add_handler(CallbackQueryHandler(handle_view_file, pattern=r"^view_files:"))
    application.add_handler(MessageHandler(filters.LOCATION, lambda update, context: logger.info(f"Global location catch: {update.message.location}")))
    # application.add_handler(MessageHandler(filters.LOCATION & ~filters.COMMAND, handle_location))
   
    
    
    logger.info("Starting polling...")
    await application.initialize()
    await application.start()
    await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    logger.info("Bot is polling...")

    try:
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        logger.info("Shutting down bot...")
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
        logger.info("Bot stopped.")

if __name__ == '__main__':
    asyncio.run(main())
