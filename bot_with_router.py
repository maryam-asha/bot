import logging
import asyncio
import signal
import sys
from telegram.ext import Application, ContextTypes, CommandHandler, MessageHandler, filters, ConversationHandler, CallbackQueryHandler
from telegram import Update
from services.api_service import ApiService
from handlers.message_router import MessageRouter
from config.settings import settings
from utils.performance_monitor import performance_monitor, monitor_async_performance
from utils.cache_manager import cache_manager

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class RouterBot:
    """Bot محسن باستخدام نظام Router مع handlers منفصلة"""
    
    def __init__(self):
        self.api_service: ApiService = None
        self.application = None
        self.message_router: MessageRouter = None
        
        # Performance monitoring
        performance_monitor.enable_tracemalloc()
        
    @monitor_async_performance
    async def initialize(self):
        """تهيئة البوت مع مراقبة الأداء"""
        try:
            # بدء مدير التخزين المؤقت
            await cache_manager.start()
            
            # تهيئة خدمة API
            self.api_service = ApiService()
            await self.api_service.initialize_urls()
            
            # تهيئة موجه الرسائل
            self.message_router = MessageRouter(self.api_service)
            
            # بناء التطبيق مع إعدادات محسنة
            self.application = Application.builder().token(settings.telegram_token).build()
            
            # إعداد المعالجات
            await self._setup_handlers()
            
            logger.info("تم تهيئة البوت بنجاح")
            
        except Exception as e:
            logger.error(f"فشل في تهيئة البوت: {str(e)}")
            raise
            
    async def _setup_handlers(self):
        """إعداد معالجات المحادثة"""
        # معالج الأوامر الخاصة
        self.application.add_handler(CommandHandler('start', self._handle_start_command))
        self.application.add_handler(CommandHandler('cancel', self._handle_cancel_command))
        self.application.add_handler(CommandHandler('help', self._handle_help_command))
        
        # معالج الرسائل النصية
        self.application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, 
            self._handle_text_message
        ))
        
        # معالج الموقع
        self.application.add_handler(MessageHandler(
            filters.LOCATION,
            self._handle_location_message
        ))
        
        # معالج الملفات والوثائق
        self.application.add_handler(MessageHandler(
            filters.Document.ALL,
            self._handle_document_message
        ))
        
        # معالج الصور
        self.application.add_handler(MessageHandler(
            filters.PHOTO,
            self._handle_photo_message
        ))
        
        # معالج الرسائل الصوتية
        self.application.add_handler(MessageHandler(
            filters.VOICE,
            self._handle_voice_message
        ))
        
        # معالج استعلامات Callback
        self.application.add_handler(CallbackQueryHandler(self._handle_callback_query))
        
    @monitor_async_performance
    async def _handle_start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة أمر /start"""
        await self.message_router.handle_special_commands(update, context)
        
    @monitor_async_performance
    async def _handle_cancel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة أمر /cancel"""
        await self.message_router.handle_special_commands(update, context)
        
    @monitor_async_performance
    async def _handle_help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة أمر /help"""
        await self.message_router.handle_special_commands(update, context)
        
    @monitor_async_performance
    async def _handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة الرسائل النصية"""
        # التحقق من الأوامر الخاصة أولاً
        if update.message.text.startswith('/'):
            return await self.message_router.handle_special_commands(update, context)
        
        # توجيه الرسالة إلى المعالج المناسب
        new_state = await self.message_router.route_message(update, context)
        
        # تحديث حالة المحادثة
        context.user_data['current_state'] = new_state
        
    @monitor_async_performance
    async def _handle_location_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة رسائل الموقع"""
        await self.message_router.handle_location(update, context)
        
    @monitor_async_performance
    async def _handle_document_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة رسائل الملفات"""
        await self.message_router.handle_document(update, context)
        
    @monitor_async_performance
    async def _handle_photo_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة رسائل الصور"""
        await self.message_router.handle_photo(update, context)
        
    @monitor_async_performance
    async def _handle_voice_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة الرسائل الصوتية"""
        await self.message_router.handle_voice(update, context)
        
    @monitor_async_performance
    async def _handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة استعلامات Callback"""
        query = update.callback_query
        await query.answer()
        
        # معالجة استعلامات عرض الملفات
        if query.data.startswith('view_files:'):
            await self._handle_view_files_callback(update, context)
        else:
            # معالجة استعلامات أخرى
            await query.edit_message_text("تم معالجة الطلب بنجاح! ✅")
            
    async def _handle_view_files_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة استعلامات عرض الملفات"""
        query = update.callback_query
        data = query.data
        
        try:
            # استخراج معرف الملف من البيانات
            file_info = data.replace('view_files:', '')
            
            # جلب معلومات الملف من API
            # file_data = await self.api_service.get_file_info(file_info)
            
            # عرض معلومات الملف
            await query.edit_message_text(
                f"معلومات الملف:\n{file_info}",
                reply_markup=None
            )
            
        except Exception as e:
            logger.error(f"Error handling view files callback: {e}")
            await query.edit_message_text(
                "حدث خطأ في عرض الملف. يرجى المحاولة مرة أخرى.",
                reply_markup=None
            )
            
    async def run(self):
        """تشغيل البوت مع مراقبة الأداء"""
        try:
            await self.initialize()
            
            # تهيئة وبدء التطبيق
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
            
            logger.info("البوت يعمل مع مراقبة الأداء...")
            
            # حلقة مراقبة الأداء
            while True:
                await asyncio.sleep(3600)  # طباعة الإحصائيات كل ساعة
                performance_monitor.print_summary()
                
        except KeyboardInterrupt:
            logger.info("إيقاف البوت...")
        except Exception as e:
            logger.error(f"خطأ في تشغيل البوت: {e}")
        finally:
            await self.cleanup()
            
    async def cleanup(self):
        """تنظيف الموارد"""
        try:
            if self.application:
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
                
            if self.api_service:
                await self.api_service.close()
                
            await cache_manager.stop()
            performance_monitor.disable_tracemalloc()
            
            logger.info("تم تنظيف البوت بنجاح")
        except Exception as e:
            logger.error(f"خطأ أثناء التنظيف: {e}")
            
    async def get_performance_stats(self):
        """الحصول على إحصائيات الأداء"""
        return {
            'performance': performance_monitor.get_slowest_functions(5),
            'cache': await cache_manager.get_stats(),
            'bot_state': 'running'
        }

def signal_handler(signum, frame):
    """معالجة إشارات الإيقاف"""
    logger.info(f"تم استلام الإشارة {signum}، إيقاف البوت...")
    sys.exit(0)

async def main():
    """النقطة الرئيسية لبدء التشغيل"""
    # إعداد معالجات الإشارات
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    bot = RouterBot()
    await bot.run()

if __name__ == '__main__':
    asyncio.run(main())