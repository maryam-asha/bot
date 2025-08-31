import logging
from typing import Dict, List, Optional, Union, Any, Tuple
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from forms.form_model import FormAttribute, FormDocument
from config.conversation_states import ConversationState
import re
import json

logger = logging.getLogger(__name__)

class FormErrorHandler:
    """معالج أخطاء النموذج"""
    
    def __init__(self):
        self.error_messages = {
            'required_field': 'حقل {field_name} مطلوب',
            'invalid_format': 'تنسيق {field_name} غير صحيح',
            'too_short': '{field_name} قصير جداً. الحد الأدنى: {min_length}',
            'too_long': '{field_name} طويل جداً. الحد الأقصى: {max_length}',
            'out_of_range': '{field_name} خارج النطاق المسموح',
            'invalid_option': 'الخيار المحدد غير صحيح',
            'file_too_large': 'حجم الملف كبير جداً. الحد الأقصى: {max_size}',
            'unsupported_file_type': 'نوع الملف غير مدعوم',
            'invalid_location': 'الموقع غير صحيح',
            'network_error': 'خطأ في الشبكة. يرجى المحاولة لاحقاً',
            'server_error': 'خطأ في الخادم. يرجى المحاولة لاحقاً',
            'validation_error': 'خطأ في التحقق من صحة البيانات',
            'timeout_error': 'انتهت مهلة العملية. يرجى المحاولة مرة أخرى'
        }
        
    def get_error_message(self, error_type: str, **kwargs) -> str:
        """الحصول على رسالة خطأ"""
        message_template = self.error_messages.get(error_type, 'حدث خطأ غير متوقع')
        try:
            return message_template.format(**kwargs)
        except KeyError:
            return message_template
            
    def format_validation_error(self, field_name: str, error_type: str, **kwargs) -> str:
        """تنسيق رسالة خطأ الفاليديشن"""
        kwargs['field_name'] = field_name
        return self.get_error_message(error_type, **kwargs)
        
    async def handle_validation_error(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                    field: Union[FormAttribute, FormDocument], error_message: str) -> int:
        """معالجة خطأ الفاليديشن"""
        # إضافة رسالة مساعدة
        help_message = await self.get_field_help_message(field)
        
        # إضافة مثال إذا كان متوفراً
        example_message = ""
        if hasattr(field, 'example') and field.example:
            example_message = f"\n💡 مثال: {field.example}"
            
        # إضافة اقتراحات التصحيح
        suggestions = await self.get_correction_suggestions(field, error_message)
        
        full_message = f"❌ {error_message}"
        if help_message:
            full_message += f"\n\nℹ️ {help_message}"
        if example_message:
            full_message += example_message
        if suggestions:
            full_message += f"\n\n💡 اقتراحات:\n{suggestions}"
            
        # إعادة عرض الحقل مع رسالة الخطأ
        await update.message.reply_text(full_message)
        
        # إعادة عرض الحقل
        return await self.redisplay_field(update, context, field)
        
    async def get_field_help_message(self, field: Union[FormAttribute, FormDocument]) -> str:
        """الحصول على رسالة مساعدة للحقل"""
        if hasattr(field, 'help_text') and field.help_text:
            return field.help_text
            
        # رسائل مساعدة افتراضية حسب نوع الحقل
        if isinstance(field, FormDocument):
            return f"يرجى رفع ملف بصيغة {', '.join(field.accept_extension)}"
            
        if field.type_code == 'text':
            if hasattr(field, 'min_length') and hasattr(field, 'max_length'):
                return f"يجب أن يكون النص بين {field.min_length} و {field.max_length} حرف"
            elif hasattr(field, 'min_length'):
                return f"يجب أن يكون النص على الأقل {field.min_length} حرف"
            elif hasattr(field, 'max_length'):
                return f"يجب أن يكون النص على الأكثر {field.max_length} حرف"
                
        elif field.type_code == 'number':
            if hasattr(field, 'min_value') and hasattr(field, 'max_value'):
                return f"يجب أن يكون الرقم بين {field.min_value} و {field.max_value}"
            elif hasattr(field, 'min_value'):
                return f"يجب أن يكون الرقم على الأقل {field.min_value}"
            elif hasattr(field, 'max_value'):
                return f"يجب أن يكون الرقم على الأكثر {field.max_value}"
                
        elif field.type_code == 'date':
            if hasattr(field, 'min_date') and hasattr(field, 'max_date'):
                return f"يجب أن يكون التاريخ بين {field.min_date} و {field.max_date}"
            elif hasattr(field, 'min_date'):
                return f"يجب أن يكون التاريخ بعد {field.min_date}"
            elif hasattr(field, 'max_date'):
                return f"يجب أن يكون التاريخ قبل {field.max_date}"
                
        elif field.type_code == 'time':
            if hasattr(field, 'min_time') and hasattr(field, 'max_time'):
                return f"يجب أن يكون الوقت بين {field.min_time} و {field.max_time}"
            elif hasattr(field, 'min_time'):
                return f"يجب أن يكون الوقت بعد {field.min_time}"
            elif hasattr(field, 'max_time'):
                return f"يجب أن يكون الوقت قبل {field.max_time}"
                
        elif field.type_code == 'email':
            return "يجب أن يكون البريد الإلكتروني بصيغة صحيحة مثل: example@domain.com"
            
        elif field.type_code == 'phone':
            return "يجب أن يكون رقم الهاتف بصيغة صحيحة مثل: 09xxxxxxxx"
            
        return "يرجى إدخال قيمة صحيحة"
        
    async def get_correction_suggestions(self, field: Union[FormAttribute, FormDocument], error_message: str) -> str:
        """الحصول على اقتراحات التصحيح"""
        suggestions = []
        
        if isinstance(field, FormDocument):
            if "حجم الملف" in error_message:
                suggestions.append("جرب ضغط الملف أو اختيار ملف أصغر")
            elif "نوع الملف" in error_message:
                suggestions.append(f"تأكد من أن الملف بصيغة {', '.join(field.accept_extension)}")
                
        elif field.type_code == 'text':
            if "قصير" in error_message:
                suggestions.append("أضف المزيد من التفاصيل")
            elif "طويل" in error_message:
                suggestions.append("اختصر النص")
            elif "تنسيق" in error_message:
                suggestions.append("تأكد من صحة التنسيق")
                
        elif field.type_code == 'number':
            if "خارج النطاق" in error_message:
                suggestions.append("تأكد من أن الرقم ضمن النطاق المسموح")
            elif "رقم" in error_message:
                suggestions.append("تأكد من إدخال أرقام فقط")
                
        elif field.type_code == 'date':
            if "تنسيق" in error_message:
                suggestions.append("استخدم تنسيق YYYY-MM-DD")
            elif "خارج النطاق" in error_message:
                suggestions.append("تأكد من أن التاريخ ضمن النطاق المسموح")
                
        elif field.type_code == 'time':
            if "تنسيق" in error_message:
                suggestions.append("استخدم تنسيق HH:MM أو HH:MM AM/PM")
            elif "خارج النطاق" in error_message:
                suggestions.append("تأكد من أن الوقت ضمن النطاق المسموح")
                
        elif field.type_code == 'email':
            suggestions.append("تأكد من وجود @ و . في البريد الإلكتروني")
            suggestions.append("تأكد من عدم وجود مسافات")
            
        elif field.type_code == 'phone':
            suggestions.append("تأكد من إدخال أرقام فقط")
            suggestions.append("تأكد من صحة رقم البلد")
            
        if not suggestions:
            suggestions.append("راجع التعليمات أعلاه")
            
        return "\n".join(f"• {suggestion}" for suggestion in suggestions)
        
    async def redisplay_field(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                             field: Union[FormAttribute, FormDocument]) -> int:
        """إعادة عرض الحقل"""
        # هنا نحتاج لإعادة عرض الحقل
        # سنقوم بتنفيذ ذلك في المعالج الرئيسي
        return ConversationState.FILL_FORM
        
    async def handle_network_error(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                 error: Exception, retry_count: int = 0) -> int:
        """معالجة خطأ الشبكة"""
        max_retries = 3
        
        if retry_count < max_retries:
            # محاولة إعادة المحاولة
            retry_message = f"خطأ في الشبكة. محاولة {retry_count + 1} من {max_retries}..."
            await update.message.reply_text(retry_message)
            
            # انتظار قبل إعادة المحاولة
            import asyncio
            await asyncio.sleep(2 ** retry_count)  # تأخير متزايد
            
            return await self.retry_operation(update, context, retry_count + 1)
        else:
            # فشلت جميع المحاولات
            error_message = self.get_error_message('network_error')
            await update.message.reply_text(error_message)
            
            # العودة للقائمة الرئيسية
            return ConversationState.MAIN_MENU
            
    async def retry_operation(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                            retry_count: int) -> int:
        """إعادة محاولة العملية"""
        # هنا نقوم بإعادة تنفيذ العملية
        # سيتم تنفيذ ذلك في المعالج الرئيسي
        return ConversationState.FILL_FORM
        
    async def handle_server_error(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                error: Exception) -> int:
        """معالجة خطأ الخادم"""
        error_message = self.get_error_message('server_error')
        
        # إضافة تفاصيل الخطأ للمطورين
        if hasattr(error, 'response') and hasattr(error.response, 'status_code'):
            error_message += f"\nرمز الخطأ: {error.response.status_code}"
            
        await update.message.reply_text(error_message)
        
        # حفظ الخطأ للتشخيص
        await self.log_error_for_diagnosis(context, error)
        
        # العودة للقائمة الرئيسية
        return ConversationState.MAIN_MENU
        
    async def log_error_for_diagnosis(self, context: ContextTypes.DEFAULT_TYPE, error: Exception):
        """تسجيل الخطأ للتشخيص"""
        error_log = {
            'timestamp': datetime.now().isoformat(),
            'user_id': context.user_data.get('user_id'),
            'error_type': type(error).__name__,
            'error_message': str(error),
            'user_data': context.user_data,
            'traceback': self.get_traceback(error)
        }
        
        # حفظ الخطأ في قاعدة البيانات أو ملف
        logger.error(f"Form error for diagnosis: {json.dumps(error_log, default=str)}")
        
    def get_traceback(self, error: Exception) -> str:
        """الحصول على تفاصيل الخطأ"""
        import traceback
        try:
            return ''.join(traceback.format_tb(error.__traceback__))
        except:
            return str(error)
            
    async def handle_timeout_error(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                 operation: str) -> int:
        """معالجة خطأ انتهاء المهلة"""
        timeout_message = self.get_error_message('timeout_error')
        timeout_message += f"\nالعملية: {operation}"
        
        await update.message.reply_text(timeout_message)
        
        # إعادة عرض الحقل الحالي
        return await self.redisplay_field(update, context, None)
        
    async def handle_validation_timeout(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                      field: Union[FormAttribute, FormDocument]) -> int:
        """معالجة انتهاء مهلة الفاليديشن"""
        timeout_message = "انتهت مهلة التحقق من صحة البيانات. يرجى المحاولة مرة أخرى."
        
        await update.message.reply_text(timeout_message)
        
        # إعادة عرض الحقل
        return await self.redisplay_field(update, context, field)
        
    async def show_error_summary(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                errors: List[Dict]) -> int:
        """عرض ملخص الأخطاء"""
        if not errors:
            return ConversationState.FILL_FORM
            
        message = "❌ تم العثور على الأخطاء التالية:\n\n"
        
        for i, error in enumerate(errors, 1):
            message += f"{i}. {error['field_name']}: {error['message']}\n"
            
        message += "\nيرجى تصحيح هذه الأخطاء قبل المتابعة."
        
        # لوحة المفاتيح
        keyboard = [
            ['✏️ تصحيح الأخطاء'],
            ['🔄 إعادة الفحص'],
            ['🏠 القائمة الرئيسية']
        ]
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
        
        await update.message.reply_text(message, reply_markup=reply_markup)
        return ConversationState.FILL_FORM
        
    async def validate_form_completeness(self, context: ContextTypes.DEFAULT_TYPE) -> Tuple[bool, List[Dict]]:
        """التحقق من اكتمال النموذج"""
        progress_tracker = context.user_data.get('form_progress')
        if not progress_tracker:
            return False, [{'field_name': 'النموذج', 'message': 'لم يتم العثور على النموذج'}]
            
        errors = []
        
        # فحص الحقول المطلوبة
        for field_id, field_state in progress_tracker.field_states.items():
            if not field_state.is_completed:
                field = progress_tracker.form.get_field_by_id(field_id)
                if field and getattr(field, 'required', False):
                    errors.append({
                        'field_name': getattr(field, 'name', field_id),
                        'message': 'حقل مطلوب',
                        'field_id': field_id
                    })
                    
        return len(errors) == 0, errors
        
    async def show_completion_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """عرض حالة اكتمال النموذج"""
        is_complete, errors = await self.validate_form_completeness(context)
        
        if is_complete:
            message = "✅ النموذج مكتمل وجاهز للإرسال!"
            keyboard = [['✅ تأكيد الإرسال'], ['🏠 القائمة الرئيسية']]
        else:
            message = f"⚠️ النموذج غير مكتمل. الأخطاء: {len(errors)}"
            keyboard = [['✏️ تصحيح الأخطاء'], ['🏠 القائمة الرئيسية']]
            
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
        
        await update.message.reply_text(message, reply_markup=reply_markup)
        
        if is_complete:
            return ConversationState.CONFIRM_SUBMISSION
        else:
            return ConversationState.FILL_FORM

class FormDataSanitizer:
    """منظف بيانات النموذج"""
    
    def __init__(self):
        self.sanitization_rules = {
            'text': self.sanitize_text,
            'number': self.sanitize_number,
            'email': self.sanitize_email,
            'phone': self.sanitize_phone,
            'date': self.sanitize_date,
            'time': self.sanitize_time
        }
        
    def sanitize_field_value(self, value: str, field_type: str) -> str:
        """تنظيف قيمة الحقل"""
        sanitizer = self.sanitization_rules.get(field_type, self.sanitize_text)
        return sanitizer(value)
        
    def sanitize_text(self, value: str) -> str:
        """تنظيف النص"""
        if not value:
            return ""
            
        # إزالة الأحرف الضارة
        value = value.strip()
        value = re.sub(r'[<>"\']', '', value)  # إزالة علامات HTML
        value = re.sub(r'\s+', ' ', value)     # توحيد المسافات
        
        return value
        
    def sanitize_number(self, value: str) -> str:
        """تنظيف الأرقام"""
        if not value:
            return ""
            
        # إزالة كل شيء ما عدا الأرقام والنقاط
        value = re.sub(r'[^\d.-]', '', value)
        
        return value
        
    def sanitize_email(self, value: str) -> str:
        """تنظيف البريد الإلكتروني"""
        if not value:
            return ""
            
        # تنظيف وإزالة المسافات
        value = value.strip().lower()
        value = re.sub(r'\s+', '', value)
        
        return value
        
    def sanitize_phone(self, value: str) -> str:
        """تنظيف رقم الهاتف"""
        if not value:
            return ""
            
        # إزالة كل شيء ما عدا الأرقام
        value = re.sub(r'[^\d+]', '', value)
        
        return value
        
    def sanitize_date(self, value: str) -> str:
        """تنظيف التاريخ"""
        if not value:
            return ""
            
        # تنظيف وإزالة المسافات الزائدة
        value = value.strip()
        value = re.sub(r'\s+', ' ', value)
        
        return value
        
    def sanitize_time(self, value: str) -> str:
        """تنظيف الوقت"""
        if not value:
            return ""
            
        # تنظيف وإزالة المسافات الزائدة
        value = value.strip()
        value = re.sub(r'\s+', ' ', value)
        
        return value
        
    def sanitize_form_data(self, form_data: Dict) -> Dict:
        """تنظيف جميع بيانات النموذج"""
        sanitized_data = {}
        
        for key, value in form_data.items():
            if isinstance(value, str):
                # تحديد نوع الحقل من المفتاح أو القيمة
                field_type = self.detect_field_type(key, value)
                sanitized_data[key] = self.sanitize_field_value(value, field_type)
            else:
                sanitized_data[key] = value
                
        return sanitized_data
        
    def detect_field_type(self, key: str, value: str) -> str:
        """تحديد نوع الحقل"""
        key_lower = key.lower()
        
        if any(word in key_lower for word in ['email', 'mail']):
            return 'email'
        elif any(word in key_lower for word in ['phone', 'mobile', 'tel']):
            return 'phone'
        elif any(word in key_lower for word in ['date', 'birth']):
            return 'date'
        elif any(word in key_lower for word in ['time']):
            return 'time'
        elif any(word in key_lower for word in ['number', 'amount', 'price', 'quantity']):
            return 'number'
        else:
            return 'text'