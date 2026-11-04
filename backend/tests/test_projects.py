from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.identity.models import User, UserRole
from app.shared.security import hash_password


def create_test_user(client: TestClient, email: str, role: str) -> str:
    """Helper to register and login a test user, returning their access token."""
    client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "password123",
            "full_name": f"Test {role}",
            "role": role,
        },
    )
    login_res = client.post(
        "/api/auth/login",
        json={"email": email, "password": "password123"},
    )
    return login_res.json()["access_token"]


def create_admin_token(client: TestClient, db: Session, email: str = "admin_test@vuneliq.org") -> str:
    """Helper to seed an admin directly and log in."""
    admin = User(
        email=email,
        hashed_password=hash_password("adminpass123"),
        full_name="Admin Reviewer",
        role=UserRole.ADMIN,
    )
    db.add(admin)
    db.commit()
    login_res = client.post(
        "/api/auth/login",
        json={"email": email, "password": "adminpass123"},
    )
    return login_res.json()["access_token"]


SAMPLE_PROJECT_PAYLOAD = {
    "title": "Clean Water for Ogun Community",
    "description": "Providing solar-powered boreholes to deliver clean drinking water to over 5,000 residents.",
    "category": "Water & Sanitation",
    "location": "Ogun State, Nigeria",
    "funding_target": 500000000,  # 5,000,000 NGN in kobo
    "currency": "NGN",
    "beneficiary_target": "5,000 community members",
    "intended_outcomes": "Reduction in waterborne diseases and access to clean water.",
    "budget_breakdown": "Drilling: 2.5m, Solar Pump: 1.5m, Filtration & Tanks: 1.0m",
}


def test_submit_project_as_owner(client: TestClient):
    """Test project owner submitting a project. Stored as pending_review."""
    token = create_test_user(client, "owner1@vuneliq.org", "project_owner")

    response = client.post(
        "/api/projects",
        json=SAMPLE_PROJECT_PAYLOAD,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "pending_review"
    assert data["title"] == SAMPLE_PROJECT_PAYLOAD["title"]
    assert data["funding_target"] == 500000000


def test_rule_1_unapproved_projects_not_in_public_discovery(client: TestClient):
    """Rule 1: Unapproved projects cannot appear in public discovery or detail view."""
    owner_token = create_test_user(client, "owner2@vuneliq.org", "project_owner")

    # Submit project (pending_review)
    res = client.post(
        "/api/projects",
        json=SAMPLE_PROJECT_PAYLOAD,
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    project_id = res.json()["id"]

    # Public list must be empty
    public_list = client.get("/api/projects").json()
    assert all(p["id"] != project_id for p in public_list)

    # Public detail page must return 404
    detail_res = client.get(f"/api/projects/{project_id}")
    assert detail_res.status_code == 404


def test_admin_approve_project_makes_it_public(client: TestClient, db_session: Session):
    """Admin approves project -> project status becomes approved and appears in public discovery."""
    owner_token = create_test_user(client, "owner3@vuneliq.org", "project_owner")
    admin_token = create_admin_token(client, db_session, "approver@vuneliq.org")

    # 1. Owner submits project
    create_res = client.post(
        "/api/projects",
        json=SAMPLE_PROJECT_PAYLOAD,
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    project_id = create_res.json()["id"]

    # 2. Admin inspects pending queue
    queue_res = client.get("/api/admin/projects/pending", headers={"Authorization": f"Bearer {admin_token}"})
    assert queue_res.status_code == 200
    assert any(p["id"] == project_id for p in queue_res.json())

    # 3. Admin approves project
    review_res = client.post(
        f"/api/admin/projects/{project_id}/review",
        json={"action": "approve", "reason": "All verification documents and budget validated."},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert review_res.status_code == 200
    assert review_res.json()["action"] == "approve"

    # 4. Now project MUST appear in public discovery
    public_res = client.get(f"/api/projects/{project_id}")
    assert public_res.status_code == 200
    assert public_res.json()["status"] == "approved"


def test_rule_3_owner_cannot_edit_another_owners_project(client: TestClient):
    """Rule 3: Project owners cannot manage or edit projects belonging to other owners."""
    token_owner_a = create_test_user(client, "owner_a@vuneliq.org", "project_owner")
    token_owner_b = create_test_user(client, "owner_b@vuneliq.org", "project_owner")

    # Owner A creates project
    create_res = client.post(
        "/api/projects",
        json=SAMPLE_PROJECT_PAYLOAD,
        headers={"Authorization": f"Bearer {token_owner_a}"},
    )
    project_id = create_res.json()["id"]

    # Owner B attempts to edit Owner A's project
    patch_res = client.patch(
        f"/api/projects/{project_id}",
        json={"title": "Hacked Title by Owner B"},
        headers={"Authorization": f"Bearer {token_owner_b}"},
    )
    assert patch_res.status_code == 403


def test_rule_5_donor_cannot_access_review_queue(client: TestClient):
    """Rule 5: Non-admin users cannot access the admin review queue or submit review actions."""
    donor_token = create_test_user(client, "donor_reviewer_attempt@vuneliq.org", "donor")

    # Attempt to view review queue
    res = client.get("/api/admin/projects/pending", headers={"Authorization": f"Bearer {donor_token}"})
    assert res.status_code == 403


def test_rule_27_owner_cannot_approve_own_submission(client: TestClient, db_session: Session):
    """Rule 27: Conflict of interest: An owner cannot approve their own submission."""
    # Seed an admin who also creates a project
    admin_token = create_admin_token(client, db_session, "dual_role_user@vuneliq.org")

    create_res = client.post(
        "/api/projects",
        json=SAMPLE_PROJECT_PAYLOAD,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    project_id = create_res.json()["id"]

    # Attempt to self-approve
    approve_res = client.post(
        f"/api/admin/projects/{project_id}/review",
        json={"action": "approve", "reason": "Self-approving my own project."},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert approve_res.status_code == 400
    assert "cannot approve their own" in approve_res.json()["detail"].lower()


def test_owner_edit_requeues_project_for_review(client: TestClient, db_session: Session):
    """Owner editing an approved or changes_requested project resets status to pending_review."""
    owner_token = create_test_user(client, "owner_requeue@vuneliq.org", "project_owner")
    admin_token = create_admin_token(client, db_session, "admin_requeue@vuneliq.org")

    # 1. Create project
    create_res = client.post(
        "/api/projects",
        json=SAMPLE_PROJECT_PAYLOAD,
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    project_id = create_res.json()["id"]

    # 2. Admin requests changes
    client.post(
        f"/api/admin/projects/{project_id}/review",
        json={"action": "request_changes", "reason": "Please provide clearer budget details."},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # 3. Owner updates the project
    patch_res = client.patch(
        f"/api/projects/{project_id}",
        json={"budget_breakdown": "Drilling: 2.5m, Solar Pump: 1.5m, Filtration: 1.0m (Updated details)"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert patch_res.status_code == 200
    # Status MUST be reset to pending_review!
    assert patch_res.json()["status"] == "pending_review"

    # 4. Verify it reappears in admin pending queue
    pending_queue = client.get(
        "/api/admin/projects/pending",
        headers={"Authorization": f"Bearer {admin_token}"},
    ).json()
    assert any(p["id"] == project_id for p in pending_queue)


def test_reject_explicit_null_in_project_patch(client: TestClient):
    """Explicit null for non-nullable fields must be rejected with 422, not cause a 500."""
    owner_token = create_test_user(client, "null_tester@vuneliq.org", "project_owner")

    create_res = client.post(
        "/api/projects",
        json=SAMPLE_PROJECT_PAYLOAD,
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    project_id = create_res.json()["id"]

    # Attempt to send explicit null
    patch_res = client.patch(
        f"/api/projects/{project_id}",
        json={"title": None},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    # Must return 422 Unprocessable Entity
    assert patch_res.status_code == 422
    assert "cannot be null" in patch_res.text