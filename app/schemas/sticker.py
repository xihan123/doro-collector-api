from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class StickerBase(BaseModel):
    description: str
    url: str
    md5: str
    doro_confidence: float = 0.0
    tags: List[str] = []
    width: Optional[int] = None
    height: Optional[int] = None
    file_size: Optional[int] = None


class StickerCreate(StickerBase):
    pass


class StickerUpdate(BaseModel):
    description: Optional[str] = None
    likes: Optional[int] = None
    dislikes: Optional[int] = None
    tags: Optional[List[str]] = None


class StickerResponse(StickerBase):
    id: str
    created_at: datetime
    likes: int = 0
    dislikes: int = 0

    class Config:
        from_attributes = True


class StickerPagination(BaseModel):
    total: int
    items: List[StickerResponse]
    page: int
    size: int
    pages: int


class UploadResponse(BaseModel):
    success: bool
    message: str
    sticker: Optional[StickerResponse] = None


class StickerDescriptionUpdate(BaseModel):
    description: str


class StickerTagsUpdate(BaseModel):
    tag_name: str