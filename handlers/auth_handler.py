import logging
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardRemove, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from config.conversation_states import ConversationState
from config.settings import settings
from handlers.base_handler import BaseHandler
from utils.performance_monitor import monitor_async_performance

logger = logging.getLogger(__name__)

class AuthHandler(BaseHandler):
    """Handler for authentication operations"""
    
    def __init__(self, api_service=None):
        super().__init__()
        self.api_service = api_service
        self.MOBILE_CODE = settings.mobile_code
        self.MOBILE_LENGTH = settings.mobile_length
        self.TOKEN_EXPIRY_DAYS = 2  # التوكن ينتهي بعد يومين
        
        # للاختبار فقط - توكن ستاتيكي
        self.TEST_MODE = True  # تغيير هذا إلى False لإعادة تفعيل المصادقة الحقيقية
        self.STATIC_TOKEN = "test_token_12345"  # توكن ستاتيكي للاختبار
        
    @monitor_async_performance
    async def process(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> ConversationState:
        """Process authentication interactions"""
        current_state = context.user_data.get('current_state')
        
        if current_state == ConversationState.AUTH_CHECK:
            return await self._check_auth_status(update, context)
        elif current_state == ConversationState.ENTER_MOBILE:
            return await self._handle_mobile_input(update, context)
        elif current_state == ConversationState.ENTER_OTP:
            return await self._handle_otp_input(update, context)
        else:
            logger.error(f"Invalid auth state: {current_state}")
            return ConversationState.MAIN_MENU
    
    async def _check_auth_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> ConversationState:
        """Check if user is authenticated and token is valid"""
        
        # للاختبار فقط - اعتبار المستخدم مصادق عليه دائماً
        if self.TEST_MODE:
            logger.info("TEST MODE: User automatically authenticated")
            context.user_data['user_authenticated'] = True
            context.user_data['access_token'] = self.STATIC_TOKEN
            context.user_data['token_timestamp'] = datetime.now().isoformat()
            
            # تحديث API service token
            if self.api_service:
                self.api_service.update_token(self.STATIC_TOKEN, 'Bearer')
            
            return ConversationState.SERVICE_MENU
        
        # الكود الأصلي للمصادقة الحقيقية
        try:
            # Check if user has a valid token
            token = context.user_data.get('access_token')
            token_timestamp = context.user_data.get('token_timestamp')
            
            if not token or not token_timestamp:
                logger.info("No token found, requesting authentication")
                return await self._start_auth_flow(update, context)
            
            # Check if token is expired (2 days)
            token_date = datetime.fromisoformat(token_timestamp)
            if datetime.now() - token_date > timedelta(days=self.TOKEN_EXPIRY_DAYS):
                logger.info("Token expired, requesting re-authentication")
                # Clear expired token
                context.user_data.pop('access_token', None)
                context.user_data.pop('token_timestamp', None)
                context.user_data.pop('user_authenticated', None)
                return await self._start_auth_flow(update, context)
            
            # Token is valid, user is authenticated
            logger.info("User has valid token, proceeding to service menu")
            context.user_data['user_authenticated'] = True
            return ConversationState.SERVICE_MENU
            
        except Exception as e:
            logger.error(f"Error checking auth status: {e}")
            return await self._start_auth_flow(update, context)
    
    async def _start_auth_flow(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> ConversationState:
        """Start authentication flow"""
        
        # للاختبار فقط - تخطي المصادقة
        if self.TEST_MODE:
            logger.info("TEST MODE: Skipping authentication, user automatically authenticated")
            context.user_data['user_authenticated'] = True
            context.user_data['access_token'] = self.STATIC_TOKEN
            context.user_data['token_timestamp'] = datetime.now().isoformat()
            
            # تحديث API service token
            if self.api_service:
                self.api_service.update_token(self.STATIC_TOKEN, 'Bearer')
            
            return ConversationState.SERVICE_MENU
        
        # الكود الأصلي
        await update.message.reply_text(
            "يرجى تسجيل الدخول للمتابعة. أدخل رقم هاتفك المحمول:",
            reply_markup=ReplyKeyboardRemove()
        )
        context.user_data['current_state'] = ConversationState.ENTER_MOBILE
        return ConversationState.ENTER_MOBILE
            
    async def _handle_mobile_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> ConversationState:
        """Handle mobile number input"""
        
        # للاختبار فقط - تخطي إدخال رقم الهاتف
        if self.TEST_MODE:
            logger.info("TEST MODE: Skipping mobile input, user automatically authenticated")
            context.user_data['user_authenticated'] = True
            context.user_data['access_token'] = self.STATIC_TOKEN
            context.user_data['token_timestamp'] = datetime.now().isoformat()
            context.user_data['mobile'] = '0947800974'  # رقم افتراضي للاختبار
            
            # تحديث API service token
            if self.api_service:
                self.api_service.update_token(self.STATIC_TOKEN, 'Bearer')
            
            await update.message.reply_text(
                "TEST MODE: تم تسجيل الدخول تلقائياً! 🎉",
                reply_markup=ReplyKeyboardMarkup(
                    keyboard=[
                        ["طلباتي", "تقديم طلب"],
                        ["عودة للقائمة الرئيسية"]
                    ],
                    resize_keyboard=True,
                    one_time_keyboard=True
                )
            )
            return ConversationState.SERVICE_MENU
        
        # الكود الأصلي
        mobile = update.message.text.strip()
        
        # Validate mobile number format
        if not mobile.startswith(self.MOBILE_CODE):
            await update.message.reply_text(
                f"يرجى إدخال رقم هاتف صحيح يبدأ بـ {self.MOBILE_CODE}"
            )
            return ConversationState.ENTER_MOBILE
            
        # Check length without prefix (remove prefix for length validation)
        mobile_without_prefix = mobile[len(self.MOBILE_CODE):]
        if len(mobile_without_prefix) != 8:  # Assuming 8 digits after prefix
            await update.message.reply_text(
                f"يرجى إدخال رقم هاتف من 8 أرقام بعد البادئة {self.MOBILE_CODE}"
            )
            return ConversationState.ENTER_MOBILE
            
        # Store mobile number
        context.user_data['mobile'] = mobile
        
        # Request OTP
        try:
            await self.api_service.request_otp(mobile)
            await update.message.reply_text(
                f"تم إرسال رمز التحقق إلى {mobile}",
                reply_markup=ReplyKeyboardRemove()
            )
            context.user_data['current_state'] = ConversationState.ENTER_OTP
            return ConversationState.ENTER_OTP
            
        except Exception as e:
            logger.error(f"Error requesting OTP: {e}")
            await update.message.reply_text(
                "حدث خطأ في إرسال رمز التحقق. يرجى المحاولة مرة أخرى."
            )
            return ConversationState.ENTER_MOBILE
            
    async def _handle_otp_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> ConversationState:
        """Handle OTP verification"""
        
        # للاختبار فقط - تخطي إدخال OTP
        if self.TEST_MODE:
            logger.info("TEST MODE: Skipping OTP input, user automatically authenticated")
            context.user_data['user_authenticated'] = True
            context.user_data['access_token'] = self.STATIC_TOKEN
            context.user_data['token_timestamp'] = datetime.now().isoformat()
            
            # تحديث API service token
            if self.api_service:
                self.api_service.update_token(self.STATIC_TOKEN, 'Bearer')
            
            await update.message.reply_text(
                "TEST MODE: تم تسجيل الدخول تلقائياً! 🎉",
                reply_markup=ReplyKeyboardMarkup(
                    keyboard=[
                        ["طلباتي", "تقديم طلب"],
                        ["عودة للقائمة الرئيسية"]
                    ],
                    resize_keyboard=True,
                    one_time_keyboard=True
                )
            )
            return ConversationState.SERVICE_MENU
        
        # الكود الأصلي
        otp = update.message.text.strip()
        mobile = context.user_data.get('mobile')
        
        if not mobile:
            await update.message.reply_text(
                "يرجى إعادة إدخال رقم الهاتف أولاً."
            )
            context.user_data['current_state'] = ConversationState.ENTER_MOBILE
            return ConversationState.ENTER_MOBILE
            
        try:
            result = await self.api_service.login_otp(mobile, otp)
            
            if result.get('status') == 'success':
                # Store authentication data
                context.user_data['user_authenticated'] = True
                context.user_data['access_token'] = result.get('access_token')
                context.user_data['token_type'] = result.get('token_type', 'Bearer')
                context.user_data['token_timestamp'] = datetime.now().isoformat()
                
                # Update API service token
                if self.api_service:
                    self.api_service.update_token(
                        result.get('access_token'),
                        result.get('token_type', 'Bearer')
                    )
                
                await update.message.reply_text(
                    "تم تسجيل الدخول بنجاح! 🎉",
                    reply_markup=ReplyKeyboardMarkup(
                        keyboard=[
                            ["طلباتي", "تقديم طلب"],
                            ["عودة للقائمة الرئيسية"]
                        ],
                        resize_keyboard=True,
                        one_time_keyboard=True
                    )
                )
                return ConversationState.SERVICE_MENU
            else:
                await update.message.reply_text(
                    "رمز التحقق غير صحيح. يرجى المحاولة مرة أخرى."
                )
                return ConversationState.ENTER_OTP
                
        except Exception as e:
            logger.error(f"Error verifying OTP: {e}")
            await update.message.reply_text(
                "حدث خطأ في التحقق من الرمز. يرجى المحاولة مرة أخرى."
            )
            return ConversationState.ENTER_OTP
            
    async def is_authenticated(self, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Check if user is authenticated with valid token"""
        
        # للاختبار فقط - اعتبار المستخدم مصادق عليه دائماً
        if self.TEST_MODE:
            return True
        
        # الكود الأصلي
        try:
            token = context.user_data.get('access_token')
            token_timestamp = context.user_data.get('token_timestamp')
            
            if not token or not token_timestamp:
                return False
            
            # Check if token is expired
            token_date = datetime.fromisoformat(token_timestamp)
            if datetime.now() - token_date > timedelta(days=self.TOKEN_EXPIRY_DAYS):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking authentication: {e}")
            return False
        
    async def logout(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> ConversationState:
        """Logout user"""
        context.user_data.clear()
        await update.message.reply_text(
            "تم تسجيل الخروج بنجاح.",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[
                    ["حول المنصة"], ["حول الوزارة"], ["حول الشركة المطورة"],
                    ["سمعنا صوتك"]
                ],
                resize_keyboard=True,
                one_time_keyboard=True
            )
        )
        return ConversationState.MAIN_MENU
    
    async def update_token_activity(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Update token activity timestamp"""
        if context.user_data.get('access_token'):
            context.user_data['token_timestamp'] = datetime.now().isoformat()
            logger.debug("Token activity updated")