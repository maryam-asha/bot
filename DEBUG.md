# 🐛 دليل تشخيص المشاكل

## 🚨 المشكلة الحالية

البوت يعرض رسالة "حدث خطأ في النموذج. يرجى المحاولة مرة أخرى" عند محاولة ملء النموذج.

## 🔍 خطوات التشخيص

### **1. اختبار التهيئة**

```bash
python test_bot.py
```

هذا سيتحقق من:
- ✅ تهيئة API Service
- ✅ إنشاء المعالجات المحسنة
- ✅ ربط المعالجات معاً

### **2. فحص السجلات**

```bash
# تشغيل البوت مع تسجيل مفصل
python bot.py 2>&1 | tee bot.log
```

ابحث عن:
- `Enhanced form handlers initialized successfully`
- `Error in improved form handler`
- `Error starting form`

### **3. اختبار المعالجات الفردية**

```python
# في Python REPL
from bot import form_handler, file_handler, location_handler, error_handler

print(f"form_handler: {form_handler}")
print(f"file_handler: {file_handler}")
print(f"location_handler: {location_handler}")
print(f"error_handler: {error_handler}")
```

## 🔧 الحلول المحتملة

### **المشكلة 1: عدم تهيئة المعالجات**

**الأعراض:**
```
AttributeError: 'NoneType' object has no attribute 'handle_field_input'
```

**الحل:**
```python
# تأكد من استدعاء initialize_bot() في main()
await initialize_bot()
```

### **المشكلة 2: عدم ربط المعالجات**

**الأعراض:**
```
AttributeError: 'ImprovedFormHandler' object has no attribute 'file_handler'
```

**الحل:**
```python
# في initialize_bot()
form_handler.set_handlers(file_handler, location_handler, error_handler)
```

### **المشكلة 3: عدم وجود FormProgressTracker**

**الأعراض:**
```
KeyError: 'form_progress'
```

**الحل:**
```python
# تأكد من أن start_form_filling ينشئ FormProgressTracker
progress_tracker = FormProgressTracker(form)
context.user_data['form_progress'] = progress_tracker
```

### **المشكلة 4: خطأ في API**

**الأعراض:**
```
HTTPError: 404 Not Found
```

**الحل:**
```python
# تأكد من صحة endpoint
f"{settings.base_url}/complaints/form-for-request"
```

## 📋 قائمة التحقق

### **✅ قبل التشغيل:**
- [ ] جميع الملفات المحسنة موجودة
- [ ] الاستيرادات صحيحة في bot.py
- [ ] initialize_bot() يستدعى في main()
- [ ] المعالجات مربوطة معاً

### **✅ أثناء التشغيل:**
- [ ] رسالة "Enhanced form handlers initialized successfully"
- [ ] لا توجد أخطاء في التهيئة
- [ ] المعالجات متاحة في context

### **✅ عند ملء النموذج:**
- [ ] select_subject يستدعي form_handler.start_form_filling
- [ ] FormProgressTracker ينشأ بنجاح
- [ ] الحقول تعرض بشكل صحيح

## 🧪 اختبارات إضافية

### **اختبار 1: فحص المعالجات**

```python
async def test_handlers():
    await initialize_bot()
    
    # اختبار المعالجات
    assert form_handler is not None
    assert file_handler is not None
    assert location_handler is not None
    assert error_handler is not None
    
    # اختبار الربط
    assert form_handler.file_handler is file_handler
    assert form_handler.location_handler is location_handler
    assert form_handler.error_handler is error_handler
    
    print("✅ جميع المعالجات تعمل بشكل صحيح")
```

### **اختبار 2: فحص النموذج**

```python
async def test_form():
    # محاكاة إنشاء نموذج
    form_data = {
        "groups": [
            {
                "id": 1,
                "name": "معلومات أساسية",
                "order": 1,
                "attributes": [
                    {
                        "id": 1,
                        "name": "الاسم",
                        "type_code": "text",
                        "required": True
                    }
                ]
            }
        ],
        "documents": [],
        "form_version_id": 1
    }
    
    form = DynamicForm(form_data)
    progress_tracker = FormProgressTracker(form)
    
    print(f"✅ النموذج: {form}")
    print(f"✅ متتبع التقدم: {progress_tracker}")
```

## 🚀 تشغيل البوت

### **الطريقة 1: التشغيل المباشر**

```bash
python bot.py
```

### **الطريقة 2: التشغيل مع التسجيل**

```bash
python bot.py > bot.log 2>&1
```

### **الطريقة 3: التشغيل في الخلفية**

```bash
nohup python bot.py > bot.log 2>&1 &
```

## 📞 الدعم

إذا استمرت المشكلة:

1. **راجع السجلات** للبحث عن أخطاء محددة
2. **اختبر كل مرحلة** على حدة
3. **تحقق من API** باستخدام Postman أو curl
4. **أنشئ Issue** مع تفاصيل الخطأ

## 🔄 التطبيق التدريجي

### **المرحلة 1: المعالج الأساسي فقط**
```python
form_handler = ImprovedFormHandler(api_service)
# لا تربط المعالجات الأخرى
```

### **المرحلة 2: إضافة معالج الملفات**
```python
file_handler = FormFileHandler(api_service)
form_handler.set_handlers(file_handler, None, None)
```

### **المرحلة 3: إضافة معالج الموقع**
```python
location_handler = FormLocationHandler(api_service)
form_handler.set_handlers(file_handler, location_handler, None)
```

### **المرحلة 4: إضافة معالج الأخطاء**
```python
error_handler = FormErrorHandler()
form_handler.set_handlers(file_handler, location_handler, error_handler)
```

---

**ملاحظة**: تأكد من اختبار كل مرحلة قبل الانتقال للتالية!