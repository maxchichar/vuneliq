from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.identity.models import User, UserRole
from app.shared.security import hash_password


def test_register_user_success(client: TestClient):
    """Test user registration returns 201 and valid UUID."""
    response = client.post(
        "/api/auth/register",
        json={
            "email": "donor@example.com",
            "password": "securepassword123",
            "full_name": "Alice Donor",
            "role": "donor",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "donor@example.com"
    assert data["role"] == "donor"
    assert "id" in data
    # Verify id is a valid UUID string
    assert len(data["id"]) == 36
    assert "hashed_password" not in data


def test_register_duplicate_email_fails(client: TestClient):
    """Rule: Duplicate email addresses must be rejected with 409 Conflict."""
    payload = {
        "email": "duplicate@example.com",
        "password": "securepassword123",
        "full_name": "Bob Duplicate",
        "role": "donor",
    }
    first_res = client.post("/api/auth/register", json=payload)
    assert first_res.status_code == 201

    second_res = client.post("/api/auth/register", json=payload)
    assert second_res.status_code == 409
    assert "already exists" in second_res.json()["detail"]


def test_login_returns_access_and_refresh_tokens(client: TestClient):
    """Test login returns both access_token and refresh_token."""
    client.post(
        "/api/auth/register",
        json={
            "email": "login_user@example.com",
            "password": "validpassword123",
            "full_name": "Charlie Login",
            "role": "donor",
        },
    )

    login_res = client.post(
        "/api/auth/login",
        json={"email": "login_user@example.com", "password": "validpassword123"},
    )
    assert login_res.status_code == 200
    token_data = login_res.json()
    assert "access_token" in token_data
    assert "refresh_token" in token_data
    assert token_data["token_type"] == "bearer"
    assert token_data["user"]["email"] == "login_user@example.com"


def test_token_refresh_flow(client: TestClient):
    """Test exchanging a refresh token for a new access token."""
    client.post(
        "/api/auth/register",
        json={
            "email": "refresher@example.com",
            "password": "validpassword123",
            "full_name": "Refresh Tester",
            "role": "donor",
        },
    )
    login_res = client.post(
        "/api/auth/login",
        json={"email": "refresher@example.com", "password": "validpassword123"},
    )
    refresh_token = login_res.json()["refresh_token"]

    refresh_res = client.post(
        "/api/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_res.status_code == 200
    assert "access_token" in refresh_res.json()


def test_logout_revokes_refresh_token(client: TestClient):
    """Test that logging out revokes the refresh token."""
    client.post(
        "/api/auth/register",
        json={
            "email": "logout_user@example.com",
            "password": "validpassword123",
            "full_name": "Logout Tester",
            "role": "donor",
        },
    )
    login_res = client.post(
        "/api/auth/login",
        json={"email": "logout_user@example.com", "password": "validpassword123"},
    )
    refresh_token = login_res.json()["refresh_token"]

    # Logout
    logout_res = client.post(
        "/api/auth/logout",
        json={"refresh_token": refresh_token},
    )
    assert logout_res.status_code == 200

    # Attempting to refresh with the revoked token must fail with 401
    failed_refresh = client.post(
        "/api/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert failed_refresh.status_code == 401


def test_logout_all_devices(client: TestClient):
    """Test logout-all revokes all sessions for the user."""
    client.post(
        "/api/auth/register",
        json={
            "email": "multidevice@example.com",
            "password": "validpassword123",
            "full_name": "Multi Device",
            "role": "donor",
        },
    )
    # Login on device 1
    session1 = client.post(
        "/api/auth/login",
        json={"email": "multidevice@example.com", "password": "validpassword123"},
    ).json()

    # Login on device 2
    session2 = client.post(
        "/api/auth/login",
        json={"email": "multidevice@example.com", "password": "validpassword123"},
    ).json()

    # Call /logout-all using session 1's access token
    logout_all_res = client.post(
        "/api/auth/logout-all",
        headers={"Authorization": f"Bearer {session1['access_token']}"},
    )
    assert logout_all_res.status_code == 200

    # Both refresh tokens must now be rejected
    res1 = client.post("/api/auth/refresh", json={"refresh_token": session1["refresh_token"]})
    res2 = client.post("/api/auth/refresh", json={"refresh_token": session2["refresh_token"]})
    assert res1.status_code == 401
    assert res2.status_code == 401

    # Device 2's ALREADY-ISSUED access token must ALSO be rejected immediately!
    stale_access_res = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {session2['access_token']}"},
    )
    assert stale_access_res.status_code == 401
    assert "revoked" in stale_access_res.json()["detail"].lower()


def test_rbac_donor_cannot_access_admin_endpoint(client: TestClient):
    """Rule 5: Unauthorized users cannot perform reviewer/admin actions (403 Forbidden)."""
    client.post(
        "/api/auth/register",
        json={
            "email": "normal_donor@example.com",
            "password": "password12345",
            "full_name": "Normal Donor",
            "role": "donor",
        },
    )
    login_res = client.post(
        "/api/auth/login",
        json={"email": "normal_donor@example.com", "password": "password12345"},
    )
    donor_token = login_res.json()["access_token"]

    admin_res = client.get(
        "/api/auth/admin-only-test",
        headers={"Authorization": f"Bearer {donor_token}"},
    )
    assert admin_res.status_code == 403
    assert "Operation not permitted" in admin_res.json()["detail"]


def test_rbac_admin_can_access_admin_endpoint(client: TestClient, db_session: Session):
    """Verify an admin user can access the admin-only route."""
    admin = User(
        email="admin@vuneliq.org",
        hashed_password=hash_password("adminpassword123"),
        full_name="Super Admin",
        role=UserRole.ADMIN,
    )
    db_session.add(admin)
    db_session.commit()

    login_res = client.post(
        "/api/auth/login",
        json={"email": "admin@vuneliq.org", "password": "adminpassword123"},
    )
    admin_token = login_res.json()["access_token"]

    admin_res = client.get(
        "/api/auth/admin-only-test",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert admin_res.status_code == 200
    assert admin_res.json()["message"] == "Welcome Admin"