from enum import IntEnum
from typing import Dict, Type

class ConversationState(IntEnum):
    """Enumeration for conversation states to improve code readability"""
    MAIN_MENU = 0
    SERVICE_MENU = 1
    SELECT_REQUEST_TYPE = 2
    SELECT_COMPLAINT_TYPE = 3
    SELECT_SUBJECT = 4
    FILL_FORM = 5
    ENTER_MOBILE = 6
    ENTER_OTP = 7
    SELECT_REQUEST_NUMBER = 8
    SELECT_SIDE = 9
    SELECT_SERVICE_HIERARCHY = 10
    SELECT_SERVICE_CATEGORY = 11
    SELECT_COMPLAINT_SUBJECT = 12
    SELECT_SERVICE = 13
    SELECT_COMPLIMENT_SIDE = 14
    CONFIRM_SUBMISSION = 15
    COLLECT_FORM_FIELD = 16
    SELECT_OTHER_SUBJECT = 17
    SELECT_TIME_AM_PM = 18
    
    # حالات جديدة مطلوبة للسيناريو الجديد
    AUTH_CHECK = 19
    VIEW_REQUESTS = 20
    VIEW_REQUEST_DETAILS = 21
    SELECT_ENTITY = 22
    SELECT_ENTITY_CHILDREN = 23
    SELECT_SUBJECTS = 24

# State transition mapping for better navigation
STATE_TRANSITIONS: Dict[ConversationState, ConversationState] = {
    ConversationState.SELECT_COMPLIMENT_SIDE: ConversationState.SERVICE_MENU,
    ConversationState.SELECT_REQUEST_TYPE: ConversationState.SELECT_COMPLIMENT_SIDE,
    ConversationState.SELECT_SUBJECT: ConversationState.SELECT_REQUEST_TYPE,
    ConversationState.SELECT_OTHER_SUBJECT: ConversationState.SELECT_SUBJECT,
    ConversationState.SELECT_SERVICE_CATEGORY: ConversationState.SELECT_SUBJECT,
    ConversationState.SELECT_SERVICE: ConversationState.SELECT_SERVICE_CATEGORY,
    ConversationState.FILL_FORM: ConversationState.SELECT_SUBJECT,
    ConversationState.COLLECT_FORM_FIELD: ConversationState.FILL_FORM,
    ConversationState.CONFIRM_SUBMISSION: ConversationState.COLLECT_FORM_FIELD,
    ConversationState.SELECT_REQUEST_NUMBER: ConversationState.SERVICE_MENU,
    ConversationState.ENTER_OTP: ConversationState.ENTER_MOBILE,
    ConversationState.ENTER_MOBILE: ConversationState.SERVICE_MENU,
    ConversationState.SELECT_TIME_AM_PM: ConversationState.FILL_FORM,
    
    # انتقالات جديدة للسيناريو الجديد
    ConversationState.AUTH_CHECK: ConversationState.ENTER_MOBILE,
    ConversationState.ENTER_MOBILE: ConversationState.ENTER_OTP,
    ConversationState.ENTER_OTP: ConversationState.SERVICE_MENU,
    ConversationState.SERVICE_MENU: ConversationState.VIEW_REQUESTS,
    ConversationState.SERVICE_MENU: ConversationState.SELECT_ENTITY,
    ConversationState.SELECT_ENTITY: ConversationState.SELECT_ENTITY_CHILDREN,
    ConversationState.SELECT_ENTITY_CHILDREN: ConversationState.SELECT_REQUEST_TYPE,
    ConversationState.SELECT_REQUEST_TYPE: ConversationState.SELECT_SUBJECTS,
    ConversationState.SELECT_SUBJECTS: ConversationState.FILL_FORM,
    ConversationState.VIEW_REQUESTS: ConversationState.VIEW_REQUEST_DETAILS,
    ConversationState.VIEW_REQUEST_DETAILS: ConversationState.VIEW_REQUESTS,
}

def get_previous_state(current_state: ConversationState) -> ConversationState:
    """Get the previous state for navigation"""
    return STATE_TRANSITIONS.get(current_state, ConversationState.MAIN_MENU)

def is_valid_transition(from_state: ConversationState, to_state: ConversationState) -> bool:
    """Check if a state transition is valid"""
    return to_state in STATE_TRANSITIONS.values() or to_state == ConversationState.MAIN_MENU
