"""
ملف يوضح كيفية تكامل المعالجات المحسنة مع bot.py
"""

# ============================================================================
# 1. الاستيرادات المطلوبة في بداية bot.py
# ============================================================================

# إضافة هذه الاستيرادات في بداية bot.py
from form_handler_improved import ImprovedFormHandler
from form_file_handler import FormFileHandler, FormLocationHandler
from form_error_handler import FormErrorHandler, FormDataSanitizer

# ============================================================================
# 2. المتغيرات العامة
# ============================================================================

# إضافة هذه المتغيرات بعد الاستيرادات
form_handler = None
file_handler = None
location_handler = None
error_handler = None
sanitizer = None

# ============================================================================
# 3. تحديث دالة initialize_bot
# ============================================================================

async def initialize_bot():
    global api_service, form_handler, file_handler, location_handler, error_handler, sanitizer
    
    # الكود الأصلي
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
    sanitizer = FormDataSanitizer()
    
    # ربط المعالجات معاً
    form_handler.set_handlers(file_handler, location_handler, error_handler)
    
    logger.info("Enhanced form handlers initialized successfully")

# ============================================================================
# 4. استبدال دالة fill_form
# ============================================================================

# استبدل الدالة القديمة
async def fill_form(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة محسنة لملء النموذج"""
    try:
        # استخدام المعالج المحسن
        return await form_handler.handle_field_input(update, context)
    except Exception as e:
        logger.error(f"Error in improved form handler: {str(e)}")
        # استخدام معالج الأخطاء المحسن
        return await error_handler.handle_validation_error(
            update, context, None, f"حدث خطأ: {str(e)}"
        )

# ============================================================================
# 5. إنشاء دوال محسنة للملفات والموقع
# ============================================================================

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

# ============================================================================
# 6. تحديث دالة select_subject
# ============================================================================

async def select_subject(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # ... الكود الأصلي ...
    
    # عند اختيار الموضوع، بدء النموذج المحسن
    try:
        # جلب النموذج
        response = await api_service.get_form(
            request_type_id=context.user_data['request_type']['id'],
            complaint_subject_id=selected_subject['id']
        )
        
        form = DynamicForm.from_dict(response)
        
        # بدء النموذج المحسن
        return await form_handler.start_form_filling(update, context, form)
        
    except Exception as e:
        logger.error(f"Error starting form: {str(e)}")
        return await error_handler.handle_validation_error(
            update, context, None, f"خطأ في بدء النموذج: {str(e)}"
        )

# ============================================================================
# 7. تحديث ConversationHandler
# ============================================================================

async def main():
    # ... الكود الأصلي ...
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            # ... الحالات الأخرى ...
            ConversationState.FILL_FORM: [
                MessageHandler(filters.LOCATION, handle_location_improved),
                MessageHandler(filters.TEXT & ~filters.COMMAND, fill_form),
                MessageHandler(filters.ATTACHMENT, handle_attachment_improved),
            ],
            # ... باقي الحالات ...
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    # ... باقي الكود ...

# ============================================================================
# 8. تحديث دوال أخرى
# ============================================================================

async def show_form_field(update: Update, context: ContextTypes.DEFAULT_TYPE, field) -> int:
    """عرض الحقل باستخدام المعالج المحسن"""
    try:
        return await form_handler.show_current_field(update, context)
    except Exception as e:
        logger.error(f"Error showing form field: {str(e)}")
        return await error_handler.handle_validation_error(
            update, context, field, f"خطأ في عرض الحقل: {str(e)}"
        )

async def show_form_summary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """عرض ملخص النموذج باستخدام المعالج المحسن"""
    try:
        return await form_handler.show_form_summary(update, context)
    except Exception as e:
        logger.error(f"Error showing form summary: {str(e)}")
        return await error_handler.handle_validation_error(
            update, context, None, f"خطأ في عرض ملخص النموذج: {str(e)}"
        )

# ============================================================================
# 9. دوال مساعدة إضافية
# ============================================================================

async def handle_form_error(update: Update, context: ContextTypes.DEFAULT_TYPE, error: Exception, field=None) -> int:
    """معالجة أخطاء النموذج"""
    try:
        return await error_handler.handle_validation_error(
            update, context, field, str(error)
        )
    except Exception as e:
        logger.error(f"Error in error handler: {str(e)}")
        await update.message.reply_text("حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى.")
        return ConversationState.MAIN_MENU

async def sanitize_form_data(form_data: dict) -> dict:
    """تنظيف بيانات النموذج"""
    try:
        return sanitizer.sanitize_form_data(form_data)
    except Exception as e:
        logger.error(f"Error sanitizing form data: {str(e)}")
        return form_data

# ============================================================================
# 10. مثال على الاستخدام في دالة confirm_submission
# ============================================================================

async def confirm_submission(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # ... الكود الأصلي ...
    
    if update.message.text == 'تأكيد الإرسال':
        try:
            form = context.user_data.get('form')
            if not form:
                return await handle_form_error(update, context, Exception("النموذج غير موجود"))
                
            form_data = context.user_data.get('form_data_for_submission', {})
            if not form_data:
                return await handle_form_error(update, context, Exception("بيانات النموذج غير موجودة"))
                
            # تنظيف البيانات
            clean_form_data = await sanitize_form_data(form_data)
            
            # إرسال البيانات
            response = await api_service.submit_complaint(clean_form_data)
            request_number = response.get('request_number')
            
            await update.message.reply_text(
                f"تم تسجيل الشكوى بنجاح. الطلب الخاص بكم أخذ الرقم {request_number}",
                reply_markup=get_main_menu_keyboard()
            )
            
            # تنظيف البيانات
            context.user_data.clear()
            context.user_data['conversation_state'] = ConversationState.MAIN_MENU
            return ConversationState.MAIN_MENU
            
        except Exception as e:
            logger.error(f"Error submitting complaint: {str(e)}")
            return await handle_form_error(update, context, e)
    
    # ... باقي الكود ...

# ============================================================================
# 11. دوال إضافية للتنقل
# ============================================================================

async def go_to_previous_field_improved(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """الانتقال للحقل السابق باستخدام المعالج المحسن"""
    try:
        return await form_handler.go_to_previous_field(update, context)
    except Exception as e:
        return await handle_form_error(update, context, e)

async def go_to_next_field_improved(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """الانتقال للحقل التالي باستخدام المعالج المحسن"""
    try:
        return await form_handler.go_to_next_field(update, context)
    except Exception as e:
        return await handle_form_error(update, context, e)

async def skip_current_field_improved(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """تخطي الحقل الحالي باستخدام المعالج المحسن"""
    try:
        return await form_handler.skip_current_field(update, context)
    except Exception as e:
        return await handle_form_error(update, context, e)

# ============================================================================
# 12. دالة لفحص حالة النموذج
# ============================================================================

async def check_form_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """فحص حالة النموذج"""
    try:
        progress_tracker = context.user_data.get('form_progress')
        if not progress_tracker:
            await update.message.reply_text("لا يوجد نموذج نشط.")
            return ConversationState.MAIN_MENU
            
        # عرض حالة النموذج
        progress_info = await form_handler.get_progress_info(progress_tracker)
        
        message = "📊 حالة النموذج:\n\n"
        message += progress_info
        
        # لوحة المفاتيح
        keyboard = [
            ['✏️ متابعة النموذج'],
            ['🏠 القائمة الرئيسية']
        ]
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
        
        await update.message.reply_text(message, reply_markup=reply_markup)
        return ConversationState.MAIN_MENU
        
    except Exception as e:
        return await handle_form_error(update, context, e)

# ============================================================================
# 13. دالة لاستعادة النموذج المحفوظ
# ============================================================================

async def restore_saved_form(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """استعادة النموذج المحفوظ"""
    try:
        saved_progress = context.user_data.get('saved_form_progress')
        if not saved_progress:
            await update.message.reply_text("لا يوجد نموذج محفوظ.")
            return ConversationState.MAIN_MENU
            
        # استعادة النموذج
        form = context.user_data.get('form')
        if not form:
            await update.message.reply_text("النموذج غير موجود.")
            return ConversationState.MAIN_MENU
            
        # استعادة التقدم
        return await form_handler.start_form_filling(update, context, form)
        
    except Exception as e:
        return await handle_form_error(update, context, e)

# ============================================================================
# ملاحظات مهمة
# ============================================================================

"""
ملاحظات للتطبيق:

1. تأكد من أن جميع الملفات المحسنة موجودة في نفس المجلد
2. تأكد من أن جميع الاستيرادات صحيحة
3. اختبر كل ميزة على حدة قبل التطبيق الكامل
4. احتفظ بنسخة احتياطية من bot.py الأصلي
5. راجع الأخطاء في السجلات عند التطبيق

الميزات الجديدة:
- معالجة محسنة للأخطاء
- فاليديشن متقدم للحقول
- معالجة محسنة للملفات والموقع
- تتبع التقدم
- التنقل الذكي
- الحفظ التلقائي
"""