#!/usr/bin/env python3
"""
ملف اختبار بسيط للبوت
"""

import asyncio
import logging
from bot import initialize_bot, logger

async def test_initialization():
    """اختبار تهيئة البوت"""
    try:
        logger.info("بدء اختبار التهيئة...")
        await initialize_bot()
        logger.info("✅ تم تهيئة البوت بنجاح!")
        return True
    except Exception as e:
        logger.error(f"❌ فشل في تهيئة البوت: {str(e)}")
        return False

async def test_handlers():
    """اختبار المعالجات"""
    try:
        logger.info("اختبار المعالجات...")
        
        # اختبار أن المعالجات موجودة
        from bot import form_handler, file_handler, location_handler, error_handler
        
        if form_handler is None:
            logger.error("❌ form_handler غير موجود")
            return False
            
        if file_handler is None:
            logger.error("❌ file_handler غير موجود")
            return False
            
        if location_handler is None:
            logger.error("❌ location_handler غير موجود")
            return False
            
        if error_handler is None:
            logger.error("❌ error_handler غير موجود")
            return False
            
        logger.info("✅ جميع المعالجات موجودة")
        return True
        
    except Exception as e:
        logger.error(f"❌ فشل في اختبار المعالجات: {str(e)}")
        return False

async def main():
    """الدالة الرئيسية للاختبار"""
    logger.info("🚀 بدء اختبار البوت...")
    
    # اختبار التهيئة
    init_success = await test_initialization()
    if not init_success:
        logger.error("فشل في اختبار التهيئة")
        return
    
    # اختبار المعالجات
    handlers_success = await test_handlers()
    if not handlers_success:
        logger.error("فشل في اختبار المعالجات")
        return
    
    logger.info("🎉 جميع الاختبارات نجحت!")

if __name__ == "__main__":
    # إعداد التسجيل
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    
    # تشغيل الاختبار
    asyncio.run(main())