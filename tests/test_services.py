import pytest
from app.services import link_service
from app.schemas.link import LinkCreate
from datetime import datetime, timedelta, timezone

def test_generate_short_code_length():
    code = link_service.generate_short_code()
    assert len(code) == 6
    assert all(c in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789" for c in code)

def test_create_link_with_custom_alias(db_session):
    data = LinkCreate(original_url="https://example.com", custom_alias="test")
    link = link_service.create_link(db_session, data, user_id=None)
    assert link.short_code == "test"
    assert link.original_url == "https://example.com/"

def test_create_link_duplicate_alias_raises(db_session):
    data = LinkCreate(original_url="https://example.com", custom_alias="test")
    link_service.create_link(db_session, data, user_id=None)
    with pytest.raises(ValueError, match="Alias already exists"):
        link_service.create_link(db_session, data, user_id=None)

def test_increment_clicks(db_session):
    data = LinkCreate(original_url="https://example.com")
    link = link_service.create_link(db_session, data, user_id=None)
    assert link.clicks == 0
    assert link.last_used_at is None
    link_service.increment_clicks(db_session, link)
    assert link.clicks == 1
    assert link.last_used_at is not None

def test_delete_expired_links(db_session):
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    expired_data = LinkCreate(
        original_url="https://expired.com",
        expires_at=now - timedelta(days=1)
    )
    expired_link = link_service.create_link(db_session, expired_data, user_id=None)
    valid_data = LinkCreate(
        original_url="https://valid.com",
        expires_at=now + timedelta(days=1)
    )
    valid_link = link_service.create_link(db_session, valid_data, user_id=None)
    count = link_service.delete_expired_links(db_session)
    assert count == 1
    assert link_service.get_link_by_code(db_session, expired_link.short_code) is None
    assert link_service.get_link_by_code(db_session, valid_link.short_code) is not None

def test_delete_unused_links(db_session):
    now = datetime.now(timezone.utc)
    unused = LinkCreate(original_url="https://example.com")
    link_unused = link_service.create_link(db_session, unused, user_id=None)
    link_unused.last_used_at = now - timedelta(days=31)
    db_session.commit()
    used = LinkCreate(original_url="https://example.com")
    link_used = link_service.create_link(db_session, used, user_id=None)
    link_used.last_used_at = now - timedelta(days=1)
    db_session.commit()
    count = link_service.delete_unused_links(db_session, days=30)
    assert count == 1
    assert link_service.get_link_by_code(db_session, link_unused.short_code) is None
    assert link_service.get_link_by_code(db_session, link_used.short_code) is not None

def test_get_links_by_user(db_session):
    from app.models.user import User
    user = User(email="user@test.com", username="user", hashed_password="dummy")
    db_session.add(user)
    db_session.commit()
    data1 = LinkCreate(original_url="https://example.com/1")
    data2 = LinkCreate(original_url="https://example.com/2")
    link1 = link_service.create_link(db_session, data1, user_id=user.id)
    link2 = link_service.create_link(db_session, data2, user_id=user.id)
    links = link_service.get_links_by_user(db_session, user.id)
    assert len(links) == 2
    assert link1.id in [l.id for l in links]
    assert link2.id in [l.id for l in links]

def test_get_link_by_original_url(db_session):
    url = "https://example.com/searchme"
    data = LinkCreate(original_url=url)
    link = link_service.create_link(db_session, data, user_id=None)
    results = link_service.get_link_by_original_url(db_session, url)
    assert len(results) == 1
    assert results[0].id == link.id
    results = link_service.get_link_by_original_url(db_session, "https://notfound.com")
    assert results == []