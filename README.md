# YourVoiceBot - Refactored Version

A Telegram bot for handling complaints and requests, refactored using Python best practices and design patterns.

## 🏗️ Architecture Overview

The bot has been refactored to follow these design principles:

- **Single Responsibility Principle**: Each class has one clear responsibility
- **Dependency Injection**: Services are injected rather than created directly
- **Template Method Pattern**: Base handler class provides common functionality
- **Strategy Pattern**: Different handlers for different conversation states
- **Factory Pattern**: Keyboard creation is centralized

## 📁 Project Structure

```
YourVoiceBot/
├── config/                     # Configuration management
│   ├── __init__.py
│   ├── settings.py            # Pydantic-based settings
│   └── conversation_states.py # State enums and transitions
├── handlers/                   # Conversation handlers
│   ├── __init__.py
│   ├── base_handler.py        # Base handler class
│   ├── main_menu_handler.py   # Main menu logic
│   ├── service_menu_handler.py # Service menu logic
│   ├── form_handler.py        # Form handling logic
│   ├── auth_handler.py        # Authentication logic
│   └── request_handler.py     # Request handling logic
├── keyboards/                  # Keyboard utilities
│   ├── __init__.py
│   └── base_keyboard.py       # Keyboard creation utilities
├── services/                   # External services
│   ├── __init__.py
│   ├── api_service.py         # API integration
│   └── http_client.py         # HTTP client with pooling
├── utils/                      # Utility functions
│   ├── __init__.py
│   └── error_handler.py       # Centralized error handling
├── forms/                      # Form models (existing)
├── bot_refactored.py          # Main bot class
├── requirements.txt            # Dependencies
└── README.md                  # This file
```

## 🚀 Key Improvements

### 1. **Modular Architecture**
- Separated concerns into focused modules
- Each handler manages one conversation state
- Easy to add new features without modifying existing code

### 2. **Better Error Handling**
- Centralized error handling with `BotErrorHandler`
- Consistent error messages and logging
- Graceful fallbacks for different error types

### 3. **Configuration Management**
- Pydantic-based settings with validation
- Environment variable support
- Type-safe configuration access

### 4. **HTTP Client Improvements**
- Connection pooling and session management
- Better timeout handling
- Automatic retry logic

### 5. **State Management**
- Clear state transitions
- Validation of state changes
- Better navigation logic

## 🛠️ Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd YourVoiceBot
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Run the bot**
```bash
python bot_refactored.py
```

## 🔧 Configuration

Create a `.env` file with the following variables:

```env
# Required
TELEGRAM_TOKEN=your_telegram_bot_token

# Optional (with defaults)
BASE_URL=https://yourvoice.sy/api
IMAGE_BASE_URL=https://yourvoice.sy/
COUNTRY_CODE=963
USERNAME_HINT=## ### ####
MOBILE_LENGTH=8
MOBILE_CODE=09
LOG_LEVEL=INFO
```

## 📝 Usage Examples

### Adding a New Handler

```python
from handlers.base_handler import BaseHandler
from config.conversation_states import ConversationState

class NewFeatureHandler(BaseHandler):
    async def process(self, update, context):
        # Your logic here
        return ConversationState.MAIN_MENU
```

### Creating Custom Keyboards

```python
from keyboards.base_keyboard import BaseKeyboard

keyboard = BaseKeyboard.create_reply_keyboard(
    buttons=[["Option 1", "Option 2"]],
    include_back=True,
    include_main_menu=True
)
```

### Error Handling

```python
from utils.error_handler import BotErrorHandler

error_handler = BotErrorHandler()
await error_handler.handle_api_error(update, error, "context_name")
```

## 🧪 Testing

The project includes testing infrastructure:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=.

# Run specific test file
pytest tests/test_handlers.py
```

## 🔍 Code Quality

The project uses several tools for code quality:

- **Black**: Code formatting
- **Flake8**: Linting
- **MyPy**: Type checking

```bash
# Format code
black .

# Check types
mypy .

# Lint code
flake8 .
```

## 📊 Performance Improvements

- **Connection Pooling**: HTTP client reuses connections
- **Async Operations**: Non-blocking I/O operations
- **Memory Management**: Better resource cleanup
- **Caching**: Intelligent caching of frequently used data

## 🔒 Security Features

- **Input Validation**: All user inputs are validated
- **Error Sanitization**: Errors don't expose sensitive information
- **Rate Limiting**: Built-in rate limiting for API calls
- **Secure Configuration**: Sensitive data in environment variables

## 🚧 Migration from Old Code

To migrate from the old monolithic structure:

1. **Update imports** to use new module structure
2. **Replace global variables** with configuration settings
3. **Update error handling** to use centralized error handler
4. **Refactor handlers** to inherit from `BaseHandler`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure code quality checks pass
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue in the repository
- Check the documentation
- Review the code examples

## 🔮 Future Enhancements

- **Database Integration**: Persistent storage for user data
- **Analytics**: Usage statistics and monitoring
- **Multi-language Support**: Internationalization
- **Plugin System**: Extensible architecture for custom features
- **Web Dashboard**: Admin interface for bot management

