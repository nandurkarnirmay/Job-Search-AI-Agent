def test_register_login_me(client):
    r = client.post("/auth/register", json={"email": "A@Example.com", "password": "password123"})
    assert r.status_code == 201
    r = client.post("/auth/login", json={"email": "a@example.com", "password": "password123"})
    token = r.json()["access_token"]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["email"] == "a@example.com"


def test_duplicate_and_bad_password(client):
    body = {"email": "a@example.com", "password": "password123"}
    client.post("/auth/register", json=body)
    assert client.post("/auth/register", json=body).json()["error"]["code"] == "conflict"
    r = client.post("/auth/login", json={**body, "password": "wrongpass1"})
    assert r.status_code == 401 and r.json()["error"]["code"] == "invalid_credentials"


def test_short_password_rejected(client):
    r = client.post("/auth/register", json={"email": "a@example.com", "password": "short"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"


def test_protected_routes_need_token(client):
    assert client.get("/me/profile").status_code == 401
    r = client.get("/auth/me", headers={"Authorization": "Bearer garbage"})
    assert r.status_code == 401 and "request_id" in r.json()["error"]


def test_profile_roundtrip(auth_client):
    body = {"full_name": "Asha", "current_city": "Pune", "preferred_cities": ["Bengaluru", " "],
            "experience_years": 1.5, "skills": ["Python", "python", "SQL"], "expected_lpa": 8,
            "notice_period_days": 30, "work_mode": "hybrid"}
    r = auth_client.put("/me/profile", json=body)
    assert r.status_code == 200
    got = auth_client.get("/me/profile").json()
    assert got["preferred_cities"] == ["Bengaluru"] and got["skills"] == ["python", "sql"]


def test_delete_account(auth_client):
    assert auth_client.delete("/auth/me").status_code == 204
    assert auth_client.get("/auth/me").status_code == 401
