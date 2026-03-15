from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models.link import Link
from app.schemas.link import LinkCreate, LinkUpdate
from datetime import datetime, timedelta, timezone
import random
import string
from typing import Optional, List

def generate_short_code(length: int = 6) -> str:
    chars = string.ascii_letters + string.digits
    return ''.join(random.choices(chars, k=length))

def get_link_by_code(db: Session, short_code: str) -> Optional[Link]:
    return db.query(Link).filter(Link.short_code == short_code).first()

def get_link_by_original_url(db: Session, original_url: str) -> List[Link]:
    return db.query(Link).filter(Link.original_url == original_url.strip()).all()

def create_link(
    db: Session, 
    link_data: LinkCreate, 
    user_id: Optional[int] = None
) -> Link:
    
    if link_data.custom_alias:
        short_code = link_data.custom_alias
        if get_link_by_code(db, short_code):
            raise ValueError("Alias already exists")
    else:
        while True:
            short_code = generate_short_code()
            if not get_link_by_code(db, short_code):
                break
    
    db_link = Link(
        short_code=short_code,
        original_url=str(link_data.original_url),  # HttpUrl в строку
        expires_at=link_data.expires_at,
        user_id=user_id
    )
    
    db.add(db_link)
    db.commit()
    db.refresh(db_link)
    return db_link

def update_link(
    db: Session, 
    link: Link, 
    link_data: LinkUpdate
) -> Link:
    link.original_url = str(link_data.original_url)
    db.commit()
    db.refresh(link)
    return link

def delete_link(db: Session, link: Link) -> None:
    db.delete(link)
    db.commit()

def increment_clicks(db: Session, link: Link) -> None:
    link.clicks += 1
    link.last_used_at = datetime.utcnow()
    db.commit()

def get_links_by_user(db: Session, user_id: int) -> List[Link]:
    return db.query(Link).filter(Link.user_id == user_id).all()

def delete_expired_links(db: Session) -> int:
    now = datetime.utcnow()
    expired = db.query(Link).filter(Link.expires_at < now).all()
    count = len(expired)
    for link in expired:
        db.delete(link)
    db.commit()
    return count

def delete_unused_links(db: Session, days: int) -> int:
    threshold = datetime.now(timezone.utc) - timedelta(days=days)
    unused = db.query(Link).filter(
        Link.last_used_at.isnot(None),
        Link.last_used_at < threshold
    ).all()
    count = len(unused)
    for link in unused:
        db.delete(link)
    db.commit()
    return count