from enum import Enum

class ConversationState(Enum):
    """حالات المحادثة في البوت"""
    
    # حالات المصادقة
    AUTH_CHECK = "auth_check"
    ENTER_MOBILE = "enter_mobile"
    ENTER_OTP = "enter_otp"
    
    # القائمة الرئيسية
    MAIN_MENU = "main_menu"
    
    # قائمة الخدمات
    SERVICE_MENU = "service_menu"
    
    # عرض الطلبات
    VIEW_REQUESTS = "view_requests"
    VIEW_REQUEST_DETAILS = "view_request_details"
    
    # تقديم طلب جديد
    SELECT_ENTITY = "select_entity"
    SELECT_ENTITY_CHILDREN = "select_entity_children"
    SELECT_REQUEST_TYPE = "select_request_type"
    SELECT_SUBJECTS = "select_subjects"
    
    # اختيار الخدمات (للنوع service)
    SELECT_SERVICE_CATEGORY = "select_service_category"
    SELECT_SERVICE = "select_service"
    
    # ملء النموذج
    FILL_FORM = "fill_form"
    COLLECT_FORM_FIELD = "collect_form_field"
    CONFIRM_SUBMISSION = "confirm_submission"
    
    # حالات خاصة
    ERROR = "error"
    HELP = "help"
