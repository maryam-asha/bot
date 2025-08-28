from typing import Dict, List, Optional, Any, Union
import re
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)

class FormAttribute:
    def __init__(self, data: Dict[str, Any]):
        self.id = data.get('id')
        self.type_code = data.get('type_code')
        self.component_type = data.get('component_type')
        self.component_characters_type = data.get('component_characters_type')
        self.code = data.get('code')
        self.order = data.get('order')
        self.name = data.get('name')
        self.hint = data.get('hint')
        self.required = bool(data.get('required', 0))
        raw_extra = data.get('extra', {})
        if isinstance(raw_extra, dict):
            self.extra = raw_extra
        else:
            logger.warning(f"[FormAttribute] Unexpected 'extra' type for attribute '{self.name}': {type(raw_extra).__name__}. Defaulting to empty dict.")
            self.extra = {}
        self.options = data.get('options', [])
        self.example = data.get('example', '')
        self.ar = data.get('ar', {})
        self.en = data.get('en', {})
        self.selected_values = []  # Store multiple selected values
        
    def validate(self, value: str) -> tuple[bool, str]:
        """Validate the input value based on type_code and extra constraints."""
        if not value and self.required:
            return False, "هذا الحقل مطلوب."

        if not value:
            return True, ""  

        if self.type_code in ['text', 'text_area']:
            min_length = self.extra.get('min_length')
            max_length = self.extra.get('max_length')
         
            try:
                if min_length is not None and str(min_length).strip() != '':
                    min_length_int = int(min_length)
                    if len(value) < min_length_int:
                        return False, f"النص يجب أن يكون على الأقل {min_length_int} حرفًا."
            except Exception:
                pass
            
            try:
                if max_length is not None and str(max_length).strip() != '':
                    max_length_int = int(max_length)
                    if len(value) > max_length_int:
                        return False, f"النص يجب ألا يتجاوز {max_length_int} حرفًا."
            except Exception:
                pass
      
        if self.type_code == 'text':
            return True, ""
        
        elif self.type_code == 'text_area':
            return True, ""
        
        elif self.type_code == 'number':
            digit_num = int(self.extra.get('digit_num', 10))
            if not re.match(r'^\d+$', value) or len(value) > digit_num:
                return False, f"يرجى إدخال رقم مكون من {digit_num} أرقام على الأكثر."
            return True, ""
        
        elif self.type_code == 'money':
            if not re.match(r'^\d+(\.\d{1,2})?$', value):
                return False, "يرجى إدخال مبلغ صحيح"
            return True, ""
        
        elif self.type_code == 'date':
            try:
                input_date = datetime.strptime(value, '%Y-%m-%d').date()
                min_date_str = self.extra.get('min_date', '1900-01-01')
                max_date_str = self.extra.get('max_date', '2100-12-31')
                min_date = datetime.strptime(min_date_str, '%Y-%m-%d').date()
                max_date = datetime.strptime(max_date_str, '%Y-%m-%d').date()
                if not (min_date <= input_date <= max_date):
                    return False, f"التاريخ يجب أن يكون بين {min_date_str} و{max_date_str}."
                return True, ""
            except ValueError:
                return False, f"يرجى إدخال تاريخ بالصيغة yyyy-mm-dd. مثال: التاريخ يجب أن يكون بين {self.extra.get('min_date', '1900-01-01')} و{self.extra.get('max_date', '2100-12-31')}."
    
        elif self.type_code == 'time':
            logger.info(f"Validating time field: value={value}, extra={self.extra}")
            try:
                # Parse input time (HH:MM format)
                input_time = datetime.strptime(value, '%H:%M').time()
                
                # Get min_time and max_time from extra (HH:MM:SS format)
                min_time_str = self.extra.get('min_time', '00:00:00')
                max_time_str = self.extra.get('max_time', '23:59:59')
                
                # Parse min_time and max_time as HH:MM:SS
                min_time = datetime.strptime(min_time_str, '%H:%M:%S').time()
                max_time = datetime.strptime(max_time_str, '%H:%M:%S').time()
                
                # Log the parsed values for debugging
                logger.info(f"Parsed input_time: {input_time}, min_time: {min_time}, max_time: {max_time}")
                
                # Check if input_time is within the valid range
                if not (min_time <= input_time <= max_time):
                    period_min = self.extra.get('period_min_time', min_time_str[:5])  
                    period_max = self.extra.get('period_max_time', max_time_str[:5])  
                    return False, (
                        f"الوقت يجب أن يكون بين {period_min} و{period_max}.\n"
                        f"يرجى إدخال وقت بالصيغة hh:mm"
                    )
                
                return True, ""

            except ValueError:
                return False, "يرجى إدخال وقت بالصيغة hh:mm."
        
        elif self.type_code == 'mobile':
            cleaned_value = value.replace(' ', '').replace('-', '')
            if not re.match(r'^(\+963|09)[0-9]{8,9}$', cleaned_value):
                return False, "يرجى إدخال رقم موبايل صحيح (مثال: +9639xxxxxxxx)."
            return True, ""
        
        elif self.type_code == 'phone':
            if not re.match(r'^\+?\d{7,15}$', value):
                return False, "يرجى إدخال رقم هاتف صحيح."
            return True, ""
        
        elif self.type_code == 'switch':
            if str(value).lower() not in ['true', 'false']:
                return False, "يرجى اختيار نعم أو لا فقط."
            return True, ""
        
        elif self.type_code in ['options', 'autocomplete']:
            logger.debug(f"Options for {self.name}: {[option['id'] for option in self.options]}")
            try:
                return any(option['id'] == int(value) for option in self.options), "يرجى اختيار خيار صالح."
            except ValueError:
                logger.debug(f"Value {value} is not a valid integer for {self.name}")
                return False, "يرجى اختيار خيار صالح."
        
        elif self.type_code in ['multiple_autocomplete', 'multi_options']:
            if not value:
                return not self.required, "يرجى اختيار خيار واحد على الأقل إذا كان الحقل مطلوبًا."
            selected_values = str(value).split(',')
            try:
                return all(any(option['id'] == int(val.strip()) for option in self.options) for val in selected_values), "يرجى اختيار خيارات صالحة من القائمة."
            except ValueError:
                logger.debug(f"Invalid integer in multiple selections: {value}")
                return False, "يرجى اختيار خيارات صالحة من القائمة."
        
        return True, ""
       
    async def get_autocomplete_options(self, api_service) -> List[Dict[str, Any]]:
        if self.type_code not in ['autocomplete', 'multiple_autocomplete'] or not self.extra:
            return self.options
            
        try:
            resource = self.extra.get('resource')
            if not resource:
                return self.options
            response = await api_service.get_autocomplete_options(resource)
            data = response.get('data', [])
            options = [{'id': item['value'], 'name': item['text']} for item in data]
            self.options = options
            return options
        except Exception as e:
            logger.error(f"Error fetching autocomplete options: {str(e)}")
            return self.options
            
    def add_selected_value(self, value: str) -> bool:
        if self.type_code not in ['multiple_autocomplete', 'multi_options']:
            return False
        if value not in self.selected_values:
            self.selected_values.append(value)
            return True
        return False
        
    def remove_selected_value(self, value: str) -> bool:
        if self.type_code not in ['multiple_autocomplete', 'multi_options']:
            return False
        if value in self.selected_values:
            self.selected_values.remove(value)
            return True
        return False
        
    def get_selected_values(self) -> List[str]:
        return self.selected_values

class FormGroup:
    def __init__(self, data: Dict[str, Any]):
        self.id = data.get('id')
        self.display_group_id = data.get('display_group_id')
        self.order = data.get('order')
        self.name = data.get('name')
        self.attributes = [FormAttribute(attr) for attr in data.get('attributes', [])]
        self.attributes.sort(key=lambda x: x.order)

class FormDocument:
    def __init__(self, data: Dict[str, Any]):
        self.id = data.get('id')
        self.documents_type_id = data.get('documents_type_id')
        self.documents_type_name = data.get('documents_type_name')
        self.types = data.get('types', [])
        self.is_multi = bool(data.get('is_multi', 0))
        self.required = bool(data.get('required', 0))
        self.accept_extension = data.get('accept_extension')

class DynamicForm:
    def __init__(self, form_data: Dict[str, Any]):
        logger.debug(f"Form data received: {json.dumps(form_data, ensure_ascii=False)}")
        self.groups = [FormGroup(group) for group in form_data.get('groups', [])]
        self.documents = [FormDocument(doc) for doc in form_data.get('documents', [])]
        self.form_version_id = form_data.get('form_version_id')
        self.full_files_size = form_data.get('full_files_size')
        self.groups.sort(key=lambda x: x.order)
        self.data: Dict[str, Any] = {}
        self.document_data: Dict[str, List[str]] = {}
        self.errors: Dict[str, str] = {}

    def get_field_by_id(self, field_id):
        """Find a field object by its ID."""
        # Search through attributes in groups
        for group in self.groups:
            for attr in group.attributes:
                if str(attr.id) == str(field_id):
                    return attr
        
        # Search through documents
        for doc in self.documents:
            if str(doc.id) == str(field_id):
                return doc
        
        return None
    def get_next_field(self, context=None) -> Optional[Union[FormAttribute, FormDocument]]:
        logger.debug("Getting next field")
        
        # Log current form state for debugging
        logger.debug(f"Current form data: {self.data}")
        logger.debug(f"Current document data: {self.document_data}")
        
        # Check if we're in a multi-file upload state
        if context and 'multi_upload_field_id' in context.user_data:
            multi_upload_field_id = context.user_data['multi_upload_field_id']
            for document in self.documents:
                if document.id == multi_upload_field_id and document.is_multi:
                    logger.debug(f"Continuing multi-upload for FormDocument ID {document.id}")
                    return document
        
        # Normal field selection logic: attributes first, then documents
        for group in self.groups:
            for attribute in group.attributes:
                if str(attribute.id) not in self.data:
                    logger.debug(f"Returning FormAttribute ID {attribute.id} ({attribute.name})")
                    return attribute
        
        for document in self.documents:
            if document.id not in self.document_data or (document.is_multi and context and 'multi_upload_field_id' not in context.user_data):
                logger.debug(f"Returning FormDocument ID {document.id} ({document.documents_type_name})")
                if document.is_multi:
                    context.user_data['multi_upload_field_id'] = document.id
                return document
        
        logger.debug("No next field found")
        if context and 'multi_upload_field_id' in context.user_data:
            del context.user_data['multi_upload_field_id']
        return None

    def set_field_value(self, field_code: str, value: str) -> bool:
        for group in self.groups:
            for attribute in group.attributes:
                if attribute.code == field_code and str(attribute.id) not in self.data:
                    is_valid, error = attribute.validate(value)
                    if is_valid:
                        self.data[str(attribute.id)] = value
                        if str(attribute.id) in self.errors:
                            del self.errors[str(attribute.id)]
                        logger.debug(f"Set field value: {field_code} = {value}")
                        return True
                    else:
                        self.errors[str(attribute.id)] = error
                        logger.debug(f"Validation failed for {field_code}: {error}")
                        return False
        logger.debug(f"Field {field_code} not found or already set")
        return False
        
    def skip_field(self, field_id: str) -> bool:
        """Mark a non-required field as skipped by setting an empty value."""
        for group in self.groups:
            for attribute in group.attributes:
                if str(attribute.id) == field_id and not attribute.required:
                    self.data[field_id] = ""
                    logger.debug(f"Skipped FormAttribute field ID {field_id}")
                    return True
        for document in self.documents:
            if str(document.id) == field_id and not document.required:
                self.document_data[document.id] = []
                logger.debug(f"Skipped FormDocument field ID {field_id}")
                return True
        logger.debug(f"Failed to skip field ID {field_id}")
        return False

    def set_document(self, document_id: int, file_ids: List[str]) -> bool:
        if not any(doc.id == document_id for doc in self.documents):
            logger.debug(f"Document ID {document_id} not found")
            return False
        self.document_data[document_id] = file_ids
        logger.debug(f"Set document ID {document_id} with file IDs {file_ids}")
        return True
        
    def is_complete(self) -> bool:
        for group in self.groups:
            for attribute in group.attributes:
                if attribute.required and str(attribute.id) not in self.data:
                    logger.debug(f"Required field ID {attribute.id} not filled")
                    return False
        for document in self.documents:
            if document.required and document.id not in self.document_data:
                logger.debug(f"Required document ID {document.id} not filled")
                return False
        logger.debug("Form is complete")
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        documents = []
        for doc_id, file_ids in self.document_data.items():
            document = next((doc for doc in self.documents if doc.id == doc_id), None)
            if document:
                documents.append({
                    'id': doc_id,
                    'documents_type_id': document.documents_type_id,
                    'file_ids': [{'file_id': file_id} for file_id in file_ids]
                })
        groups_data = []
        for group in self.groups:
            group_data = {
                'id': group.id,
                'display_group_id': group.display_group_id,
                'order': group.order,
                'name': group.name,
                'attributes': []
            }
            for attribute in group.attributes:
                attribute_data = {
                    'id': attribute.id,
                    'type_code': attribute.type_code,
                    'component_type': attribute.component_type,
                    'component_characters_type': attribute.component_characters_type,
                    'code': attribute.code,
                    'order': attribute.order,
                    'name': attribute.name,
                    'hint': attribute.hint,
                    'required': attribute.required,
                    'extra': attribute.extra,
                    'options': attribute.options,
                    'example': attribute.example,
                    'ar': attribute.ar,
                    'en': attribute.en
                }
                group_data['attributes'].append(attribute_data)
            groups_data.append(group_data)
        return {
            'form_version_id': self.form_version_id,
            'data': self.data,
            'documents': documents,
            'groups': groups_data
        }
        