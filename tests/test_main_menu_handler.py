import pytest
from unittest.mock import Mock, AsyncMock
from telegram import Update, Message, User
from telegram.ext import ContextTypes
from config.conversation_states import ConversationState
from handlers.main_menu_handler import MainMenuHandler

@pytest.fixture
def mock_update():
    """Create a mock update object"""
    update = Mock(spec=Update)
    update.message = Mock(spec=Message)
    update.message.text = "سمعنا صوتك"
    return update

@pytest.fixture
def mock_context():
    """Create a mock context object"""
    context = Mock(spec=ContextTypes.DEFAULT_TYPE)
    context.user_data = {
        'authenticated': True,
        'conversation_state': ConversationState.MAIN_MENU
    }
    return context

@pytest.fixture
def handler():
    """Create a MainMenuHandler instance"""
    return MainMenuHandler()

class TestMainMenuHandler:
    """Test cases for MainMenuHandler"""
    
    @pytest.mark.asyncio
    async def test_handle_service_access_authenticated(self, handler, mock_update, mock_context):
        """Test service access when user is authenticated"""
        result = await handler._handle_service_access(mock_update, mock_context)
        
        assert result == ConversationState.SERVICE_MENU
        mock_update.message.reply_text.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_service_access_not_authenticated(self, handler, mock_update, mock_context):
        """Test service access when user is not authenticated"""
        mock_context.user_data['authenticated'] = False
        
        result = await handler._handle_service_access(mock_update, mock_context)
        
        assert result == ConversationState.ENTER_MOBILE
        assert mock_context.user_data['authenticated'] is None
        assert mock_context.user_data['auth_token'] is None
        assert mock_context.user_data['mobile'] is None
    
    @pytest.mark.asyncio
    async def test_show_info_response(self, handler, mock_update, mock_context):
        """Test showing info response for menu options"""
        option = "حول المنصة"
        
        await handler._show_info_response(mock_update, mock_context, option)
        
        mock_update.message.reply_text.assert_called_once()
        # Verify the response contains the expected text
        call_args = mock_update.message.reply_text.call_args
        assert "منصة صوتك" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_show_invalid_input_message(self, handler, mock_update, mock_context):
        """Test showing message for invalid input"""
        await handler._show_invalid_input_message(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "يرجى اختيار خيار من القائمة" in call_args[0][0]
    
    def test_get_main_menu_keyboard(self, handler):
        """Test main menu keyboard creation"""
        keyboard = handler.get_main_menu_keyboard()
        
        assert keyboard is not None
        assert len(keyboard.keyboard) == 4  # 4 menu options
        assert keyboard.resize_keyboard is True
        assert keyboard.one_time_keyboard is True
    
    def test_get_service_menu_keyboard(self, handler):
        """Test service menu keyboard creation"""
        keyboard = handler._get_service_menu_keyboard()
        
        assert keyboard is not None
        assert len(keyboard.keyboard) == 2  # 2 service options
        assert keyboard.resize_keyboard is True
        assert keyboard.one_time_keyboard is True

@pytest.mark.asyncio
async def test_main_menu_handler_integration(handler, mock_update, mock_context):
    """Integration test for main menu handler"""
    # Test the main process method
    result = await handler.process(mock_update, mock_context)
    
    # Should return SERVICE_MENU for "سمعنا صوتك" when authenticated
    assert result == ConversationState.SERVICE_MENU

@pytest.mark.asyncio
async def test_main_menu_handler_with_info_option(handler, mock_update, mock_context):
    """Test handler with info menu option"""
    mock_update.message.text = "حول المنصة"
    
    result = await handler.process(mock_update, mock_context)
    
    # Should return MAIN_MENU for info options
    assert result == ConversationState.MAIN_MENU
