import base64
import os
import dotenv
import requests
from typing import Dict, Any
from pathlib import Path
from app.logger import logging
from dotenv import load_dotenv  
import ssl
import json
import urllib.request
dotenv.load_dotenv()

# Create a custom SSL context that ignores certificate verification
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# Configure requests to use the custom SSL context
requests.packages.urllib3.util.ssl_.DEFAULT_CIPHERS = 'ALL'
requests.packages.urllib3.util.ssl_.create_default_context = lambda: ssl_context

class B2Client:
    """Simplified B2 API client for file operations."""

    def __init__(self):
        self.api_url = None
        self.auth_token = None
        self.bucket_id = os.getenv("B2_BUCKET_ID")
        self.bucket_name = os.getenv("B2_BUCKET")
        self.key_id = os.getenv("B2_USER")
        self.key = os.getenv("B2_KEY")

        # Debug logging for environment variables
        logging.info(f"B2_BUCKET_ID: {'Set' if self.bucket_id else 'Not set'}")
        logging.info(f"B2_USER: {'Set' if self.key_id else 'Not set'}")
        logging.info(f"B2_KEY: {'Set' if self.key else 'Not set'}")

        # Authenticate on init
        self._authenticate()

    def _authenticate(self):
        """Authenticate with B2 API."""
        try:
            id_and_key = f'{self.key_id}:{self.key}'
            basic_auth_string = 'Basic ' + base64.b64encode(id_and_key.encode()).decode()
            headers = {
                'Authorization': basic_auth_string,
                'Content-Type': 'application/json'
            }

            logging.info("Authenticating with B2 API...")
            
            response = requests.get(
                'https://api.backblazeb2.com/b2api/v2/b2_authorize_account',
                headers=headers,
                verify=False  # Disable SSL verification
            )
            response.raise_for_status()
            auth_data = response.json()

            self.api_url = auth_data['apiUrl']
            self.auth_token = auth_data['authorizationToken']
            logging.info("Successfully authenticated with B2 API")
            
        except Exception as e:
            logging.error(f"Failed to authenticate with B2: {str(e)}")
            if hasattr(e, 'response'):
                logging.error(f"Response: {e.response.text}")
            raise

    def _get_upload_url(self) -> Dict[str, str]:
        """Get an upload URL and authorization token."""
        try:
            headers = {
                'Authorization': self.auth_token,
                'Content-Type': 'application/json'
            }

            logging.info("Getting B2 upload URL...")
            
            response = requests.post(
                f'{self.api_url}/b2api/v4/b2_get_upload_url',
                headers=headers,
                json={"bucketId": self.bucket_id},
                verify=False  # Disable SSL verification
            )
            response.raise_for_status()
            data = response.json()

            logging.info("Successfully got B2 upload URL")
            return {
                'uploadUrl': data['uploadUrl'],
                'authorizationToken': data['authorizationToken']
            }
            
        except Exception as e:
            logging.error(f"Failed to get B2 upload URL: {str(e)}")
            if hasattr(e, 'response'):
                logging.error(f"Response: {e.response.text}")
            raise

    def upload_file(self, file_path: Path, file_name: str) -> str:
        """Upload file to B2."""
        try:
            # Get upload URL and auth token
            upload_creds = self._get_upload_url()
            upload_url = upload_creds['uploadUrl']
            auth_token = upload_creds['authorizationToken']

            # Read file content
            with open(file_path, "rb") as f:
                file_content = f.read()
            
            file_size = len(file_content)
            logging.info(f"Uploading file: {file_name}, Size: {file_size} bytes")
            
            # Prepare headers for upload
            headers = {
                "Authorization": auth_token,
                "Content-Type": "application/octet-stream",
                "Content-Length": str(file_size),
                "X-Bz-File-Name": file_name,
                "X-Bz-Content-Sha1": "do_not_verify",
                "X-Bz-Info-Author": "zip_service"
            }
            
            # Upload file
            upload_response = requests.post(
                upload_url,  # Use the upload URL directly
                headers=headers,
                data=file_content,
                verify=False  # Disable SSL verification
            )
            
            if upload_response.status_code != 200:
                logging.error(f"Upload failed with status {upload_response.status_code}")
                logging.error(f"Response: {upload_response.text}")
                upload_response.raise_for_status()
            
            result = upload_response.json()
            logging.info(f"Successfully uploaded file {file_name} to B2")
            
            # Construct download URL
            download_url = f"https://f004.backblazeb2.com/file/{self.bucket_name}/{file_name}"
            logging.info(f"Download URL: {download_url}")
            
            return download_url
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to upload file {file_name} to B2: {str(e)}")
            if hasattr(e, 'response') and e.response:
                logging.error(f"Error response: {e.response.text}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error uploading file {file_name}: {str(e)}")
            raise
