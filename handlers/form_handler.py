import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes
from config.conversation_states import ConversationState
from forms.form_model import FormAttribute, FormDocument, DynamicForm
from handlers.base_handler import BaseHandler
from utils.performance_monitor import monitor_async_performance
from typing import Union

logger = logging.getLogger(__name__)

class FormHandler(BaseHandler):
    """Handler for form filling operations"""
    
    def __init__(self, api_service=None):
        super().__init__()
        self.api_service = api_service
        
    @monitor_async_performance
    async def process(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> ConversationState:
        """Process form filling interactions"""
        text = update.message.text
        
        if text == "▶️ الرجوع":
            return await self._go_back(update, context)
        elif text == "⏩ العودةإلى القائمة الرئيسية":
            return ConversationState.MAIN_MENU
        elif text == "التالي":
            return await self._next_field(update, context)
        else:
            return await self._handle_field_input(update, context)
            
    async def _handle_field_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> ConversationState:
        """Handle form field input"""
        form = context.user_data.get('form')
        if not form:
            await update.message.reply_text(
                "حدث خطأ في تحميل النموذج. يرجى المحاولة مرة أخرى."
            )
            return ConversationState.MAIN_MENU
            
        current_field = form.get_current_field()
        if not current_field:
            await update.message.reply_text(
                "لا يوجد حقل حالي. يرجى المحاولة مرة أخرى."
            )
            return ConversationState.FILL_FORM
            
        # Validate and store field value
        try:
            if isinstance(current_field, FormAttribute):
                # Handle form attribute
                value = await self._validate_attribute_input(update, current_field)
                if value is not None:
                    form.set_attribute_value(current_field.id, value)
                    
            elif isinstance(current_field, FormDocument):
                # Handle form document
                await self._handle_document_input(update, current_field, form)
                
            # Move to next field
            return await self._move_to_next_field(update, context, form)
            
        except Exception as e:
            logger.error(f"Error handling field input: {e}")
            await update.message.reply_text(
                "حدث خطأ في معالجة المدخلات. يرجى المحاولة مرة أخرى."
            )
            return ConversationState.FILL_FORM
            
    async def _validate_attribute_input(self, update: Update, attribute: FormAttribute) -> Union[str, None]:
        """Validate attribute input"""
        text = update.message.text.strip()
        
        # Basic validation based on attribute type
        if attribute.type_code == 'text':
            if len(text) < attribute.min_length:
                await update.message.reply_text(
                    f"النص يجب أن يكون على الأقل {attribute.min_length} أحرف."
                )
                return None
            if len(text) > attribute.max_length:
                await update.message.reply_text(
                    f"النص يجب أن يكون أقل من {attribute.max_length} أحرف."
                )
                return None
                
        elif attribute.type_code == 'number':
            try:
                number = float(text)
                if hasattr(attribute, 'min_value') and number < attribute.min_value:
                    await update.message.reply_text(
                        f"الرقم يجب أن يكون أكبر من {attribute.min_value}."
                    )
                    return None
                if hasattr(attribute, 'max_value') and number > attribute.max_value:
                    await update.message.reply_text(
                        f"الرقم يجب أن يكون أقل من {attribute.max_value}."
                    )
                    return None
                return str(number)
            except ValueError:
                await update.message.reply_text("يرجى إدخال رقم صحيح.")
                return None
                
        elif attribute.type_code == 'email':
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, text):
                await update.message.reply_text("يرجى إدخال بريد إلكتروني صحيح.")
                return None
                
        return text
        
    async def _handle_document_input(self, update: Update, document: FormDocument, form: DynamicForm):
        """Handle document input"""
        if update.message.document:
            file = update.message.document
            try:
                # Download file data
                file_data = await update.get_file(file.file_id).download_as_bytearray()
                
                # Upload file to API
                if self.api_service:
                    upload_result = await self.api_service.upload_file(file_data, file.file_name)
                    
                    # Store file ID in form
                    current_document_files = form.get_document_files(document.id) or []
                    current_document_files.append(upload_result['file_id'])
                    form.set_document_files(document.id, current_document_files)
                    
                    await update.message.reply_text(
                        f"تم رفع الملف {file.file_name} بنجاح."
                    )
                else:
                    await update.message.reply_text(
                        f"تم استقبال الملف {file.file_name} بنجاح."
                    )
                
            except Exception as e:
                logger.error(f"Error uploading file: {e}")
                await update.message.reply_text(
                    "حدث خطأ في رفع الملف. يرجى المحاولة مرة أخرى."
                )
        else:
            await update.message.reply_text(
                "يرجى إرفاق ملف للاستمرار."
            )
            
    async def _move_to_next_field(self, update: Update, context: ContextTypes.DEFAULT_TYPE, form: DynamicForm) -> ConversationState:
        """Move to next field in form"""
        if form.has_more_fields():
            next_field = form.get_next_field()
            await self._show_field(update, context, next_field, form)
            return ConversationState.FILL_FORM
        else:
            # Form is complete, show summary
            return await self._show_form_summary(update, context, form)
            
    async def _show_field(self, update: Update, context: ContextTypes.DEFAULT_TYPE, field: Union[FormAttribute, FormDocument], form: DynamicForm):
        """Show form field to user"""
        if isinstance(field, FormAttribute):
            message = f"يرجى إدخال: {field.name}\n"
            if field.description:
                message += f"الوصف: {field.description}\n"
            if field.is_required:
                message += "هذا الحقل مطلوب"
                
            keyboard = [["▶️ الرجوع"]]
            if form.has_previous_field():
                keyboard[0].append("التالي")
                
        elif isinstance(field, FormDocument):
            message = f"يرجى رفع: {field.name}\n"
            if field.description:
                message += f"الوصف: {field.description}\n"
            if field.is_required:
                message += "هذا الحقل مطلوب"
                
            keyboard = [["▶️ الرجوع"]]
            if form.has_previous_field():
                keyboard[0].append("التالي")
                
        await update.message.reply_text(
            message,
            reply_markup=ReplyKeyboardMarkup(
                keyboard=keyboard,
                resize_keyboard=True,
                one_time_keyboard=True
            )
        )
        
    async def _show_form_summary(self, update: Update, context: ContextTypes.DEFAULT_TYPE, form: DynamicForm) -> ConversationState:
        """Show form summary for confirmation"""
        summary = "ملخص النموذج:\n\n"
        
        # Add attribute values
        for attribute in form.attributes:
            value = form.get_attribute_value(attribute.id)
            if value:
                summary += f"{attribute.name}: {value}\n"
                
        # Add document files
        for document in form.documents:
            files = form.get_document_files(document.id)
            if files:
                summary += f"{document.name}: {len(files)} ملف(ات)\n"
                
        keyboard = [["تأكيد الإرسال"], ["تعديل"]]
        
        await update.message.reply_text(
            summary,
            reply_markup=ReplyKeyboardMarkup(
                keyboard=keyboard,
                resize_keyboard=True,
                one_time_keyboard=True
            )
        )
        return ConversationState.CONFIRM_SUBMISSION
        
    async def _go_back(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> ConversationState:
        """Go back to previous field"""
        form = context.user_data.get('form')
        if not form:
            return ConversationState.MAIN_MENU
            
        if form.has_previous_field():
            previous_field = form.get_previous_field()
            await self._show_field(update, context, previous_field, form)
            return ConversationState.FILL_FORM
        else:
            # Go back to request selection
            return ConversationState.SELECT_REQUEST_TYPE
            
    async def _next_field(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> ConversationState:
        """Move to next field"""
        form = context.user_data.get('form')
        if not form:
            return ConversationState.MAIN_MENU
            
        if form.has_more_fields():
            next_field = form.get_next_field()
            await self._show_field(update, context, next_field, form)
            return ConversationState.FILL_FORM
        else:
            return await self._show_form_summary(update, context, form)
            
    async def submit_form(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> ConversationState:
        """Submit the completed form"""
        form = context.user_data.get('form')
        if not form:
            await update.message.reply_text("لا يوجد نموذج للإرسال.")
            return ConversationState.MAIN_MENU
            
        try:
            # Prepare form data for submission
            form_data = {
                'request_type_id': context.user_data.get('request_type_id'),
                'complaint_subject_id': context.user_data.get('complaint_subject_id'),
                'form_version_id': form.form_version_id,
                'data': form.get_attribute_values(),
                'documents': form.get_document_data()
            }
            
            # Submit to API
            result = await self.api_service.submit_complaint(form_data)
            
            await update.message.reply_text(
                f"تم إرسال النموذج بنجاح!\nرقم الطلب: {result.get('request_number', 'N/A')}",
                reply_markup=ReplyKeyboardMarkup(
                    keyboard=[["عودة للقائمة الرئيسية"]],
                    resize_keyboard=True,
                    one_time_keyboard=True
                )
            )
            
            # Clear form data
            context.user_data.pop('form', None)
            
            return ConversationState.MAIN_MENU
            
        except Exception as e:
            logger.error(f"Error submitting form: {e}")
            await update.message.reply_text(
                "حدث خطأ في إرسال النموذج. يرجى المحاولة مرة أخرى."
            )
            return ConversationState.FILL_FORM