from pydantic import BaseModel, HttpUrl
from typing import List, Optional


class VideoDownloadRequest(BaseModel):
    urls: List[HttpUrl]
    webhook_url: Optional[HttpUrl] = None
    unique_id: str
    model_type: str = "campaign"


class TaskResponse(BaseModel):
    task_id: str
    status: str


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    result: Optional[dict] = None
