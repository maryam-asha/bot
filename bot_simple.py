import logging
import asyncio
import signal
import sys
from telegram.ext import Application, ContextTypes, CommandHandler, MessageHandler, filters
from telegram import Update, ReplyKeyboardMarkup
from services.api_service import ApiService
from config.settings import settings
from utils.performance_monitor import performance_monitor, monitor_async_performance
from utils.cache_manager import cache_manager

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class SimpleBot:
    """Bot مبسط للتأكد من عمله"""
    
    def __init__(self):
        self.api_service: ApiService = None
        self.application = None
        
        # Performance monitoring
        performance_monitor.enable_tracemalloc()
        
    @monitor_async_performance
    async def initialize(self):
        """تهيئة البوت"""
        try:
            # بدء مدير التخزين المؤقت
            await cache_manager.start()
            
            # تهيئة خدمة API
            self.api_service = ApiService()
            await self.api_service.initialize_urls()
            
            # بناء التطبيق
            self.application = Application.builder().token(settings.telegram_token).build()
            
            # إعداد المعالجات
            await self._setup_handlers()
            
            logger.info("تم تهيئة البوت بنجاح")
            
        except Exception as e:
            logger.error(f"فشل في تهيئة البوت: {str(e)}")
            raise
            
    async def _setup_handlers(self):
        """إعداد معالجات المحادثة"""
        # معالج الأوامر
        self.application.add_handler(CommandHandler('start', self._handle_start))
        self.application.add_handler(CommandHandler('help', self._handle_help))
        
        # معالج الرسائل النصية
        self.application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, 
            self._handle_text_message
        ))
        
        # معالج عام للتحديثات (للتشخيص)
        self.application.add_handler(MessageHandler(filters.ALL, self._debug_log_update), group=1)
        self.application.add_error_handler(self._on_error)
        
    @monitor_async_performance
    async def _handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة أمر /start"""
        keyboard = [
            ["حول المنصة"], ["حول الوزارة"], ["حول الشركة المطورة"],
            ["الخدمات"]
        ]
        
        await update.message.reply_text(
            "مرحباً بك في منصة صوتك! 👋\n\nاختر من القائمة أدناه:",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=keyboard,
                resize_keyboard=True,
                one_time_keyboard=True
            )
        )
        
    @monitor_async_performance
    async def _handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة أمر /help"""
        help_text = """
🤖 مساعدة البوت:

/start - بدء البوت من جديد
/help - عرض هذه المساعدة

للحصول على المساعدة، يمكنك:
1. اختيار "الخدمات" من القائمة
2. أو التواصل مع الدعم الفني
        """
        await update.message.reply_text(help_text)
        
    @monitor_async_performance
    async def _handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة الرسائل النصية"""
        text = update.message.text
        
        if text == "حول المنصة":
            response = "منصة صوتك هي المنصة الأولى للمواطنين للتعبير عن آرائهم ومقترحاتهم وتقديم شكاويهم في كل المواضيع والخدمات والجهات العاملة تحت وزارة التقانة والاتصالات للجمهورية العربية السورية وقريباً في جميع الوزارات"
            await update.message.reply_text(response)
            
        elif text == "حول الوزارة":
            response = "تتولى وزارة الاتصالات وتقانة المعلومات في الجمهورية العربية السورية بموجب قواعد تنظيمها مهام متعددة تشمل: تنفيذ السياسات العامة في قطاعات الاتصالات والبريد وتقانة المعلومات، تنظيم وتطوير هذه القطاعات، دعم صناعة البرمجيات والخدمات الرقمية، تشجيع الاستثمار والشراكات بين القطاعين العام والخاص، وضع الخطط اللازمة للتحول الرقمي وضمان أمن المعلومات، المشاركة في المشاريع الدولية والإقليمية، بناء القدرات الفنية والعلمية عبر التدريب ودعم البحث العلمي، ورفع الوعي بأهمية الاتصالات وتقانة المعلومات في التنمية الاقتصادية والاجتماعية"
            await update.message.reply_text(response)
            
        elif text == "حول الشركة المطورة":
            response = "مجموعة أوتوماتا4 هي شركة إقليمية مكرسة لتقديم حلول وخدمات استشارية مخصصة عالية الجودة لتكنولوجيا المعلومات..."
            await update.message.reply_text(response)
            
        elif text == "الخدمات":
            keyboard = [
                ["شكوى"], ["شكر وتقدير"], ["استفسار"], ["اقتراح"],
                ["عودة للقائمة الرئيسية"]
            ]
            
            await update.message.reply_text(
                "اختر نوع الخدمة:",
                reply_markup=ReplyKeyboardMarkup(
                    keyboard=keyboard,
                    resize_keyboard=True,
                    one_time_keyboard=True
                )
            )
            
        elif text == "عودة للقائمة الرئيسية":
            keyboard = [
                ["حول المنصة"], ["حول الوزارة"], ["حول الشركة المطورة"],
                ["الخدمات"]
            ]
            
            await update.message.reply_text(
                "القائمة الرئيسية:",
                reply_markup=ReplyKeyboardMarkup(
                    keyboard=keyboard,
                    resize_keyboard=True,
                    one_time_keyboard=True
                )
            )
            
        elif text in ["شكوى", "شكر وتقدير", "استفسار", "اقتراح"]:
            await update.message.reply_text(
                f"تم اختيار: {text}\n\nهذه الميزة قيد التطوير. سيتم إضافتها قريباً! 🚀",
                reply_markup=ReplyKeyboardMarkup(
                    keyboard=[["عودة للقائمة الرئيسية"]],
                    resize_keyboard=True,
                    one_time_keyboard=True
                )
            )
            
        else:
            await update.message.reply_text(
                "يرجى اختيار خيار من القائمة أدناه:",
                reply_markup=ReplyKeyboardMarkup(
                    keyboard=[
                        ["حول المنصة"], ["حول الوزارة"], ["حول الشركة المطورة"],
                        ["الخدمات"]
                    ],
                    resize_keyboard=True,
                    one_time_keyboard=True
                )
            )
    
    async def _debug_log_update(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """تسجيل التحديثات للتشخيص"""
        logger.info(f"تحديث واصل: {update}")
        if update.message:
            logger.info(f"رسالة من المستخدم: {update.message.from_user.username or update.message.from_user.id}")
            logger.info(f"نص الرسالة: {update.message.text}")
            
    async def _on_error(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """معالجة الأخطاء غير المعالجة"""
        logger.error("خطأ غير معالج", exc_info=context.error)
            
    async def run(self):
        """تشغيل البوت"""
        try:
            await self.initialize()
            
            # تهيئة وبدء التطبيق
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True
            )
            
            logger.info("البوت يعمل بنجاح! 🚀")
            logger.info("اضغط Ctrl+C لإيقاف البوت")
            
            # انتظار إيقاف البوت
            while True:
                await asyncio.sleep(1)
                
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

def signal_handler(signum, frame):
    """معالجة إشارات الإيقاف"""
    logger.info(f"تم استلام الإشارة {signum}، إيقاف البوت...")
    sys.exit(0)

async def main():
    """النقطة الرئيسية لبدء التشغيل"""
    # إعداد معالجات الإشارات
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    bot = SimpleBot()
    await bot.run()

if __name__ == '__main__':
    asyncio.run(main())