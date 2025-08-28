import logging
from telegram import Update, ReplyKeyboardRemove, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from config.conversation_states import ConversationState
from config.settings import settings
from handlers.base_handler import BaseHandler
from utils.performance_monitor import monitor_async_performance

logger = logging.getLogger(__name__)

class AuthHandler(BaseHandler):
    """Handler for authentication operations"""
    
    def __init__(self, api_service):
        super().__init__()
        self.api_service = api_service
        self.MOBILE_CODE = settings.mobile_code
        self.MOBILE_LENGTH = settings.mobile_length
        
    @monitor_async_performance
    async def process(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> ConversationState:
        """Process authentication interactions"""
        current_state = context.user_data.get('current_state')
        
        if current_state == ConversationState.ENTER_MOBILE:
            return await self._handle_mobile_input(update, context)
        elif current_state == ConversationState.ENTER_OTP:
            return await self._handle_otp_input(update, context)
        else:
            logger.error(f"Invalid auth state: {current_state}")
            return ConversationState.MAIN_MENU
            
    async def _handle_mobile_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> ConversationState:
        """Handle mobile number input"""
        mobile = update.message.text.strip()
        
        # Validate mobile number format
        if not mobile.startswith(self.MOBILE_CODE):
            await update.message.reply_text(
                f"يرجى إدخال رقم هاتف صحيح يبدأ بـ {self.MOBILE_CODE}"
            )
            return ConversationState.ENTER_MOBILE
            
        if len(mobile) != self.MOBILE_LENGTH:
            await update.message.reply_text(
                f"يرجى إدخال رقم هاتف من {self.MOBILE_LENGTH} أرقام"
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
                context.user_data['user_authenticated'] = True
                context.user_data['access_token'] = result.get('access_token')
                context.user_data['token_type'] = result.get('token_type', 'Bearer')
                
                # Update API service token
                self.api_service.update_token(
                    result.get('access_token'),
                    result.get('token_type', 'Bearer')
                )
                
                await update.message.reply_text(
                    "تم تسجيل الدخول بنجاح! 🎉",
                    reply_markup=ReplyKeyboardMarkup(
                        keyboard=[
                            ["حول المنصة"], ["حول الوزارة"], ["حول الشركة المطورة"], ["سمعنا صوتك"],
                            ["الخدمات"],
                            ["▶️ الرجوع"]
                        ],
                        resize_keyboard=True,
                        one_time_keyboard=True
                    )
                )
                return ConversationState.MAIN_MENU
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
            
    async def start_auth_flow(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> ConversationState:
        """Start authentication flow"""
        await update.message.reply_text(
            "يرجى إدخال رقم الهاتف للمتابعة:",
            reply_markup=ReplyKeyboardRemove()
        )
        context.user_data['current_state'] = ConversationState.ENTER_MOBILE
        return ConversationState.ENTER_MOBILE
        
    async def is_authenticated(self, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Check if user is authenticated"""
        return context.user_data.get('user_authenticated', False)
        
    async def logout(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> ConversationState:
        """Logout user"""
        context.user_data.clear()
        await update.message.reply_text(
            "تم تسجيل الخروج بنجاح.",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[
                    ["حول المنصة"], ["حول الوزارة"], ["حول الشركة المطورة"], ["سمعنا صوتك"],
                    ["الخدمات"]
                ],
                resize_keyboard=True,
                one_time_keyboard=True
            )
        )
        return ConversationState.MAIN_MENU