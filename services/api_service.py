import logging
import httpx
from typing import Dict, Any, Optional, List, Tuple
import asyncio
import json
from config.settings import settings
logger = logging.getLogger(__name__)

class ApiService:
    def __init__(self):
        self.bearer_token = None
        self.token_type = "Bearer"
        self.headers = {
            "Accept": "application/json",
            "os-type": "Telegram",
            "Authorization": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiIxIiwianRpIjoiMDk3NDVjZGE4Y2Q5YmI5NjBjZmIxNjg2NDBiZGRiNWRlNmYzMjA0MWNkODk4NDNlMDAxNWE4NWQ0MWE1OTVjZTRkZjc5Zjk2MWQyYTMwZDYiLCJpYXQiOjE3NTYxMDkyNzYuMDg2MDM3LCJuYmYiOjE3NTYxMDkyNzYuMDg2MDQxLCJleHAiOjE3ODc2NDUyNzYuMDY3MjU3LCJzdWIiOiIyMyIsInNjb3BlcyI6W119.dmbzXBsiNkdgoH51hBFFdKa9O1swrA3KaoU2Pj-qzjPJV__mKUGDsT3T9lGa8dlu04FYJ4_5bcUQaQkaErrU8YsTJB6QSK9tTbT0psNtcZNOWEMwg7L4YnnlT6oRiYy7n3-4pSm-mb7yCy2VN9A-wCVOVXn8Gr-LJv6ibscrITHaF1g-KsBPb5X4ic4HPwAzBlQ22Jpfy8tIwPbuus8N6vcmYguQCN25zsVrNs9lrHSqSpKFiRE-O2X2yxdyUBQmmxd8dQuLKl14JEBSxbFmbLkauoMvYo3JpV6lx1zEYdd8LYG78daJw_n6mkmOgR3IPz-WvyytLCPgGeiOhEAlUPxsqUbBdVDV0JYDoBVbuCEu4imjdgeCaVNKDo6l8FiScmXXsER2XW7DijDkHxHj9zaua5KQESLhd2FDza77upDKI42WQ4qquacLqisyx5QR4uSGt7BtN4vQc6pIE8IgzXrxUUghkT-ls2KoUXrC6XE-z20C5sOC49BRs9KU21Ijv_UjyvKbZ82G-jrevmaWn_aq8tmOCGPXzgzTJW_l5AIBst0lgmXck79uiBgYgs499nUfbIkEECPsJch5UeKzVIXs_AHcbPOh1eMML3t0WpnMiaHjAQDIT5asn5LUy7L2v6AQZ2PhVh-9Ze4tcbO8m7iepJ5KeDiGaxuJJhIjxi8"
        }
        self.location_id = None
        # self.initialize_urls()


    async def initialize_urls(self):
        try:
            project_settings = await self.project_setting()
            if not isinstance(project_settings, dict):
                raise ValueError("Project settings must be a dictionary")
    
            settings.base_url = project_settings.get("BASE_URL", settings.base_url)
            settings.image_base_url = settings.base_url.rstrip("api")
            settings.country_code = project_settings.get("COUNTRY_CODE", settings.country_code)
            settings.username_hint = project_settings.get("USERNAME_HINT", settings.username_hint)
            settings.mobile_length = project_settings.get("MOBILE_LENGTH", settings.mobile_length)
            settings.mobile_code = project_settings.get("MOBILE_CODE", settings.mobile_code)

            return project_settings
        except Exception as e:
            settings.base_url = "https://yourvoice.sy/api"
            settings.image_base_url = "https://yourvoice.sy/"
            settings.country_code = "963"
            settings.username_hint = "## ### ####"
            settings.mobile_length = 8
            settings.mobile_code = "09"
            return {
                "BASE_URL": settings.base_url,
                "COUNTRY_CODE": settings.country_code,
                "USERNAME_HINT": settings.username_hint,
                "MOBILE_LENGTH": settings.mobile_length,
                "MOBILE_CODE": settings.mobile_code
            }



    def update_token(self, access_token: str, token_type: str = "Bearer"):
        self.bearer_token = access_token
        self.token_type = token_type
        self.headers["Authorization"] = f"{self.token_type} {self.bearer_token}"
        logger.info("Authorization token updated successfully.", self.headers)

    async def get_service_categories(self, request_type_id: int, side_id: int) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{settings.base_url}/autocomplete/complaint-service-categories-api",
                    headers=self.headers,
                    params={
                        'location_id': self.location_id,
                        'side_id': side_id,
                        'request_type_id': request_type_id,
                    },
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Error fetching service categories: {str(e)}")
                raise

    async def get_other_request_type_subjects(self, request_type_id: int, side_id: int) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{settings.base_url}/complaints/other-request-types-subjects",
                    headers=self.headers,
                    params={
                        'location_id': self.location_id,
                        'side_id': side_id,
                        'request_type_id': request_type_id,
                    },
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Error fetching other request type subjects: {str(e)}")
                raise

    async def get_services_for_category(self, category_id: int, request_type_id: int) -> Dict[str, Any]:
        logger.info(f"Fetching category_id: {category_id}")
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{settings.base_url}/autocomplete/complaint-services-api",
                    params={
                        "complaint_service_categorie_id": category_id,
                        "request_type_id": request_type_id,
                    },
                    headers=self.headers
                )
                response.raise_for_status()
                logger.info(f"Services fetched successfully for category {category_id}: {response.json()}")
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Error fetching services for category {category_id}: {str(e)}")
                raise

    async def get_parent_sides(self) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{settings.base_url}/complaints/parent-sides?location_id={self.location_id}", headers=self.headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Error fetching parent sides: {str(e)}")
                raise

    async def get_side_children(self, parent_id: int) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{settings.base_url}/complaints/children-sides/{parent_id}",
                                        params={'location_id': self.location_id},
                                        headers=self.headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Error fetching side children for {parent_id}: {str(e)}")
                raise

    async def get_request_type(self, side_id: int) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{settings.base_url}/complaints/request-types",
                                        params={'location_id': self.location_id, 'side_id': side_id},
                                        headers=self.headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Error fetching request type: {str(e)}")
                raise

    async def get_request_type_subjects(self, request_type_id: int, side_id: int) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{settings.base_url}/complaints/request-types-subjects",
                                        params={'location_id': self.location_id, 'side_id': side_id, 'request_type_id': request_type_id},
                                        headers=self.headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Error fetching request type subjects: {str(e)}")
                raise

    async def get_form_data(self, request_type_id: int, request_subject_id: int, other_subject_id: Optional[int] = None, complaint_service_id: Optional[int] = None, side_id: Optional[int] = None) -> Dict[str, Any]:
        logger.info(f"Calling form request with request_type_id={request_type_id}, request_subject_id={request_subject_id}, other_subject_id={other_subject_id}, complaint_service_id={complaint_service_id}, side_id={side_id},location_id ={self.location_id}")
        # logger.info(f"Calling form request {other_subject_id}, {request_type_id}, {request_subject_id}, {other_subject_id}, {complaint_service_id}, {side_id}")
        async with httpx.AsyncClient() as client:
            try:
                params = {
                    'side_id': side_id,
                    'location_id': self.location_id,
                    'request_type_id': request_type_id,
                    'complaint_subject_id': request_subject_id
                }
                if other_subject_id:
                    params['other_subject_id'] = other_subject_id
                if complaint_service_id:
                    params['complaint_service_id'] = complaint_service_id
                
                logger.info(f"Calling form request {params} ")

                response = await client.post(
                    f"{settings.base_url}/complaints/form-for-request",
                    headers=self.headers,
                    json=params
                )
                response.raise_for_status()
                logger.info(f"response of api  {response.json()} ")
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Error fetching form data: {str(e)}")
                raise

    async def upload_file(self, file_data: bytes, file_name: str) -> dict:
        logger.info(f"API for file {file_name}: {file_data}")
        async with httpx.AsyncClient() as client:
            try:
                files = {'file': (file_name, bytes(file_data))}
                # files = {'file': (file_name, file_data)}
                response = await client.post(
                    f"{settings.base_url}/file-upload?uploader=form-bulider-file",
                    headers=self.headers,
                    files=files
                )
                response.raise_for_status()
                response_data = response.json()
                logger.info(f"API response for file {file_name}: {response}")
                if isinstance(response_data, int):
                    file_id = str(response_data)
                    mime_type = 'application/octet-stream'
                    logger.debug(f"Received integer file_id: {file_id}")
                elif isinstance(response_data, dict):
                    file_id = response_data.get('file_id')
                    mime_type = response_data.get('mime_type', 'application/octet-stream')
                    if not file_id:
                        logger.error(f"Invalid dictionary response: Missing file_id, got {response_data}")
                        raise ValueError(f"Invalid response: Missing file_id in dictionary response")
                    file_id = str(file_id)
                    logger.debug(f"Received dictionary response with file_id: {file_id}, mime_type: {mime_type}")
                else:
                    logger.error(f"Unexpected response type: {type(response_data)}, value: {response_data}")
                    raise ValueError(f"Invalid response: Expected integer or dictionary, got {type(response_data)}")

                return {'file_id': file_id, 'mime_type': mime_type}
            except httpx.HTTPStatusError as e:
                logger.error(f"Error uploading file {file_name}: {str(e)}")
                raise
            except ValueError as e:
                logger.error(f"Error parsing response for file {file_name}: {str(e)}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error uploading file {file_name}: {str(e)}")
                raise

    async def submit_complaint(self, form_data: Dict[str, Any]) -> Dict[str, Any]:
        
        request_data = {
            'request_type_id': form_data.get('request_type_id'),
            'complaint_subject_id': form_data.get('complaint_subject_id'),
            'complaint_service_id': form_data.get('complaint_service_id'),
            'other_subject_id': form_data.get('other_subject_id'),
            'side_id': form_data.get('side_id'),
            'location_id': self.location_id,
            'form_version_id': form_data.get('form_version_id'),
            'info': [],
            'documents': [],
            'request_source': 'telegram_channel'
        }
        
        for attribute_id, value in form_data.get('data', {}).items():
            is_multi_select = False
            for group in form_data.get('groups', []):
                for attr in group.get('attributes', []):
                    if str(attr['id']) == attribute_id and attr['type_code'] in ['multi_options', 'multiple_autocomplete']:
                        is_multi_select = True
                        break
                if is_multi_select:
                    break
            
            if is_multi_select and value:
                values = [int(val.strip()) for val in value.split(',') if val.strip()]
                value_str = json.dumps(values)
                request_data['info'].append({
                    'attribute_id': int(attribute_id),
                    'values': value_str
                })
            else:
                value_str = str(value) if value is not None else ""
                request_data['info'].append({
                    'attribute_id': int(attribute_id),
                    'values': value_str
                })
            
        
        for doc in form_data.get('documents', []):
            if not isinstance(doc, dict):
                logger.error("Invalid document entry: %r", doc)
                continue

            raw_files = doc.get('file_ids', [])
            file_ids = []
            # handle JSON-encoded lists just in case
            if isinstance(raw_files, str):
                try:
                    raw_files = json.loads(raw_files)
                except json.JSONDecodeError:
                    raw_files = []

            for f in raw_files or []:
                if isinstance(f, str):
                    file_ids.append(f)
                elif isinstance(f, dict):
                    # try common keys
                    fid = f.get('file_id') or f.get('fileId') or f.get('id')
                    if fid:
                        file_ids.append(fid)

            if file_ids:
                request_data['documents'].append({
                    'form_version_document_type_id': doc.get('id'),
                    'files': file_ids
                })

        logger.info(f"Submitting complaint with data: {request_data}")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.base_url}/complaints/add-request",
                headers=self.headers,
                json=request_data
            )
            response.raise_for_status()
            logger.info(f"response from api add-request: {response.json()}")
            return response.json()


    async def get_autocomplete_options(self, resource: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{settings.base_url}/autocomplete/{resource}",
                    headers=self.headers
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Error fetching autocomplete options for {resource}: {str(e)}")
                raise

    async def get_user_requests(self) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{settings.base_url}/complaints/my-requests", headers=self.headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Error fetching user requests: {str(e)}")
                raise

    async def get_user_request_info(self, request_number: str) -> Dict[str, Any]:
        logger.info("Fetching details for request_number: %s", request_number)
        request_data = {'request_number': request_number}
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(f"{settings.base_url}/complaints/request-num-info", headers=self.headers, json=request_data)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Error fetching user request info for {request_number}: {str(e)}")
                raise

    async def request_otp(self, mobile: str) -> Dict[str, Any]:
        request_data = {"mobile": mobile}
        logger.info(f"Sending OTP request for mobile: {mobile}")
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{settings.base_url}/auth/login/otp/request",
                    json=request_data
                )
                response.raise_for_status()
                
                logger.info(f"Response status: {response.status_code}")
                logger.info(f"Response headers: {response.headers}")
                logger.info(f"Response content: '{response.text}'")
                
                if not response.text.strip():
                    logger.info("Empty response received, assuming OTP request was successful")
                    return {"success": True}
                
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Error fetching request otp: {str(e)}")
                raise
            except ValueError as e:
                logger.error(f"JSON parsing error: {str(e)}")
                if response.status_code == 200:
                    logger.info("Assuming OTP request was successful despite non-JSON response")
                    return {"success": True}
                raise

    async def login_otp(self, mobile: str, otp: str) -> Dict[str, Any]:
        request_data = {'mobile': mobile, 'otp': otp}
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(f"{settings.base_url}/auth/login/otp", json=request_data)
                response.raise_for_status()
                response_data = response.json()

                access_token = response_data.get("access_token")
                token_type = response_data.get("token_type", "Bearer")
                self.update_token(access_token, token_type)
                return {
                    "status": "success",
                    "access_token": access_token,
                    "token_type": token_type,
                }
            except httpx.HTTPStatusError as e:
                logger.error(f"Error fetching login otp: {str(e)}")
                raise

   
    async def project_setting(self, timeout=10, retries=3, backoff_factor=1) -> Dict[str, Any]:
        url = "https://automata4.app/api/project-settings?clientCode=MOC&applicationCode=YRV&version=1.1.2&osType=Android"
        async with httpx.AsyncClient(timeout=timeout) as client:
            for attempt in range(retries):
                try:
                    response = await client.get(url, headers=self.headers)
                    response.raise_for_status()
                    
                    if not response.text.strip():
                        raise ValueError("Empty response from project settings API")
                    
                    response_data = response.json()
                    
                    if not isinstance(response_data, dict) or 'data' not in response_data:
                        logger.error(f"Invalid response format: {response_data}")
                        raise ValueError("Project settings response missing 'data' key")
                    
                    return response_data['data']
                except (httpx.ReadTimeout, httpx.ConnectTimeout, httpx.HTTPStatusError) as e:
                    logger.warning(f"Attempt {attempt + 1}/{retries} failed: {str(e)}")
                    if attempt < retries - 1:
                        await asyncio.sleep(backoff_factor * (2 ** attempt))  # Exponential backoff
                    else:
                        logger.error(f"Failed to fetch project settings after {retries} attempts: {str(e)}")
                        raise
                except ValueError as e:
                    logger.error(f"JSON parsing error: {str(e)}")
                    raise

    async def user_info(self) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{settings.base_url}/user-info", headers=self.headers)
                response.raise_for_status()
                data = response.json()
                user_data = data.get("data", {})
                self.location_id = user_data.get("location_id")
                logger.info(f"location_id set to: {self.location_id}")
                return data
            except httpx.HTTPStatusError as e:
                logger.error(f"Error fetching user info: {str(e)}")
                raise