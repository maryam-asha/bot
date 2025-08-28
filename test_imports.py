#!/usr/bin/env python3
"""Test file to check if all imports work correctly"""

try:
    print("Testing config imports...")
    from config import (
        TOKEN, SELECT_REQUEST_TYPE, SELECT_COMPLAINT_TYPE, COLLECT_FORM_FIELD, 
        SELECT_SUBJECT, FILL_FORM, MAIN_MENU, SERVICE_MENU, CONFIRM_SUBMISSION, 
        ENTER_MOBILE, ENTER_OTP, SELECT_REQUEST_NUMBER, SELECT_SERVICE_HIERARCHY, 
        SELECT_SERVICE_CATEGORY, SELECT_OTHER_SUBJECT, SELECT_COMPLAINT_SUBJECT, 
        SELECT_SERVICE, SELECT_COMPLIMENT_SIDE, SELECT_TIME_AM_PM
    )
    print("✅ All config imports successful!")
    print(f"TOKEN: {TOKEN}")
    print(f"MAIN_MENU: {MAIN_MENU}")
    
    print("\nTesting other imports...")
    from services.api_service import ApiService
    print("✅ ApiService import successful!")
    
    from forms.form_model import FormAttribute, FormDocument, DynamicForm
    print("✅ Form model imports successful!")
    
    from forms.complaint_form import ComplaintForm
    print("✅ ComplaintForm import successful!")
    
    print("\n🎉 All imports successful! Your bot should work now.")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please check the error above and fix the missing imports.")
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    print("Please check the error above.")
