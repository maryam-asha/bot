from typing import List, Optional
from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

class BaseKeyboard:
    """Base class for keyboard creation"""
    
    # Common button texts
    BACK_BUTTON = "▶️ الرجوع"
    MAIN_MENU_BUTTON = "⏩ العودةإلى القائمة الرئيسية"
    NEXT_BUTTON = "التالي"
    CONFIRM_BUTTON = "تأكيد"
    DONE_BUTTON = "تم"
    
    @staticmethod
    def create_reply_keyboard(
        buttons: List[List[str]], 
        include_back: bool = True, 
        include_main_menu: bool = True, 
        one_time: bool = True
    ) -> ReplyKeyboardMarkup:
        """Create a reply keyboard with consistent button placement"""
        keyboard = [row[:] for row in buttons]
        
        # Remove existing navigation buttons
        for row in keyboard:
            if BaseKeyboard.BACK_BUTTON in row:
                row.remove(BaseKeyboard.BACK_BUTTON)
            if BaseKeyboard.MAIN_MENU_BUTTON in row:
                row.remove(BaseKeyboard.MAIN_MENU_BUTTON)
        
        # Filter out empty rows
        keyboard = [row for row in keyboard if row]
        
        # Add back button if needed
        if include_back and any(BaseKeyboard.NEXT_BUTTON in row for row in keyboard):
            for row in keyboard:
                if BaseKeyboard.NEXT_BUTTON in row and BaseKeyboard.BACK_BUTTON not in row:
                    row.insert(1, BaseKeyboard.BACK_BUTTON)
                    break
        elif include_back:
            if include_main_menu:
                keyboard.append([BaseKeyboard.BACK_BUTTON, BaseKeyboard.MAIN_MENU_BUTTON])
            else:
                keyboard.append([BaseKeyboard.BACK_BUTTON])
        
        # Add main menu button if needed
        if include_main_menu and not any(BaseKeyboard.MAIN_MENU_BUTTON in row for row in keyboard):
            keyboard.append([BaseKeyboard.MAIN_MENU_BUTTON])
        
        return ReplyKeyboardMarkup(
            keyboard=keyboard,
            resize_keyboard=True,
            one_time_keyboard=one_time
        )
    
    @staticmethod
    def create_inline_keyboard(
        buttons: List[List[dict]], 
        include_back: bool = True
    ) -> InlineKeyboardMarkup:
        """Create an inline keyboard with consistent button placement"""
        keyboard = []
        
        for row in buttons:
            keyboard_row = []
            for button_data in row:
                keyboard_row.append(InlineKeyboardButton(**button_data))
            keyboard.append(keyboard_row)
        
        # Add back button if needed
        if include_back:
            keyboard.append([InlineKeyboardButton("رجوع", callback_data="back")])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def create_navigation_keyboard(
        current_page: int, 
        total_pages: int, 
        include_back: bool = True
    ) -> List[List[str]]:
        """Create a navigation keyboard for pagination"""
        keyboard = []
        
        # Navigation buttons
        nav_buttons = []
        if current_page > 0:
            nav_buttons.append("الصفحة السابقة")
        if current_page < total_pages - 1:
            nav_buttons.append("الصفحة التالية")
        
        if nav_buttons:
            keyboard.append(nav_buttons)
        
        # Back and main menu buttons
        if include_back:
            keyboard.append([BaseKeyboard.BACK_BUTTON, BaseKeyboard.MAIN_MENU_BUTTON])
        
        return keyboard
