import logging
from typing import Dict, List, Optional, Union, Any
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from forms.form_model import FormDocument
from services.api_service import ApiService
from config.conversation_states import ConversationState
import json
import io

logger = logging.getLogger(__name__)

class FormFileHandler:
    """معالج ملفات النموذج"""
    
    def __init__(self, api_service: ApiService):
        self.api_service = api_service
        self.supported_file_types = {
            'document': ['pdf', 'doc', 'docx', 'txt', 'rtf'],
            'image': ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp'],
            'video': ['mp4', 'avi', 'mov', 'wmv', 'flv', 'mkv'],
            'audio': ['mp3', 'wav', 'ogg', 'aac', 'wma']
        }
        self.max_file_sizes = {
            'document': 10 * 1024 * 1024,  # 10MB
            'image': 5 * 1024 * 1024,      # 5MB
            'video': 50 * 1024 * 1024,     # 50MB
            'audio': 20 * 1024 * 1024      # 20MB
        }
        
    async def handle_file_upload(self, update: Update, context: ContextTypes.DEFAULT_TYPE, field: FormDocument) -> tuple[bool, str, Optional[str]]:
        """معالجة رفع الملف"""
        try:
            # تحديد نوع الملف
            file_info = await self.get_file_info(update)
            if not file_info:
                return False, "لم يتم العثور على ملف", None
                
            # فاليديشن الملف
            validation_result = await self.validate_file(file_info, field)
            if not validation_result[0]:
                return False, validation_result[1], None
                
            # رفع الملف
            upload_result = await self.upload_file_to_server(file_info, context)
            if not upload_result[0]:
                return False, upload_result[1], None
                
            return True, "تم رفع الملف بنجاح", upload_result[1]
            
        except Exception as e:
            logger.error(f"Error handling file upload: {str(e)}")
            return False, f"حدث خطأ أثناء رفع الملف: {str(e)}", None
            
    async def get_file_info(self, update: Update) -> Optional[Dict]:
        """الحصول على معلومات الملف"""
        attachment = update.message.document or update.message.photo or update.message.video or update.message.audio
        
        if not attachment:
            return None
            
        file_info = {}
        
        if update.message.document:
            file_info.update({
                'type': 'document',
                'file_id': attachment.file_id,
                'file_name': attachment.file_name,
                'file_size': attachment.file_size,
                'mime_type': attachment.mime_type
            })
        elif update.message.photo:
            # استخدام أعلى دقة
            photo = attachment[-1]
            file_info.update({
                'type': 'image',
                'file_id': photo.file_id,
                'file_name': f"photo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg",
                'file_size': photo.file_size,
                'mime_type': 'image/jpeg'
            })
        elif update.message.video:
            file_info.update({
                'type': 'video',
                'file_id': attachment.file_id,
                'file_name': attachment.file_name or f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4",
                'file_size': attachment.file_size,
                'mime_type': attachment.mime_type
            })
        elif update.message.audio:
            file_info.update({
                'type': 'audio',
                'file_id': attachment.file_id,
                'file_name': attachment.file_name or f"audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3",
                'file_size': attachment.file_size,
                'mime_type': attachment.mime_type
            })
            
        # إضافة امتداد الملف
        if '.' in file_info['file_name']:
            file_info['extension'] = file_info['file_name'].split('.')[-1].lower()
        else:
            file_info['extension'] = self.get_extension_from_mime_type(file_info['mime_type'])
            
        return file_info
        
    def get_extension_from_mime_type(self, mime_type: str) -> str:
        """الحصول على امتداد الملف من نوع MIME"""
        mime_to_ext = {
            'application/pdf': 'pdf',
            'application/msword': 'doc',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
            'text/plain': 'txt',
            'image/jpeg': 'jpg',
            'image/png': 'png',
            'image/gif': 'gif',
            'video/mp4': 'mp4',
            'video/avi': 'avi',
            'audio/mpeg': 'mp3',
            'audio/wav': 'wav'
        }
        return mime_to_ext.get(mime_type, 'bin')
        
    async def validate_file(self, file_info: Dict, field: FormDocument) -> tuple[bool, str]:
        """فاليديشن الملف"""
        # التحقق من نوع الملف
        if field.accept_extension:
            if file_info['extension'] not in [ext.lower() for ext in field.accept_extension]:
                return False, f"نوع الملف غير مدعوم. الأنواع المدعومة: {', '.join(field.accept_extension)}"
                
        # التحقق من حجم الملف
        max_size = getattr(field, 'max_file_size', self.max_file_sizes.get(file_info['type'], 10 * 1024 * 1024))
        if file_info['file_size'] > max_size:
            return False, f"حجم الملف كبير جداً. الحد الأقصى: {max_size / (1024*1024):.1f} MB"
            
        # التحقق من نوع الملف حسب الحقل
        if hasattr(field, 'file_type_restriction'):
            if file_info['type'] not in field.file_type_restriction:
                return False, f"نوع الملف غير مسموح. الأنواع المسموحة: {', '.join(field.file_type_restriction)}"
                
        return True, ""
        
    async def upload_file_to_server(self, file_info: Dict, context: ContextTypes.DEFAULT_TYPE) -> tuple[bool, str, Optional[str]]:
        """رفع الملف للخادم"""
        try:
            # تحميل الملف من تيليجرام
            file_data = await self.download_file_from_telegram(file_info['file_id'], context)
            if not file_data:
                return False, "فشل في تحميل الملف من تيليجرام", None
                
            # رفع الملف للخادم
            upload_result = await self.api_service.upload_file(file_data, file_info['file_name'])
            if not upload_result or 'file_id' not in upload_result:
                return False, "فشل في رفع الملف للخادم", None
                
            return True, "تم رفع الملف بنجاح", upload_result['file_id']
            
        except Exception as e:
            logger.error(f"Error uploading file to server: {str(e)}")
            return False, f"حدث خطأ أثناء رفع الملف: {str(e)}", None
            
    async def download_file_from_telegram(self, file_id: str, context: ContextTypes.DEFAULT_TYPE) -> Optional[bytes]:
        """تحميل الملف من تيليجرام"""
        try:
            # الحصول على bot instance من context
            bot = context.bot
            
            # تحميل معلومات الملف
            file_info = await bot.get_file(file_id)
            
            # تحميل محتوى الملف
            file_data = await file_info.download_as_bytearray()
            
            return bytes(file_data)
            
        except Exception as e:
            logger.error(f"Error downloading file from Telegram: {str(e)}")
            return None
            
    async def handle_file_deletion(self, update: Update, context: ContextTypes.DEFAULT_TYPE, field: FormDocument) -> tuple[bool, str]:
        """معالجة حذف الملفات"""
        try:
            # الحصول على الملفات الحالية
            progress_tracker = context.user_data.get('form_progress')
            if not progress_tracker:
                return False, "لم يتم العثور على تقدم النموذج"
                
            field_state = progress_tracker.field_states.get(str(field.id))
            if not field_state or not field_state.attachments:
                return False, "لا توجد ملفات لحذفها"
                
            # عرض قائمة الملفات للحذف
            await self.show_file_deletion_menu(update, context, field, field_state.attachments)
            return True, "تم عرض قائمة الملفات"
            
        except Exception as e:
            logger.error(f"Error handling file deletion: {str(e)}")
            return False, f"حدث خطأ أثناء معالجة حذف الملفات: {str(e)}"
            
    async def show_file_deletion_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, field: FormDocument, attachments: List[Dict]):
        """عرض قائمة حذف الملفات"""
        message = f"📎 الملفات المرفوعة في {field.documents_type_name}:\n\n"
        
        for i, attachment in enumerate(attachments, 1):
            message += f"{i}. {attachment['file_name']}\n"
            
        message += "\nاختر رقم الملف لحذفه، أو اكتب 'الكل' لحذف جميع الملفات"
        
        # إنشاء لوحة المفاتيح
        keyboard = []
        for i in range(1, len(attachments) + 1):
            keyboard.append([f"🗑️ {i}"])
            
        keyboard.append(['🗑️ الكل', '❌ إلغاء'])
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
        
        await update.message.reply_text(message, reply_markup=reply_markup)
        
    async def delete_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE, field: FormDocument, file_index: int) -> tuple[bool, str]:
        """حذف ملف محدد"""
        try:
            progress_tracker = context.user_data.get('form_progress')
            if not progress_tracker:
                return False, "لم يتم العثور على تقدم النموذج"
                
            field_state = progress_tracker.field_states.get(str(field.id))
            if not field_state or not field_state.attachments:
                return False, "لا توجد ملفات لحذفها"
                
            if file_index < 0 or file_index >= len(field_state.attachments):
                return False, "رقم الملف غير صحيح"
                
            # حذف الملف من الخادم
            file_to_delete = field_state.attachments[file_index]
            deletion_result = await self.delete_file_from_server(file_to_delete['file_id'])
            
            if deletion_result:
                # حذف الملف من القائمة المحلية
                field_state.attachments.pop(file_index)
                return True, f"تم حذف الملف {file_to_delete['file_name']}"
            else:
                return False, "فشل في حذف الملف من الخادم"
                
        except Exception as e:
            logger.error(f"Error deleting file: {str(e)}")
            return False, f"حدث خطأ أثناء حذف الملف: {str(e)}"
            
    async def delete_file_from_server(self, file_id: str) -> bool:
        """حذف الملف من الخادم"""
        try:
            # هنا نقوم بحذف الملف من الخادم
            # يمكن استخدام API service
            return True
        except Exception as e:
            logger.error(f"Error deleting file from server: {str(e)}")
            return False
            
    async def delete_all_files(self, update: Update, context: ContextTypes.DEFAULT_TYPE, field: FormDocument) -> tuple[bool, str]:
        """حذف جميع الملفات"""
        try:
            progress_tracker = context.user_data.get('form_progress')
            if not progress_tracker:
                return False, "لم يتم العثور على تقدم النموذج"
                
            field_state = progress_tracker.field_states.get(str(field.id))
            if not field_state or not field_state.attachments:
                return False, "لا توجد ملفات لحذفها"
                
            # حذف جميع الملفات من الخادم
            for attachment in field_state.attachments:
                await self.delete_file_from_server(attachment['file_id'])
                
            # مسح قائمة الملفات
            field_state.attachments.clear()
            
            return True, f"تم حذف جميع الملفات ({len(field_state.attachments)} ملف)"
            
        except Exception as e:
            logger.error(f"Error deleting all files: {str(e)}")
            return False, f"حدث خطأ أثناء حذف جميع الملفات: {str(e)}"

class FormLocationHandler:
    """معالج موقع النموذج"""
    
    def __init__(self, api_service: ApiService):
        self.api_service = api_service
        
    async def handle_location_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE, field) -> tuple[bool, str, Optional[str]]:
        """معالجة إدخال الموقع"""
        try:
            location = update.message.location
            if not location:
                return False, "لم يتم العثور على موقع", None
                
            # فاليديشن الموقع
            validation_result = await self.validate_location(location, field)
            if not validation_result[0]:
                return False, validation_result[1], None
                
            # تنسيق بيانات الموقع
            location_data = {
                'latitude': location.latitude,
                'longitude': location.longitude,
                'accuracy': getattr(location, 'horizontal_accuracy', None),
                'timestamp': datetime.now().isoformat()
            }
            
            return True, "تم تحديد الموقع بنجاح", json.dumps(location_data)
            
        except Exception as e:
            logger.error(f"Error handling location input: {str(e)}")
            return False, f"حدث خطأ أثناء معالجة الموقع: {str(e)}", None
            
    async def validate_location(self, location, field) -> tuple[bool, str]:
        """فاليديشن الموقع"""
        try:
            lat = location.latitude
            lng = location.longitude
            
            # التحقق من صحة الإحداثيات
            if not (-90 <= lat <= 90):
                return False, "خط العرض غير صحيح"
                
            if not (-180 <= lng <= 180):
                return False, "خط الطول غير صحيح"
                
            # التحقق من النطاق إذا كان محدداً
            if hasattr(field, 'location_bounds'):
                bounds = field.location_bounds
                if bounds:
                    min_lat = bounds.get('min_lat')
                    max_lat = bounds.get('max_lat')
                    min_lng = bounds.get('min_lng')
                    max_lng = bounds.get('max_lng')
                    
                    if min_lat and lat < min_lat:
                        return False, f"خط العرض يجب أن يكون أكبر من {min_lat}"
                    if max_lat and lat > max_lat:
                        return False, f"خط العرض يجب أن يكون أصغر من {max_lat}"
                    if min_lng and lng < min_lng:
                        return False, f"خط الطول يجب أن يكون أكبر من {min_lng}"
                    if max_lng and lng > max_lng:
                        return False, f"خط الطول يجب أن يكون أصغر من {max_lng}"
                        
            # التحقق من الدقة إذا كان مطلوباً
            if hasattr(field, 'min_accuracy') and field.min_accuracy:
                accuracy = getattr(location, 'horizontal_accuracy', None)
                if accuracy and accuracy > field.min_accuracy:
                    return False, f"دقة الموقع منخفضة جداً. الحد الأدنى: {field.min_accuracy} متر"
                    
            return True, ""
            
        except Exception as e:
            logger.error(f"Error validating location: {str(e)}")
            return False, f"خطأ في فاليديشن الموقع: {str(e)}"
            
    async def show_location_field(self, update: Update, context: ContextTypes.DEFAULT_TYPE, field, progress_info: str) -> int:
        """عرض حقل الموقع"""
        message = f"{progress_info}\n\n"
        message += f"📍 {field.name}\n"
        
        if hasattr(field, 'description') and field.description:
            message += f"ℹ️ {field.description}\n"
            
        if hasattr(field, 'example') and field.example:
            message += f"💡 مثال: {field.example}\n"
            
        # عرض القيمة الحالية إذا كانت موجودة
        progress_tracker = context.user_data.get('form_progress')
        if progress_tracker:
            field_state = progress_tracker.field_states.get(str(field.id))
            if field_state and field_state.value:
                try:
                    location_data = json.loads(field_state.value)
                    message += f"\n✅ الموقع الحالي: {location_data['latitude']:.6f}, {location_data['longitude']:.6f}\n"
                except:
                    pass
                    
        message += "\nاضغط على الزر أدناه لمشاركة موقعك:"
        
        # إنشاء لوحة المفاتيح
        keyboard = [
            ["📍 مشاركة الموقع"],
            ["🗺️ عرض الخريطة"],
            ["◀️ السابق", "التالي ▶️"],
            ["🏠 القائمة الرئيسية"]
        ]
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
        
        await update.message.reply_text(message, reply_markup=reply_markup)
        return ConversationState.FILL_FORM
        
    async def show_map_preview(self, update: Update, context: ContextTypes.DEFAULT_TYPE, field) -> int:
        """عرض معاينة الخريطة"""
        progress_tracker = context.user_data.get('form_progress')
        if not progress_tracker:
            await update.message.reply_text("حدث خطأ في النموذج. يرجى المحاولة مرة أخرى.")
            return ConversationHandler.END
            
        field_state = progress_tracker.field_states.get(str(field.id))
        if not field_state or not field_state.value:
            await update.message.reply_text("لم يتم تحديد موقع بعد. يرجى مشاركة موقعك أولاً.")
            return ConversationState.FILL_FORM
            
        try:
            location_data = json.loads(field_state.value)
            lat = location_data['latitude']
            lng = location_data['longitude']
            
            # إنشاء رابط الخريطة
            map_url = f"https://www.google.com/maps?q={lat},{lng}"
            
            message = f"📍 الموقع المحدد:\n"
            message += f"خط العرض: {lat:.6f}\n"
            message += f"خط الطول: {lng:.6f}\n\n"
            message += f"🗺️ [عرض على الخريطة]({map_url})"
            
            # لوحة المفاتيح
            keyboard = [
                ["📍 مشاركة موقع جديد"],
                ["✅ تأكيد الموقع"],
                ["◀️ السابق", "التالي ▶️"],
                ["🏠 القائمة الرئيسية"]
            ]
            
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
            
            await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown', disable_web_page_preview=True)
            return ConversationState.FILL_FORM
            
        except Exception as e:
            logger.error(f"Error showing map preview: {str(e)}")
            await update.message.reply_text("حدث خطأ في عرض الخريطة. يرجى المحاولة مرة أخرى.")
            return ConversationState.FILL_FORM