import logging
from typing import Dict, List, Optional, Union, Any
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from forms.form_model import FormAttribute, FormDocument, DynamicForm
from services.api_service import ApiService
from config.conversation_states import ConversationState
from config.settings import settings
import json
import re

logger = logging.getLogger(__name__)

class FormFieldState:
    """حالة حقل النموذج مع البيانات المدخلة"""
    
    def __init__(self, field_id: str, field_name: str, field_type: str):
        self.field_id = field_id
        self.field_name = field_name
        self.field_type = field_type
        self.value = None
        self.is_completed = False
        self.completed_at = None
        self.validation_errors = []
        self.attachments = []
        
    def set_value(self, value: Any):
        self.value = value
        self.is_completed = True
        self.completed_at = datetime.now()
        self.validation_errors = []
        
    def add_attachment(self, file_id: str, file_name: str):
        self.attachments.append({
            'file_id': file_id,
            'file_name': file_name,
            'uploaded_at': datetime.now()
        })
        
    def mark_incomplete(self):
        self.is_completed = False
        self.completed_at = None

class FormProgressTracker:
    """تتبع تقدم ملء النموذج"""
    
    def __init__(self, form: DynamicForm):
        self.form = form
        self.field_states: Dict[str, FormFieldState] = {}
        self.current_field_index = 0
        self.start_time = datetime.now()
        self.last_activity = datetime.now()
        self.auto_save_interval = 300  # 5 دقائق
        
    def initialize_fields(self):
        """تهيئة جميع الحقول"""
        for group in self.form.groups:
            for attr in group.attributes:
                field_state = FormFieldState(
                    str(attr.id),
                    attr.name,
                    attr.type_code
                )
                self.field_states[str(attr.id)] = field_state
                
        for doc in self.form.documents:
            field_state = FormFieldState(
                str(doc.id),
                doc.documents_type_name,
                'document'
            )
            self.field_states[str(doc.id)] = field_state
            
    def get_current_field(self) -> Optional[Union[FormAttribute, FormDocument]]:
        """الحصول على الحقل الحالي"""
        all_fields = self.get_all_fields()
        if 0 <= self.current_field_index < len(all_fields):
            return all_fields[self.current_field_index]
        return None
        
    def get_all_fields(self) -> List[Union[FormAttribute, FormDocument]]:
        """الحصول على جميع الحقول مرتبة"""
        fields = []
        for group in self.form.groups:
            for attr in group.attributes:
                fields.append(attr)
        for doc in self.form.documents:
            fields.append(doc)
        return fields
        
    def get_progress_percentage(self) -> float:
        """حساب نسبة التقدم"""
        total_fields = len(self.field_states)
        completed_fields = sum(1 for state in self.field_states.values() if state.is_completed)
        return (completed_fields / total_fields) * 100 if total_fields > 0 else 0
        
    def get_remaining_fields_count(self) -> int:
        """عدد الحقول المتبقية"""
        total_fields = len(self.field_states)
        completed_fields = sum(1 for state in self.field_states.values() if state.is_completed)
        return total_fields - completed_fields
        
    def get_estimated_time_remaining(self) -> str:
        """تقدير الوقت المتبقي"""
        if self.get_progress_percentage() == 0:
            return "غير محدد"
            
        elapsed_time = datetime.now() - self.start_time
        progress_percentage = self.get_progress_percentage() / 100
        
        if progress_percentage > 0:
            estimated_total_time = elapsed_time / progress_percentage
            remaining_time = estimated_total_time - elapsed_time
            
            if remaining_time.total_seconds() < 60:
                return f"{int(remaining_time.total_seconds())} ثانية"
            elif remaining_time.total_seconds() < 3600:
                return f"{int(remaining_time.total_seconds() / 60)} دقيقة"
            else:
                return f"{int(remaining_time.total_seconds() / 3600)} ساعة"
        
        return "غير محدد"
        
    def can_go_back(self) -> bool:
        """إمكانية الرجوع"""
        return self.current_field_index > 0
        
    def can_go_forward(self) -> bool:
        """إمكانية التقدم"""
        all_fields = self.get_all_fields()
        return self.current_field_index < len(all_fields) - 1
        
    def go_to_field(self, field_id: str) -> bool:
        """الانتقال لحقل محدد"""
        all_fields = self.get_all_fields()
        for i, field in enumerate(all_fields):
            if str(field.id) == field_id:
                self.current_field_index = i
                return True
        return False
        
    def go_to_previous_field(self) -> bool:
        """الانتقال للحقل السابق"""
        if self.can_go_back():
            self.current_field_index -= 1
            return True
        return False
        
    def go_to_next_field(self) -> bool:
        """الانتقال للحقل التالي"""
        if self.can_go_forward():
            self.current_field_index += 1
            return True
        return False
        
    def update_last_activity(self):
        """تحديث آخر نشاط"""
        self.last_activity = datetime.now()
        
    def should_auto_save(self) -> bool:
        """هل يجب الحفظ التلقائي"""
        return (datetime.now() - self.last_activity).total_seconds() >= self.auto_save_interval

class FormValidator:
    """محسن الفاليديشن للحقول"""
    
    @staticmethod
    def validate_text_field(value: str, field: FormAttribute) -> tuple[bool, str]:
        """فاليديشن الحقول النصية"""
        if not value or not value.strip():
            if field.required:
                return False, f"حقل {field.name} مطلوب"
            return True, ""
            
        value = value.strip()
        
        # التحقق من الطول
        if hasattr(field, 'min_length') and field.min_length and len(value) < field.min_length:
            return False, f"يجب أن يكون {field.name} على الأقل {field.min_length} أحرف"
            
        if hasattr(field, 'max_length') and field.max_length and len(value) > field.max_length:
            return False, f"يجب أن يكون {field.name} على الأكثر {field.max_length} أحرف"
            
        # التحقق من النمط
        if hasattr(field, 'pattern') and field.pattern:
            if not re.match(field.pattern, value):
                return False, f"تنسيق {field.name} غير صحيح"
                
        return True, ""
        
    @staticmethod
    def validate_number_field(value: str, field: FormAttribute) -> tuple[bool, str]:
        """فاليديشن الحقول الرقمية"""
        if not value or not value.strip():
            if field.required:
                return False, f"حقل {field.name} مطلوب"
            return True, ""
            
        try:
            num_value = float(value)
        except ValueError:
            return False, f"يجب أن يكون {field.name} رقماً"
            
        # التحقق من النطاق
        if hasattr(field, 'min_value') and field.min_value is not None and num_value < field.min_value:
            return False, f"يجب أن يكون {field.name} على الأقل {field.min_value}"
            
        if hasattr(field, 'max_value') and field.max_value is not None and num_value > field.max_value:
            return False, f"يجب أن يكون {field.name} على الأكثر {field.max_value}"
            
        return True, ""
        
    @staticmethod
    def validate_date_field(value: str, field: FormAttribute) -> tuple[bool, str]:
        """فاليديشن حقول التاريخ"""
        if not value or not value.strip():
            if field.required:
                return False, f"حقل {field.name} مطلوب"
            return True, ""
            
        try:
            # محاولة تحليل التاريخ
            if 'T' in value:  # ISO format
                date_obj = datetime.fromisoformat(value.replace('Z', '+00:00'))
            else:
                # محاولة تنسيقات مختلفة
                for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y']:
                    try:
                        date_obj = datetime.strptime(value, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    return False, f"تنسيق التاريخ غير صحيح. استخدم YYYY-MM-DD"
                    
            # التحقق من النطاق
            if hasattr(field, 'min_date') and field.min_date:
                min_date = datetime.strptime(field.min_date, '%Y-%m-%d')
                if date_obj < min_date:
                    return False, f"التاريخ يجب أن يكون بعد {field.min_date}"
                    
            if hasattr(field, 'max_date') and field.max_date:
                max_date = datetime.strptime(field.max_date, '%Y-%m-%d')
                if date_obj > max_date:
                    return False, f"التاريخ يجب أن يكون قبل {field.max_date}"
                    
            return True, ""
            
        except Exception as e:
            return False, f"خطأ في تنسيق التاريخ: {str(e)}"
            
    @staticmethod
    def validate_time_field(value: str, field: FormAttribute) -> tuple[bool, str]:
        """فاليديشن حقول الوقت"""
        if not value or not value.strip():
            if field.required:
                return False, f"حقل {field.name} مطلوب"
            return True, ""
            
        try:
            # محاولة تحليل الوقت
            if 'AM' in value.upper() or 'PM' in value.upper():
                time_obj = datetime.strptime(value, "%I:%M %p").time()
            else:
                time_obj = datetime.strptime(value, "%H:%M").time()
                
            # التحقق من النطاق
            if hasattr(field, 'min_time') and field.min_time:
                min_time = datetime.strptime(field.min_time, '%H:%M:%S').time()
                if time_obj < min_time:
                    return False, f"الوقت يجب أن يكون بعد {field.min_time}"
                    
            if hasattr(field, 'max_time') and field.max_time:
                max_time = datetime.strptime(field.max_time, '%H:%M:%S').time()
                if time_obj > max_time:
                    return False, f"الوقت يجب أن يكون قبل {field.max_time}"
                    
            return True, ""
            
        except Exception as e:
            return False, f"خطأ في تنسيق الوقت. استخدم HH:MM أو HH:MM AM/PM"
            
    @staticmethod
    def validate_email_field(value: str, field: FormAttribute) -> tuple[bool, str]:
        """فاليديشن حقول البريد الإلكتروني"""
        if not value or not value.strip():
            if field.required:
                return False, f"حقل {field.name} مطلوب"
            return True, ""
            
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, value):
            return False, f"تنسيق البريد الإلكتروني غير صحيح"
            
        return True, ""
        
    @staticmethod
    def validate_phone_field(value: str, field: FormAttribute) -> tuple[bool, str]:
        """فاليديشن حقول الهاتف"""
        if not value or not value.strip():
            if field.required:
                return False, f"حقل {field.name} مطلوب"
            return True, ""
            
        # تنظيف الرقم
        cleaned = ''.join(filter(str.isdigit, value))
        
        # التحقق من الطول
        if len(cleaned) < 10 or len(cleaned) > 15:
            return False, f"رقم الهاتف يجب أن يكون بين 10 و 15 رقم"
            
        return True, ""
        
    @staticmethod
    def validate_file_field(file_data: dict, field: FormDocument) -> tuple[bool, str]:
        """فاليديشن حقول الملفات"""
        if not file_data:
            if field.required:
                return False, f"حقل {field.documents_type_name} مطلوب"
            return True, ""
            
        # التحقق من نوع الملف
        file_extension = file_data.get('file_extension', '').lower()
        if field.accept_extension and file_extension not in [ext.lower() for ext in field.accept_extension]:
            return False, f"نوع الملف غير مدعوم. الأنواع المدعومة: {', '.join(field.accept_extension)}"
            
        # التحقق من حجم الملف
        file_size = file_data.get('file_size', 0)
        max_size = getattr(field, 'max_file_size', 10 * 1024 * 1024)  # 10MB افتراضياً
        if file_size > max_size:
            return False, f"حجم الملف كبير جداً. الحد الأقصى: {max_size / (1024*1024):.1f} MB"
            
        return True, ""

class ImprovedFormHandler:
    """معالج محسن لملء النموذج"""
    
    def __init__(self, api_service: ApiService):
        self.api_service = api_service
        self.validator = FormValidator()
        
    async def start_form_filling(self, update: Update, context: ContextTypes.DEFAULT_TYPE, form: DynamicForm) -> int:
        """بدء عملية ملء النموذج"""
        # إنشاء متتبع التقدم
        progress_tracker = FormProgressTracker(form)
        progress_tracker.initialize_fields()
        
        # حفظ في context
        context.user_data['form_progress'] = progress_tracker
        context.user_data['form'] = form
        
        # عرض الحقل الأول
        return await self.show_current_field(update, context)
        
    async def show_current_field(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """عرض الحقل الحالي"""
        progress_tracker: FormProgressTracker = context.user_data.get('form_progress')
        if not progress_tracker:
            await update.message.reply_text("حدث خطأ في النموذج. يرجى المحاولة مرة أخرى.")
            return ConversationHandler.END
            
        current_field = progress_tracker.get_current_field()
        if not current_field:
            # انتهى النموذج
            return await self.show_form_summary(update, context)
            
        # عرض معلومات التقدم
        progress_info = await self.get_progress_info(progress_tracker)
        
        # عرض الحقل
        if isinstance(current_field, FormDocument):
            return await self.show_document_field(update, context, current_field, progress_info)
        else:
            return await self.show_attribute_field(update, context, current_field, progress_info)
            
    async def get_progress_info(self, progress_tracker: FormProgressTracker) -> str:
        """الحصول على معلومات التقدم"""
        progress_percentage = progress_tracker.get_progress_percentage()
        remaining_count = progress_tracker.get_remaining_fields_count()
        estimated_time = progress_tracker.get_estimated_time_remaining()
        
        info = f"📊 التقدم: {progress_percentage:.1f}%\n"
        info += f"📝 الحقول المتبقية: {remaining_count}\n"
        if estimated_time != "غير محدد":
            info += f"⏱️ الوقت المتوقع: {estimated_time}\n"
            
        return info
        
    async def show_document_field(self, update: Update, context: ContextTypes.DEFAULT_TYPE, field: FormDocument, progress_info: str) -> int:
        """عرض حقل الملفات"""
        progress_tracker: FormProgressTracker = context.user_data.get('form_progress')
        
        message = f"{progress_info}\n\n"
        message += f"📎 {field.documents_type_name}\n"
        message += f"الملفات المسموحة: {', '.join(field.accept_extension)}\n"
        
        # عرض الملفات المرفوعة
        current_files = progress_tracker.field_states[str(field.id)].attachments
        if current_files:
            message += f"\n✅ تم رفع {len(current_files)} ملف:\n"
            for i, file in enumerate(current_files, 1):
                message += f"{i}. {file['file_name']}\n"
                
        if field.is_multi:
            message += f"\n💡 يمكنك رفع ملفات متعددة"
            
        # إنشاء لوحة المفاتيح
        keyboard = []
        
        # أزرار التنقل
        nav_buttons = []
        if progress_tracker.can_go_back():
            nav_buttons.append("◀️ السابق")
        if progress_tracker.can_go_forward():
            nav_buttons.append("التالي ▶️")
        if nav_buttons:
            keyboard.append(nav_buttons)
            
        # أزرار إضافية
        if current_files:
            keyboard.append(['🗑️ حذف الملفات', '✅ تم'])
        if not field.required:
            keyboard.append(['⏭️ تخطي'])
            
        keyboard.append(['🏠 القائمة الرئيسية'])
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
        
        await update.message.reply_text(message, reply_markup=reply_markup)
        return ConversationState.FILL_FORM
        
    async def show_attribute_field(self, update: Update, context: ContextTypes.DEFAULT_TYPE, field: FormAttribute, progress_info: str) -> int:
        """عرض حقل السمة"""
        progress_tracker: FormProgressTracker = context.user_data.get('form_progress')
        
        message = f"{progress_info}\n\n"
        message += f"📝 {field.name}\n"
        
        if field.example:
            message += f"💡 مثال: {field.example}\n"
            
        if hasattr(field, 'description') and field.description:
            message += f"ℹ️ {field.description}\n"
            
        # عرض القيمة الحالية إذا كانت موجودة
        current_value = progress_tracker.field_states[str(field.id)].value
        if current_value:
            message += f"\n✅ القيمة الحالية: {current_value}\n"
            
        # إنشاء لوحة المفاتيح حسب نوع الحقل
        keyboard = await self.create_field_keyboard(field, progress_tracker)
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
        
        await update.message.reply_text(message, reply_markup=reply_markup)
        return ConversationState.FILL_FORM
        
    async def create_field_keyboard(self, field: FormAttribute, progress_tracker: FormProgressTracker) -> List[List[str]]:
        """إنشاء لوحة المفاتيح للحقل"""
        keyboard = []
        
        # لوحة المفاتيح حسب نوع الحقل
        if field.type_code == "switch":
            keyboard.append(["✅ نعم", "❌ لا"])
        elif field.type_code in ["options", "autocomplete"]:
            options = await field.get_autocomplete_options(self.api_service) if field.type_code == "autocomplete" else field.options
            option_names = [option['name'] for option in options]
            # تقسيم الخيارات إلى صفوف
            for i in range(0, len(option_names), 2):
                row = option_names[i:i+2]
                keyboard.append(row)
        elif field.type_code in ["multi_options", "multiple_autocomplete"]:
            options = await field.get_autocomplete_options(self.api_service) if field.type_code == "multiple_autocomplete" else field.options
            option_names = [option['name'] for option in options]
            # تقسيم الخيارات إلى صفوف
            for i in range(0, len(option_names), 2):
                row = option_names[i:i+2]
                keyboard.append(row)
            keyboard.append(['✅ تم'])
        elif field.type_code == "map":
            keyboard.append(["📍 مشاركة الموقع"])
        elif field.type_code == "time":
            keyboard.append(["⏰ إدخال الوقت"])
            
        # أزرار التنقل
        nav_buttons = []
        if progress_tracker.can_go_back():
            nav_buttons.append("◀️ السابق")
        if progress_tracker.can_go_forward():
            nav_buttons.append("التالي ▶️")
        if nav_buttons:
            keyboard.append(nav_buttons)
            
        # أزرار إضافية
        if not field.required:
            keyboard.append(['⏭️ تخطي'])
            
        keyboard.append(['🏠 القائمة الرئيسية'])
        
        return keyboard
        
    async def handle_field_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """معالجة إدخال الحقل"""
        progress_tracker: FormProgressTracker = context.user_data.get('form_progress')
        if not progress_tracker:
            await update.message.reply_text("حدث خطأ في النموذج. يرجى المحاولة مرة أخرى.")
            return ConversationHandler.END
            
        current_field = progress_tracker.get_current_field()
        if not current_field:
            return await self.show_form_summary(update, context)
            
        user_input = update.message.text
        user_id = update.effective_user.id
        
        # معالجة الأوامر الخاصة
        if user_input == "🏠 القائمة الرئيسية":
            return await self.go_to_main_menu(update, context)
        elif user_input == "◀️ السابق":
            return await self.go_to_previous_field(update, context)
        elif user_input == "التالي ▶️":
            return await self.go_to_next_field(update, context)
        elif user_input == "⏭️ تخطي":
            return await self.skip_current_field(update, context)
        elif user_input == "✅ تم":
            return await self.finish_multi_selection(update, context)
            
        # معالجة الإدخال حسب نوع الحقل
        if isinstance(current_field, FormDocument):
            return await self.handle_document_input(update, context, user_input)
        else:
            return await self.handle_attribute_input(update, context, user_input)
            
    async def handle_attribute_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_input: str) -> int:
        """معالجة إدخال السمة"""
        progress_tracker: FormProgressTracker = context.user_data.get('form_progress')
        current_field = progress_tracker.get_current_field()
        
        # فاليديشن المدخل
        validation_result = await self.validate_field_input(user_input, current_field)
        if not validation_result[0]:
            await update.message.reply_text(f"❌ {validation_result[1]}")
            return ConversationState.FILL_FORM
            
        # حفظ القيمة
        field_state = progress_tracker.field_states[str(current_field.id)]
        field_state.set_value(validation_result[1])
        
        # الانتقال للحقل التالي
        return await self.go_to_next_field(update, context)
        
    async def validate_field_input(self, user_input: str, field: FormAttribute) -> tuple[bool, str]:
        """فاليديشن إدخال الحقل"""
        # تنظيف المدخل
        if user_input:
            user_input = user_input.strip()
            
        # فاليديشن حسب نوع الحقل
        if field.type_code == "text":
            return self.validator.validate_text_field(user_input, field)
        elif field.type_code == "number":
            return self.validator.validate_number_field(user_input, field)
        elif field.type_code == "date":
            return self.validator.validate_date_field(user_input, field)
        elif field.type_code == "time":
            return self.validator.validate_time_field(user_input, field)
        elif field.type_code == "email":
            return self.validator.validate_email_field(user_input, field)
        elif field.type_code == "phone":
            return self.validator.validate_phone_field(user_input, field)
        elif field.type_code == "switch":
            if user_input in ["✅ نعم", "❌ لا"]:
                return True, "true" if user_input == "✅ نعم" else "false"
            return False, "يرجى اختيار نعم أو لا"
        elif field.type_code in ["options", "autocomplete"]:
            # التحقق من أن الخيار موجود
            options = await field.get_autocomplete_options(self.api_service) if field.type_code == "autocomplete" else field.options
            selected_option = next((opt for opt in options if opt['name'] == user_input), None)
            if selected_option:
                return True, str(selected_option['id'])
            return False, "يرجى اختيار خيار من القائمة"
            
        return True, user_input
        
    async def go_to_previous_field(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """الانتقال للحقل السابق"""
        progress_tracker: FormProgressTracker = context.user_data.get('form_progress')
        if not progress_tracker:
            await update.message.reply_text("حدث خطأ في النموذج. يرجى المحاولة مرة أخرى.")
            return ConversationHandler.END
            
        if progress_tracker.go_to_previous_field():
            return await self.show_current_field(update, context)
        else:
            await update.message.reply_text("لا يمكن الرجوع أكثر من ذلك.")
            return ConversationState.FILL_FORM
            
    async def go_to_next_field(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """الانتقال للحقل التالي"""
        progress_tracker: FormProgressTracker = context.user_data.get('form_progress')
        if not progress_tracker:
            await update.message.reply_text("حدث خطأ في النموذج. يرجى المحاولة مرة أخرى.")
            return ConversationHandler.END
            
        if progress_tracker.go_to_next_field():
            return await self.show_current_field(update, context)
        else:
            # انتهى النموذج
            return await self.show_form_summary(update, context)
            
    async def skip_current_field(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """تخطي الحقل الحالي"""
        progress_tracker: FormProgressTracker = context.user_data.get('form_progress')
        current_field = progress_tracker.get_current_field()
        
        if not current_field.required:
            # تخطي الحقل
            field_state = progress_tracker.field_states[str(current_field.id)]
            field_state.mark_incomplete()
            
            await update.message.reply_text(f"تم تخطي حقل {current_field.name}")
            return await self.go_to_next_field(update, context)
        else:
            await update.message.reply_text("لا يمكن تخطي هذا الحقل لأنه مطلوب.")
            return ConversationState.FILL_FORM
            
    async def go_to_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """العودة للقائمة الرئيسية"""
        # حفظ التقدم
        await self.save_form_progress(context)
        
        # تنظيف البيانات
        context.user_data.pop('form_progress', None)
        context.user_data.pop('form', None)
        
        await update.message.reply_text("تم حفظ تقدمك. يمكنك العودة لاحقاً لإكمال النموذج.")
        return ConversationState.MAIN_MENU
        
    async def save_form_progress(self, context: ContextTypes.DEFAULT_TYPE):
        """حفظ تقدم النموذج"""
        progress_tracker: FormProgressTracker = context.user_data.get('form_progress')
        if not progress_tracker:
            return
            
        # حفظ البيانات في قاعدة البيانات أو ملف مؤقت
        progress_data = {
            'user_id': context.user_data.get('user_id'),
            'form_id': progress_tracker.form.id,
            'field_states': {k: {
                'value': v.value,
                'is_completed': v.is_completed,
                'completed_at': v.completed_at.isoformat() if v.completed_at else None,
                'attachments': v.attachments
            } for k, v in progress_tracker.field_states.items()},
            'current_field_index': progress_tracker.current_field_index,
            'start_time': progress_tracker.start_time.isoformat(),
            'last_activity': progress_tracker.last_activity.isoformat()
        }
        
        # هنا يمكن حفظ البيانات في قاعدة البيانات
        context.user_data['saved_form_progress'] = progress_data
        
    async def show_form_summary(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """عرض ملخص النموذج"""
        progress_tracker: FormProgressTracker = context.user_data.get('form_progress')
        if not progress_tracker:
            await update.message.reply_text("حدث خطأ في النموذج. يرجى المحاولة مرة أخرى.")
            return ConversationHandler.END
            
        message = "🎉 تم إكمال النموذج!\n\n"
        message += "📋 ملخص البيانات:\n\n"
        
        # عرض البيانات حسب المجموعات
        for group in progress_tracker.form.groups:
            message += f"**{group.name}**\n"
            for attr in group.attributes:
                field_state = progress_tracker.field_states.get(str(attr.id))
                if field_state and field_state.is_completed:
                    value = field_state.value
                    if attr.type_code == 'switch':
                        value = 'نعم' if value == 'true' else 'لا'
                    message += f"✅ {attr.name}: {value}\n"
                else:
                    message += f"❌ {attr.name}: غير مكتمل\n"
            message += "\n"
            
        # عرض المرفقات
        message += "📎 المرفقات:\n"
        for doc in progress_tracker.form.documents:
            field_state = progress_tracker.field_states.get(str(doc.id))
            if field_state and field_state.attachments:
                message += f"✅ {doc.documents_type_name}: {len(field_state.attachments)} ملف\n"
            else:
                message += f"❌ {doc.documents_type_name}: لا توجد مرفقات\n"
                
        # إحصائيات
        progress_percentage = progress_tracker.get_progress_percentage()
        total_time = datetime.now() - progress_tracker.start_time
        
        message += f"\n📊 الإحصائيات:\n"
        message += f"نسبة الإنجاز: {progress_percentage:.1f}%\n"
        message += f"الوقت المستغرق: {total_time.total_seconds() / 60:.1f} دقيقة\n"
        
        # لوحة المفاتيح
        keyboard = [
            ['✅ تأكيد الإرسال'],
            ['✏️ تعديل البيانات'],
            ['🏠 القائمة الرئيسية']
        ]
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
        
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
        return ConversationState.CONFIRM_SUBMISSION