# Simplified B2 Client

A simplified Backblaze B2 API client for file upload and management operations.

## Features

- **Simple Authentication**: Automatic authentication with B2 API
- **File Upload**: Upload files and get download URLs
- **File Deletion**: Delete files by name (handles multiple versions)
- **Clean API**: Easy-to-use functions for common operations

## Setup

1. Set the following environment variables:
   ```bash
   export B2_APPLICATION_KEY_ID="your_key_id"
   export B2_APPLICATION_KEY="your_application_key"
   export B2_BUCKET_ID="your_bucket_id"
   ```

2. Install dependencies:
   ```bash
   pip install requests
   ```

## Usage

### Basic Upload

```python
from pathlib import Path
from b2_client import upload_to_b2

# Upload a file
file_path = Path("my_video.mp4")
download_url = upload_to_b2(file_path, "videos/my_video.mp4")
print(f"Download URL: {download_url}")
```

### Basic Delete

```python
from b2_client import delete_from_b2

# Delete a file by name
success = delete_from_b2("videos/my_video.mp4")
if success:
    print("File deleted successfully!")
```

### Direct Client Usage

```python
from b2_client import get_b2_client

client = get_b2_client()

# Get upload URL
upload_data = client.get_upload_url()
print(f"Upload URL: {upload_data['uploadUrl']}")

# Upload file
download_url = client.upload_file(Path("file.txt"), "path/to/file.txt")
print(f"Download URL: {download_url}")
```

## Integration with Tasks

The simplified B2 client is now integrated into the `tasks.py` file, replacing the complex `b2sdk` implementation:

```python
# Old way (removed)
# from b2sdk.v2 import InMemoryAccountInfo, B2Api
# b2_api = get_b2_api()
# bucket = b2_api.get_bucket_by_name(bucket_name)

# New way (simplified)
from .b2_client import upload_to_b2
b2_url = upload_to_b2(zip_path)
```

## Benefits

1. **Simplified Code**: Removed complex SDK dependencies
2. **Better Error Handling**: Clear error messages and exceptions
3. **Easier Maintenance**: Less code to maintain and debug
4. **Direct API Access**: Uses B2 REST API directly
5. **Flexible**: Easy to extend with additional B2 operations

## API Reference

### Functions

- `upload_to_b2(file_path: Path, file_name: Optional[str] = None) -> str`
  - Uploads a file to B2 and returns the download URL
  - If `file_name` is not provided, uses `videos/{filename}`

- `delete_from_b2(file_name: str) -> bool`
  - Deletes all versions of a file by name
  - Returns `True` if successful, `False` otherwise

- `get_b2_client() -> B2Client`
  - Returns a singleton B2Client instance

### B2Client Class

- `get_upload_url() -> Dict[str, Any]`
  - Gets upload URL and authorization token for B2 bucket

- `upload_file(file_path: Path, file_name: str) -> str`
  - Uploads file and returns download URL

- `delete_file_by_name(file_name: str) -> bool`
  - Deletes all versions of a file by name 