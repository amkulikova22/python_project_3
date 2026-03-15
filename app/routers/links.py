from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timezone
import os

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_current_active_user
from app.models.user import User
from app.models.link import Link
from app.schemas.link import LinkCreate, LinkResponse, LinkStats, LinkUpdate, LinkSearchResult
from app.services import link_service

router = APIRouter(prefix="/links", tags=["links"])

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

@router.post("/shorten", response_model=LinkResponse, status_code=201)
def create_short_link(
    link_data: LinkCreate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    try:
        new_link = link_service.create_link(
            db=db,
            link_data=link_data,
            user_id=current_user.id if current_user else None
        )
        return new_link
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

@router.get("/search", response_model=List[LinkSearchResult])
def search_links(
    original_url: str,
    db: Session = Depends(get_db)
):
    print(f"Search query repr: {repr(original_url)}")
    all_links = db.query(Link.original_url).all()
    db_urls = [url for (url,) in all_links]
    print("All DB URLs repr:", [repr(u) for u in db_urls])

    links = link_service.get_link_by_original_url(db, original_url)
    print(f"Found {len(links)} links")

    result = []
    for link in links:
        result.append({
            "short_code": link.short_code,
            "short_url": f"{BASE_URL}/links/{link.short_code}",
            "created_at": link.created_at
        })
    return result

@router.get("/{short_code}/stats", response_model=LinkStats)
def get_link_stats(
    short_code: str,
    db: Session = Depends(get_db)
):
    link = link_service.get_link_by_code(db, short_code)
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    return link

@router.put("/{short_code}", response_model=LinkResponse)
def update_link(
    short_code: str,
    link_data: LinkUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    link = link_service.get_link_by_code(db, short_code)
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    if link.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    updated_link = link_service.update_link(db, link, link_data)
    return updated_link

@router.delete("/{short_code}", status_code=204)
def delete_link(
    short_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    link = link_service.get_link_by_code(db, short_code)
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    if link.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    link_service.delete_link(db, link)
    return None

@router.get("/{short_code}")
def redirect_to_original(
    short_code: str,
    request: Request,
    db: Session = Depends(get_db)
):
    link = link_service.get_link_by_code(db, short_code)
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    if link.expires_at and link.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=404, detail="Link has expired")
    link_service.increment_clicks(db, link)
    return RedirectResponse(url=link.original_url, status_code=302)