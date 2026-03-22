from fastapi.testclient import TestClient

def test_root(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "URL Shortener Service is running"}

def test_create_short_link(client: TestClient):
    response = client.post("/links/shorten", json={
        "original_url": "https://example.com",
        "expires_at": None
    })
    assert response.status_code == 201
    data = response.json()
    assert "short_code" in data
    assert data["original_url"].rstrip('/') == "https://example.com"

def test_create_short_link_with_alias(client: TestClient):
    response = client.post("/links/shorten", json={
        "original_url": "https://example.com",
        "custom_alias": "myalias"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["short_code"] == "myalias"

def test_create_short_link_duplicate_alias(client: TestClient):
    client.post("/links/shorten", json={
        "original_url": "https://example.com",
        "custom_alias": "dup"
    })
    response = client.post("/links/shorten", json={
        "original_url": "https://example.com",
        "custom_alias": "dup"
    })
    assert response.status_code == 409
    assert response.json()["detail"] == "Alias already exists"

def test_redirect_to_original(client: TestClient):
    resp = client.post("/links/shorten", json={"original_url": "https://example.com"})
    code = resp.json()["short_code"]
    response = client.get(f"/links/{code}", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "https://example.com/"

def test_redirect_not_found(client: TestClient):
    response = client.get("/links/nonexistent", follow_redirects=False)
    assert response.status_code == 404

def test_redirect_expired(client: TestClient):
    from datetime import datetime, timedelta, timezone
    expires_at = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    resp = client.post("/links/shorten", json={
        "original_url": "https://example.com",
        "expires_at": expires_at
    })
    code = resp.json()["short_code"]
    response = client.get(f"/links/{code}", follow_redirects=False)
    assert response.status_code == 404
    assert response.json()["detail"] == "Link has expired"

def test_get_stats(client: TestClient):
    resp = client.post("/links/shorten", json={"original_url": "https://example.com"})
    code = resp.json()["short_code"]
    response = client.get(f"/links/{code}/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["short_code"] == code
    assert data["original_url"] == "https://example.com/"

def test_get_stats_not_found(client: TestClient):
    response = client.get("/links/nonexistent/stats")
    assert response.status_code == 404

def test_search_links(client: TestClient):
    resp = client.post("/links/shorten", json={"original_url": "https://example.com"})
    assert resp.status_code == 201
    created_url = resp.json()["original_url"]
    print(f"Created URL: {repr(created_url)}")
    response = client.get("/links/search", params={"original_url": created_url})
    print(f"Search URL param: {repr(created_url)}")
    data = response.json()
    print(f"Search result: {data}")
    assert response.status_code == 200
    assert len(data) == 1
    assert "short_code" in data[0]
    assert data[0]["short_url"].startswith("http://localhost:8000/links/")

def test_search_links_empty(client: TestClient):
    response = client.get("/links/search", params={"original_url": "https://nonexistent.com"})
    assert response.status_code == 200
    assert response.json() == []

def test_update_link_unauthorized(client: TestClient):
    resp = client.post("/links/shorten", json={"original_url": "https://example.com"})
    code = resp.json()["short_code"]
    response = client.put(f"/links/{code}", json={"original_url": "https://new.com"})
    assert response.status_code == 401

def test_update_link_as_owner(client: TestClient, auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    resp = client.post("/links/shorten", json={"original_url": "https://example.com"}, headers=headers)
    code = resp.json()["short_code"]
    response = client.put(f"/links/{code}", json={"original_url": "https://new.com"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["original_url"] == "https://new.com/"

def test_update_link_not_found(client: TestClient, auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.put("/links/nonexistent", json={"original_url": "https://new.com"}, headers=headers)
    assert response.status_code == 404

def test_update_link_other_user(client: TestClient, auth_token):
    headers1 = {"Authorization": f"Bearer {auth_token}"}
    resp = client.post("/links/shorten", json={"original_url": "https://example.com"}, headers=headers1)
    code = resp.json()["short_code"]

    client.post("/auth/register", json={
        "email": "other@example.com",
        "username": "otheruser",
        "password": "a"
    })
    resp2 = client.post("/auth/token", data={"username": "otheruser", "password": "a"})
    token2 = resp2.json()["access_token"]
    headers2 = {"Authorization": f"Bearer {token2}"}

    response = client.put(f"/links/{code}", json={"original_url": "https://new.com"}, headers=headers2)
    assert response.status_code == 403
    assert response.json()["detail"] == "Not enough permissions"

def test_delete_link_unauthorized(client: TestClient):
    resp = client.post("/links/shorten", json={"original_url": "https://example.com"})
    code = resp.json()["short_code"]
    response = client.delete(f"/links/{code}")
    assert response.status_code == 401

def test_delete_link_as_owner(client: TestClient, auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    resp = client.post("/links/shorten", json={"original_url": "https://example.com"}, headers=headers)
    code = resp.json()["short_code"]
    response = client.delete(f"/links/{code}", headers=headers)
    assert response.status_code == 204
    response = client.get(f"/links/{code}/stats")
    assert response.status_code == 404

def test_delete_link_not_found(client: TestClient, auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.delete("/links/nonexistent", headers=headers)
    assert response.status_code == 404

def test_delete_link_other_user(client: TestClient, auth_token):
    headers1 = {"Authorization": f"Bearer {auth_token}"}
    resp = client.post("/links/shorten", json={"original_url": "https://example.com"}, headers=headers1)
    code = resp.json()["short_code"]

    client.post("/auth/register", json={
        "email": "other2@example.com",
        "username": "otheruser2",
        "password": "a"
    })
    resp2 = client.post("/auth/token", data={"username": "otheruser2", "password": "a"})
    token2 = resp2.json()["access_token"]
    headers2 = {"Authorization": f"Bearer {token2}"}

    response = client.delete(f"/links/{code}", headers=headers2)
    assert response.status_code == 403

def test_my_links_unauthorized(client: TestClient):
    response = client.get("/links/my-links")
    assert response.status_code == 401

def test_my_links_authorized(client: TestClient, auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    client.post("/links/shorten", json={"original_url": "https://example.com"}, headers=headers)
    client.post("/links/shorten", json={"original_url": "https://google.com"}, headers=headers)
    response = client.get("/links/my-links", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all(link["user_id"] is not None for link in data)

def test_my_links_invalid_token(client: TestClient):
    headers = {"Authorization": "Bearer invalid_token"}
    response = client.get("/links/my-links", headers=headers)
    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"

def test_my_links_user_not_found(client: TestClient):
    from jose import jwt
    from app.core.config import settings
    payload = {"sub": "nonexistentuser"}
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/links/my-links", headers=headers)
    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"

def test_my_links_inactive_user(client):
    reg_resp = client.post("/auth/register", json={
        "email": "inactive@example.com",
        "username": "inactive",
        "password": "a"
    })
    assert reg_resp.status_code == 200
    from app.models.user import User
    from app.core.database import SessionLocal
    db = SessionLocal()
    user = db.query(User).filter(User.username == "inactive").first()
    user.is_active = False
    db.commit()
    db.close()
    token_resp = client.post("/auth/token", data={"username": "inactive", "password": "a"})
    if token_resp.status_code == 200:
        token = token_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/links/my-links", headers=headers)
        assert response.status_code == 400
        assert response.json()["detail"] == "Inactive user"
    else:
        assert token_resp.status_code == 401

def test_swagger_ui(client: TestClient):
    response = client.get("/docs")
    assert response.status_code == 200

def test_my_links_token_without_sub(client):
    from jose import jwt
    from app.core.config import settings
    payload = {}
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/links/my-links", headers=headers)
    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"