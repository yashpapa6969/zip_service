from fastapi import FastAPI
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from app.tasks import download_and_upload_videos
from app.models import VideoDownloadRequest, TaskResponse
from app.logger import logging

load_dotenv()


app = FastAPI(title="Video Download Service", version="1.0.0")

@app.post("/download-videos", response_model=TaskResponse)
async def download_videos(request: VideoDownloadRequest):
    """
    Submit video URLs for download, zip, and upload to Backblaze B2.
    """
    logging.info(
        f"Received download request for URLs: {request.urls} "
        f"with webhook: {request.webhook_url}"
    )
    urls = [str(url) for url in request.urls]
    webhook_url = str(request.webhook_url) if request.webhook_url else None
    unique_id = request.unique_id 
    model_type = request.model_type
    if not unique_id:
        ValueError("no unique id provided")
    try:
        download_and_upload_videos.apply_async(args=[urls, webhook_url, unique_id, model_type])
        logging.info("Task submitted to Celery queue.")
        return JSONResponse(content={"success": True, "status": "pending"})
    except Exception as e:
        logging.error(f"Failed to submit task: {e}")
        return JSONResponse(
            content={"success": False, "status": "error", "detail": str(e)},
            status_code=500,
        )


@app.get("/health")
async def health_check():
    logging.info("Health check endpoint called.")
    return {"status": "healthy"}
