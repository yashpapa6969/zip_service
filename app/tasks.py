import tempfile
from types import NoneType
import zipfile
from pathlib import Path
from typing import List, Optional
import httpx
import asyncio
from app.celery_app import celery_app
from app.b2_client import B2Client
from app.logger import logging


@celery_app.task(bind=True)
def download_and_upload_videos(
    self, urls: List[str], webhook_url: Optional[str] = None,unique_id: str = None,type=None
):
    """Download videos from URLs, zip them, upload to B2, and call webhook."""
    try:
        logging.info(f"Task {self.request.id}: Starting download for URLs: {urls}")
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            download_dir = temp_path / "downloads"
            download_dir.mkdir()

            # Download videos
            downloaded_files = asyncio.run(download_videos(urls, download_dir))

            # Check download results
            if not downloaded_files:
                failed_count = len(urls)
                error_msg = f"No videos were successfully downloaded (Failed: {failed_count}/{len(urls)})"
                logging.error(f"Task {self.request.id}: {error_msg}")
                raise ValueError(error_msg)

            # Continue with successful downloads
            logging.info(
                f"Task {self.request.id}: Successfully downloaded {len(downloaded_files)}/{len(urls)} files. "
                "Creating zip."
            )
            zip_path = temp_path / f"{unique_id}.zip"
            create_zip(downloaded_files, zip_path)

            # Verify zip file
            if not zip_path.exists() or zip_path.stat().st_size == 0:
                raise ValueError("Created zip file is empty or does not exist")

            logging.info(f"Task {self.request.id}: Uploading zip to B2.")
            b2_url = B2Client().upload_file(zip_path, f"{unique_id}.zip")
    
            result = {
                "unique_id": unique_id,
                "type": type,
                "status": "completed",
                "download_url": b2_url,
                "file_count": len(downloaded_files),
                "failed_count": len(urls) - len(downloaded_files)
            }

            if webhook_url:
                logging.info(f"Task {self.request.id}: Calling webhook {webhook_url}.")
                call_webhook(webhook_url, {"task_id": self.request.id, **result})

            logging.info(f"Task {self.request.id}: Task completed successfully.")
            return result

    except Exception as e:
        logging.error(f"Error in download_and_upload_videos: {e}")
        raise


async def download_videos(urls: List[str], download_dir: Path) -> List[Path]:
    """Download videos in parallel batches using httpx."""
    downloaded_files = []
    logging.info(f"Starting download of {len(urls)} videos to {download_dir}")

    async def download_video(url: str) -> Optional[Path]:
        try:
            logging.info(f"Attempting to download video from: {url}")
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                head_response = await client.head(url)
                content_type = head_response.headers.get('content-type', '')
                content_length = head_response.headers.get('content-length', 'unknown')
                logging.info(f"URL headers - Content-Type: {content_type}, Size: {content_length} bytes")

                # Get the actual content
                response = await client.get(url)
                response.raise_for_status()

                if not response.content:
                    logging.error(f"No content received from {url}")
                    return None

                filename = url.split("/")[-1]
                if not filename.endswith((".mp4", ".MP4")):
                    filename += ".mp4"

                file_path = download_dir / filename
                
                # Log the file size before writing
                content_size = len(response.content)
                logging.info(f"Received {content_size} bytes for {filename}")

                with open(file_path, "wb") as f:
                    f.write(response.content)

                # Verify the file was written correctly
                if file_path.exists():
                    file_size = file_path.stat().st_size
                    if file_size > 0:
                        logging.info(f"Successfully downloaded {filename} ({file_size} bytes)")
                        return file_path
                    else:
                        logging.error(f"File was created but is empty: {filename}")
                        return None
                else:
                    logging.error(f"Failed to create file: {filename}")
                    return None

        except httpx.TimeoutException as e:
            logging.error(f"Timeout downloading {url}: {e}")
            return None
        except httpx.HTTPStatusError as e:
            logging.error(f"HTTP error downloading {url}: {e.response.status_code} - {e}")
            return None
        except httpx.RequestError as e:
            logging.error(f"Request error downloading {url}: {e}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error downloading {url}: {e}")
            return None

    batch_size = 4
    for i in range(0, len(urls), batch_size):
        batch = urls[i : i + batch_size]
        logging.info(f"Processing batch {i//batch_size + 1} of {(len(urls) + batch_size - 1)//batch_size}")
        try:
            results = await asyncio.gather(
                *[download_video(url) for url in batch],
                return_exceptions=False
            )
            successful_downloads = [f for f in results if f is not None]
            logging.info(f"Batch completed. Successfully downloaded: {len(successful_downloads)}/{len(batch)}")
            downloaded_files.extend(successful_downloads)
        except Exception as e:
            logging.error(f"Error processing batch: {e}")

    logging.info(f"Download complete. Total successful downloads: {len(downloaded_files)}/{len(urls)}")
    return downloaded_files


def create_zip(files: List[Path], zip_path: Path) -> None:
    """Create a zip file from the downloaded videos."""
    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for file_path in files:
                zipf.write(file_path, file_path.name)
        logging.info(f"Created zip file at {zip_path} with {len(files)} files.")
    except Exception as e:
        logging.error(f"Failed to create zip file at {zip_path}: {e}")
        raise


def call_webhook(webhook_url: str, data: dict) -> None:
    """Call the webhook with the result data."""
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(webhook_url, json=data)
            response.raise_for_status()
        logging.info(f"Successfully called webhook {webhook_url}.")
    except Exception as e:
        logging.error(f"Failed to call webhook {webhook_url}: {e}")
        raise
