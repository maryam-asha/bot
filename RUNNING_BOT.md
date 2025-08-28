# دليل تشغيل البوت

## 🚀 تشغيل سريع

### 1. البوت المبسط (الموصى به للبداية)
```bash
python bot_simple.py
```

### 2. البوت مع نظام Router
```bash
python bot_with_router.py
```

### 3. البوت الأصلي
```bash
python bot.py
```

## 🔧 متطلبات التشغيل

### 1. تثبيت المتطلبات
```bash
pip install -r requirements.txt
```

### 2. إعداد ملف البيئة
تأكد من وجود ملف `.env` يحتوي على:
```
TELEGRAM_TOKEN=your_bot_token_here
```

### 3. التأكد من صحة الإعدادات
```bash
python -c "from config.settings import settings; print('Token:', settings.telegram_token[:10] + '...')"
```

## 🎯 أنواع البوتات المتاحة

### 1. **bot_simple.py** - البوت المبسط
- **المميزات**: سهل التشغيل، يحتوي على القوائم الأساسية
- **الاستخدام**: للتجربة والتأكد من عمل البوت
- **الوظائف**: القائمة الرئيسية، المعلومات العامة، الخدمات الأساسية

### 2. **bot_with_router.py** - البوت المتقدم
- **المميزات**: نظام router متطور، handlers منفصلة، مراقبة الأداء
- **الاستخدام**: للإنتاج والاستخدام الكامل
- **الوظائف**: جميع المميزات مع تحسينات الأداء

### 3. **bot.py** - البوت الأصلي
- **المميزات**: البوت الأصلي قبل التحسينات
- **الاستخدام**: للمقارنة أو الاحتفاظ بالنسخة الأصلية

## ✅ خطوات التأكد من التشغيل

### 1. اختبار البوت المبسط
```bash
python bot_simple.py
```

**النتيجة المتوقعة:**
```
2025-08-28 14:47:42,326 - utils.cache_manager - INFO - Cache manager started
2025-08-28 14:47:42,328 - __main__ - INFO - تم تهيئة البوت بنجاح
2025-08-28 14:47:42,330 - __main__ - INFO - البوت يعمل بنجاح! 🚀
2025-08-28 14:47:42,330 - __main__ - INFO - اضغط Ctrl+C لإيقاف البوت
```

### 2. اختبار الأوامر
في Telegram:
- أرسل `/start` - يجب أن تظهر القائمة الرئيسية
- أرسل `/help` - يجب أن تظهر رسالة المساعدة
- اختر "حول المنصة" - يجب أن تظهر المعلومات

### 3. اختبار القوائم
- اختر "الخدمات" - يجب أن تظهر قائمة الخدمات
- اختر "عودة للقائمة الرئيسية" - يجب أن تعود للقائمة الرئيسية

## 🚨 حل المشاكل الشائعة

### 1. خطأ "MainMenuHandler.__init__() takes 1 positional argument but 2 were given"
**الحل:** تم إصلاح هذا الخطأ في الإصدارات الجديدة.

### 2. خطأ "No module named 'config'"
**الحل:**
```bash
# تأكد من أنك في المجلد الصحيح
cd /path/to/YourVoiceBot

# أو أضف المجلد للـ Python path
export PYTHONPATH="${PYTHONPATH}:/path/to/YourVoiceBot"
```

### 3. خطأ "Invalid token"
**الحل:**
```bash
# تحقق من ملف .env
cat .env

# تأكد من أن التوكن صحيح
echo $TELEGRAM_TOKEN
```

### 4. خطأ "Connection failed"
**الحل:**
- تحقق من اتصال الإنترنت
- تأكد من أن البوت مفعل في Telegram
- تحقق من إعدادات الجدار الناري

## 📊 مراقبة الأداء

### 1. تشغيل تحليل الأداء
```bash
python performance_analysis.py
```

### 2. مراقبة Logs
```bash
# تشغيل البوت مع logs مفصلة
python bot_simple.py 2>&1 | tee bot.log

# مراقبة Logs في الوقت الفعلي
tail -f bot.log
```

### 3. إحصائيات الأداء
البوت يطبع إحصائيات الأداء كل ساعة تلقائياً.

## 🔄 تطوير وإضافة ميزات

### 1. إضافة Handler جديد
```python
# في handlers/new_handler.py
from handlers.base_handler import BaseHandler

class NewHandler(BaseHandler):
    def __init__(self, api_service=None):
        super().__init__()
        self.api_service = api_service
        
    async def process(self, update, context):
        # معالجة الرسالة
        return ConversationState.MAIN_MENU
```

### 2. إضافة للـ Router
```python
# في message_router.py
from handlers.new_handler import NewHandler
self.state_handlers[ConversationState.NEW_STATE] = NewHandler(self.api_service)
```

### 3. اختبار التغييرات
```bash
# إعادة تشغيل البوت بعد التغييرات
python bot_with_router.py
```

## 🎯 نصائح للاستخدام

### 1. للتطوير
- استخدم `bot_simple.py` للتجارب السريعة
- استخدم `bot_with_router.py` للتطوير المتقدم
- راجع logs للتشخيص

### 2. للإنتاج
- استخدم `bot_with_router.py` للحصول على أفضل أداء
- فعّل مراقبة الأداء
- راقب logs بانتظام

### 3. للصيانة
- احتفظ بنسخة احتياطية من الكود
- راجع إحصائيات الأداء دورياً
- حدث المتطلبات بانتظام

## 📞 الدعم

### للمشاكل التقنية
1. راجع logs للتفاصيل
2. تحقق من الإعدادات
3. جرب البوت المبسط أولاً

### للمساعدة
- راجع `README_ROUTER.md` للتفاصيل التقنية
- راجع `ROUTER_SYSTEM.md` لفهم النظام
- استخدم `performance_analysis.py` لتحليل الأداء

---

*البوت الآن جاهز للاستخدام! 🚀*