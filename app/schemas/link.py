from pydantic import BaseModel, HttpUrl, Field
from datetime import datetime
from typing import Optional

class LinkBase(BaseModel):
    original_url: HttpUrl
    expires_at: Optional[datetime] = None

class LinkCreate(LinkBase):
    custom_alias: Optional[str] = Field(
        None, 
        min_length=3, 
        max_length=50
    )
class LinkResponse(LinkBase):
    id: int
    short_code: str
    created_at: datetime
    clicks: int
    last_used_at: Optional[datetime] = None
    user_id: Optional[int] = None

    class Config:
        from_attributes = True

class LinkStats(BaseModel):
    short_code: str
    original_url: str
    created_at: datetime
    clicks: int
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class LinkUpdate(BaseModel):
    original_url: HttpUrl

class LinkSearchResult(BaseModel):
    short_code: str
    short_url: str
    created_at: datetime

    class Config:
        from_attributes = True