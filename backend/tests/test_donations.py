from unittest.mock import patch
from fastapi.testclient import TestClient
import pytest
import uuid
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.donations.models import Donation, Payment
from app.modules.identity.models import User, UserRole
from app.modules.projects.models import Project, ProjectStatus
from app.shared.security import hash_password


def create_donor_token(client: TestClient, email: str = "donor_test@vuneliq.org") -> str:
    client.post(
        "/api/auth/register",
        json={"email": email, "password": "password123", "full_name": "Test Donor", "role": "donor"},
    )
    login_res = client.post(
        "/api/auth/login",
        json={"email": email, "password": "password123"},
    )

    return login_res.json()["access_token"]


def seed_project(db: Session, status: ProjectStatus = ProjectStatus.APPROVED) -> Project:
    owner = User(
        email=f"owner_{status.value}@vuneliq.org",
        hashed_password=hash_password("password123"),
        full_name="Project Owner",
        role=UserRole.PROJECT_OWNER,
    )
    db.add(owner)
    db.flush()


    project = Project(
        owner_id=owner.id,
        title="Community Solar Grid",
        description="Providing renewable power to off-grid rural health centers.",
        category="Energy",
        location="Kaduna State",
        funding_target=100000000,  # 1,000,000 NGN in kobo
        amount_raised=0,
        currency="NGN",
        beneficiary_target="10,000 residents",
        intended_outcomes="Reliable power for vaccines and maternity clinics.",
        budget_breakdown="Panels: 500k, Batteries: 300k, Inverters: 200k",
        status=status,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def test_initiate_donation_success(client: TestClient, db_session: Session):
    """Test successful donation initiation against an approved project."""
    project = seed_project(db_session, ProjectStatus.APPROVED)
    donor_token = create_donor_token(client, "donor_success@vuneliq.org")

    res = client.post(
        f"/api/projects/{project.id}/donations",
        json={"amount": 500000, "currency": "NGN", "is_anonymous": False},  # 5,000 NGN
        headers={
            "Authorization": f"Bearer {donor_token}",
            "Idempotency-Key": f"test-key-{uuid.uuid4().hex}",
        },
    )

    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "pending"
    assert data["amount"] == 500000
    assert len(data["payments"]) == 1
    assert data["payments"][0]["status"] == "pending"
    assert data["payments"][0]["reference"].startswith("VUN-")


def test_rule_1_cannot_donate_to_unapproved_project(client: TestClient, db_session: Session):
    """Rule 1: Donations to pending_review projects are rejected with 400 Bad Request."""
    project = seed_project(db_session, ProjectStatus.PENDING_REVIEW)
    donor_token = create_donor_token(client, "donor_unapproved@vuneliq.org")
    res = client.post(
        f"/api/projects/{project.id}/donations",
        json={"amount": 500000},
        headers={
            "Authorization": f"Bearer {donor_token}",
            "Idempotency-Key": f"test-key-{uuid.uuid4().hex}",
        },
    )
    assert res.status_code == 400
    assert "not open for public donations" in res.json()["detail"].lower()


def test_rule_2_cannot_donate_to_suspended_project(client: TestClient, db_session: Session):
    """Rule 2: Donations to suspended projects are rejected with 400 Bad Request."""
    project = seed_project(db_session, ProjectStatus.SUSPENDED)
    donor_token = create_donor_token(client, "donor_suspended@vuneliq.org")
    res = client.post(
        f"/api/projects/{project.id}/donations",
        json={"amount": 500000},
        headers={
            "Authorization": f"Bearer {donor_token}",
            "Idempotency-Key": f"test-key-{uuid.uuid4().hex}",
        },
    )
    assert res.status_code == 400
    assert "suspended" in res.json()["detail"].lower()


def test_rule_6_reject_invalid_donation_amounts(client: TestClient, db_session: Session):
    """Rule 6: Amounts <= 0 must be rejected."""
    project = seed_project(db_session, ProjectStatus.APPROVED)
    donor_token = create_donor_token(client, "donor_invalid_amount@vuneliq.org")
    # Zero amount
    res_zero = client.post(
        f"/api/projects/{project.id}/donations",
        json={"amount": 0},
        headers={
            "Authorization": f"Bearer {donor_token}",
            "Idempotency-Key": f"test-key-{uuid.uuid4().hex}",
        },
    )
    assert res_zero.status_code == 422
    # Negative amount
    res_neg = client.post(
        f"/api/projects/{project.id}/donations",
        json={"amount": -1000},
        headers={
            "Authorization": f"Bearer {donor_token}",
            "Idempotency-Key": f"test-key-{uuid.uuid4().hex}",
        },
    )
    assert res_neg.status_code == 422

def test_rule_8_successful_payment_updates_project_amount_raised(client: TestClient, db_session: Session):
    """Rule 8: Successful payment simulation increments project.amount_raised."""
    project = seed_project(db_session, ProjectStatus.APPROVED)
    donor_token = create_donor_token(client, "donor_credited@vuneliq.org")
    # 1. Initiate donation of 25,000 NGN (2,500,000 kobo)
    donation_res = client.post(
        f"/api/projects/{project.id}/donations",
        json={"amount": 2500000},
        headers={
            "Authorization": f"Bearer {donor_token}",
            "Idempotency-Key": f"test-key-{uuid.uuid4().hex}",
        },
    )
    payment_id = donation_res.json()["payments"][0]["id"]
    # 2. Simulate payment success
    pay_res = client.post(
        f"/api/payments/{payment_id}/simulate-result",
        json={"status": "succeeded", "provider_tx_id": "TX-MOCK-SUCCESS-123"},
    )
    assert pay_res.status_code == 200
    assert pay_res.json()["status"] == "succeeded"
    # 3. Check public project: amount_raised MUST be 2,500,000
    project_res = client.get(f"/api/projects/{project.id}")
    assert project_res.json()["amount_raised"] == 2500000


def test_rule_7_failed_payment_does_not_increment_project_total(client: TestClient, db_session: Session):
    """Rule 7: Failed or cancelled payments do NOT increment project totals."""
    project = seed_project(db_session, ProjectStatus.APPROVED)
    donor_token = create_donor_token(client, "donor_failed_flow@vuneliq.org")
    donation_res = client.post(
        f"/api/projects/{project.id}/donations",
        json={"amount": 1000000},
        headers={
            "Authorization": f"Bearer {donor_token}",
            "Idempotency-Key": f"test-key-{uuid.uuid4().hex}",
        },
    )
    payment_id = donation_res.json()["payments"][0]["id"]
    # Simulate payment failure
    client.post(
        f"/api/payments/{payment_id}/simulate-result",
        json={"status": "failed"},
    )
    # Project total must remain 0!
    project_res = client.get(f"/api/projects/{project.id}")
    assert project_res.json()["amount_raised"] == 0


def test_rule_9_idempotency_prevents_double_counting(client: TestClient, db_session: Session):
    """Rule 9: Replaying payment success confirmation multiple times does NOT double-count."""
    project = seed_project(db_session, ProjectStatus.APPROVED)
    donor_token = create_donor_token(client, "donor_idempotent@vuneliq.org")
    donation_res = client.post(
        f"/api/projects/{project.id}/donations",
        json={"amount": 1000000},  # 10,000 NGN
        headers={
            "Authorization": f"Bearer {donor_token}",
            "Idempotency-Key": f"test-key-{uuid.uuid4().hex}",
        },
    )
    payment_id = donation_res.json()["payments"][0]["id"]
    # First confirmation
    res1 = client.post(f"/api/payments/{payment_id}/simulate-result", json={"status": "succeeded"})
    assert res1.status_code == 200
    # Duplicate confirmation (e.g. webhook retry or double-click)
    res2 = client.post(f"/api/payments/{payment_id}/simulate-result", json={"status": "succeeded"})
    assert res2.status_code == 200
    # Project total MUST be 1,000,000 — NOT 2,000,000!
    project_res = client.get(f"/api/projects/{project.id}")
    assert project_res.json()["amount_raised"] == 1000000


def test_idempotency_key_prevents_duplicate_donation_creation(client: TestClient, db_session: Session):
    """Sending the same Idempotency-Key returns the existing donation instead of creating a second one."""
    project = seed_project(db_session, ProjectStatus.APPROVED)
    donor_token = create_donor_token(client, "donor_idempotent_key@vuneliq.org")
    headers = {
        "Authorization": f"Bearer {donor_token}",
        "Idempotency-Key": "unique-client-session-key-12345",
    }
    # First request
    res1 = client.post(
        f"/api/projects/{project.id}/donations",
        json={"amount": 500000},
        headers=headers,
    )
    assert res1.status_code == 201
    donation_id = res1.json()["id"]
    # Replayed / double-clicked request with identical Idempotency-Key
    res2 = client.post(
        f"/api/projects/{project.id}/donations",
        json={"amount": 500000},
        headers=headers,
    )
    # Must return the SAME donation ID!
    assert res2.status_code == 201
    assert res2.json()["id"] == donation_id
    # Verify donor only has ONE donation recorded
    my_donations = client.get("/api/my/donations", headers={"Authorization": f"Bearer {donor_token}"}).json()
    assert len(my_donations) == 1


def test_rule_4_donor_privacy_and_history(client: TestClient, db_session: Session):
    """Rule 4: Donor A can view their history; Donor B cannot access Donor A's private donation details."""
    project = seed_project(db_session, ProjectStatus.APPROVED)
    token_alice = create_donor_token(client, "alice_donor@vuneliq.org")
    token_bob = create_donor_token(client, "bob_donor@vuneliq.org")
    
    # Alice makes a donation
    alice_donation = client.post(
        f"/api/projects/{project.id}/donations",
        json={"amount": 750000},
        headers={
            "Authorization": f"Bearer {token_alice}",
            "Idempotency-Key": "alice-unique-key-001",
        },
    ).json()

    # 1. Alice can view her list of donations
    alice_history = client.get("/api/my/donations", headers={"Authorization": f"Bearer {token_alice}"})
    assert alice_history.status_code == 200
    assert any(d["id"] == alice_donation["id"] for d in alice_history.json())
    
    # 2. Bob's list does NOT contain Alice's donation
    bob_history = client.get("/api/my/donations", headers={"Authorization": f"Bearer {token_bob}"})
    assert bob_history.status_code == 200
    assert all(d["id"] != alice_donation["id"] for d in bob_history.json())
    
    # 3. Bob directly requesting Alice's donation details by ID is REJECTED (403 Forbidden)
    bob_detail = client.get(
        f"/api/donations/{alice_donation['id']}",
        headers={"Authorization": f"Bearer {token_bob}"},
    )
    assert bob_detail.status_code == 403


def test_transaction_rollback_on_midway_failure(client: TestClient, db_session: Session):
    """
    Simulates an unexpected crash after flush but before commit during donation initiation.
    Verifies that db.rollback() fires and NO orphaned donation row is left in the database.
    """
    project = seed_project(db_session, ProjectStatus.APPROVED)
    donor_token = create_donor_token(client, "donor_crash_tester@vuneliq.org")
    
    # We mock db.commit to raise an unexpected runtime error (simulating power loss / DB crash)
    with patch.object(Session, "commit", side_effect=RuntimeError("Simulated DB Connection Crash")):
        with pytest.raises(RuntimeError):
            client.post(
                f"/api/projects/{project.id}/donations",
                json={"amount": 500000},
                headers={
                    "Authorization": f"Bearer {donor_token}",
                    "Idempotency-Key": f"test-key-{uuid.uuid4().hex}",
                },
            )
    # ACID Check: The donation must NOT exist in the database!
    remaining_donations = db_session.scalars(select(Donation)).all()
    assert len(remaining_donations) == 0
    remaining_payments = db_session.scalars(select(Payment)).all()
    assert len(remaining_payments) == 0

def test_missing_idempotency_header_rejected_with_422(client: TestClient, db_session: Session):
    """Omitting the mandatory Idempotency-Key header is rejected by FastAPI with 422."""
    project = seed_project(db_session, ProjectStatus.APPROVED)
    donor_token = create_donor_token(client, "donor_no_header@vuneliq.org")

    # Request with NO Idempotency-Key
    res = client.post(
        f"/api/projects/{project.id}/donations",
        json={"amount": 500000},
        headers={"Authorization": f"Bearer {donor_token}"},
    )
    assert res.status_code == 422
    assert "idempotency-key" in res.text.lower()


def test_idempotency_key_payload_mutation_rejected_with_409(client: TestClient, db_session: Session):
    """Reusing the same Idempotency-Key with altered parameters must return 409 Conflict."""
    project = seed_project(db_session, ProjectStatus.APPROVED)
    donor_token = create_donor_token(client, "donor_payload_mutation@vuneliq.org")
    headers = {
        "Authorization": f"Bearer {donor_token}",
        "Idempotency-Key": "test-mutation-key-9999",
    }
    
    # 1. Original donation of 500,000 kobo
    res1 = client.post(
        f"/api/projects/{project.id}/donations",
        json={"amount": 500000, "currency": "NGN"},
        headers=headers,
    )
    assert res1.status_code == 201

    # 2. Replay with SAME key, but altered amount (700,000 kobo)
    res2 = client.post(
        f"/api/projects/{project.id}/donations",
        json={"amount": 700000, "currency": "NGN"},
        headers=headers,
    )
    assert res2.status_code == 409
    assert "different request parameters" in res2.json()["detail"].lower()


def test_currency_mismatch_rejected(client: TestClient, db_session: Session):
    """Attempting to donate in USD to an NGN project must return 400 Bad Request."""
    project = seed_project(db_session, ProjectStatus.APPROVED)
    donor_token = create_donor_token(client, "donor_currency_mismatch@vuneliq.org")

    res = client.post(
        f"/api/projects/{project.id}/donations",
        json={"amount": 500000, "currency": "USD"},
        headers={
            "Authorization": f"Bearer {donor_token}",
            "Idempotency-Key": f"test-curr-{uuid.uuid4().hex}",
        },
    )
    assert res.status_code == 400
    assert "currency mismatch" in res.json()["detail"].lower()


def test_terminal_payment_state_cannot_be_overwritten(client: TestClient, db_session: Session):
    """A failed payment cannot be transitioned to succeeded."""
    project = seed_project(db_session, ProjectStatus.APPROVED)
    donor_token = create_donor_token(client, "donor_terminal_state@vuneliq.org")

    donation_res = client.post(
        f"/api/projects/{project.id}/donations",
        json={"amount": 500000},
        headers={
            "Authorization": f"Bearer {donor_token}",
            "Idempotency-Key": f"test-term-{uuid.uuid4().hex}",
        },
    )
    payment_id = donation_res.json()["payments"][0]["id"]

    # Transition to failed
    fail_res = client.post(f"/api/payments/{payment_id}/simulate-result", json={"status": "failed"})
    assert fail_res.status_code == 200

    # Attempt to transition failed -> succeeded must be rejected
    res = client.post(f"/api/payments/{payment_id}/simulate-result", json={"status": "succeeded"})
    assert res.status_code == 400
    assert "terminal status" in res.json()["detail"].lower()


def test_get_project_donations_summary(client: TestClient, db_session: Session):
    """Verifies that the summary endpoint returns accurate counts, sums, and 404s for invalid projects."""
    project = seed_project(db_session, ProjectStatus.APPROVED)
    donor_token = create_donor_token(client, "donor_summary_tester@vuneliq.org")

    # Initial summary: 0 donations
    s1 = client.get(f"/api/projects/{project.id}/donations/summary")
    assert s1.status_code == 200
    assert s1.json()["total_successful_donations"] == 0
    assert s1.json()["total_amount_raised"] == 0

    # Add and confirm a donation of 1,500,000 kobo
    d1 = client.post(
        f"/api/projects/{project.id}/donations",
        json={"amount": 1500000},
        headers={
            "Authorization": f"Bearer {donor_token}",
            "Idempotency-Key": f"test-sum-{uuid.uuid4().hex}",
        },
    ).json()
    client.post(f"/api/payments/{d1['payments'][0]['id']}/simulate-result", json={"status": "succeeded"})

    # Summary should reflect 1 donation and 1,500,000
    s2 = client.get(f"/api/projects/{project.id}/donations/summary")
    assert s2.status_code == 200
    assert s2.json()["total_successful_donations"] == 1
    assert s2.json()["total_amount_raised"] == 1500000

    # Summary for non-existent project returns 404
    non_existent = uuid.uuid4()
    s3 = client.get(f"/api/projects/{non_existent}/donations/summary")
    assert s3.status_code == 404