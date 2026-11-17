import uuid
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.identity.models import User, UserRole
from app.modules.projects.models import Project, ProjectStatus
from app.shared.security import hash_password


def create_user_token(
    client: TestClient,
    email: str,
    role: str = "project_owner",
) -> str:
    client.post(
        "/api/auth/register",
        json={"email": email, "password": "password123", "full_name": "Test User", "role": role},
    )
    login_res = client.post(
        "/api/auth/login",
        json={"email": email, "password": "password123"},
    )
    return login_res.json()["access_token"]


def seed_funded_project(
    db: Session,
    amount_raised: int = 10_000_000,  # 100,000 NGN in kobo
    funding_target: int = 20_000_000, # 200,000 NGN in kobo
    status: ProjectStatus = ProjectStatus.APPROVED,
) -> tuple[Project, User]:
    owner = User(
        email=f"owner_{uuid.uuid4().hex[:8]}@vuneliq.org",
        hashed_password=hash_password("password123"),
        full_name="Funded Project Owner",
        role=UserRole.PROJECT_OWNER,
    )
    db.add(owner)
    db.flush()

    project = Project(
        owner_id=owner.id,
        title="Borehole Water Project",
        description="Clean water for rural community.",
        category="Water",
        location="Enugu State",
        funding_target=funding_target,
        amount_raised=amount_raised,
        currency="NGN",
        beneficiary_target="5,000 residents",
        intended_outcomes="Reduce water-borne diseases.",
        budget_breakdown="Drilling: 100k, Pump: 60k, Pipes: 40k",
        status=status,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project, owner


def test_owner_can_log_expense_success(client: TestClient, db_session: Session):
    """Rule 10 & 11: Project owner can log a valid expense within raised funds."""
    project, owner = seed_funded_project(db_session, amount_raised=10_000_000)
    owner_token = create_user_token(client, owner.email)

    res = client.post(
        f"/api/projects/{project.id}/expenses",
        json={
            "amount": 2_500_000,  # 25,000 NGN
            "currency": "NGN",
            "category": "EQUIPMENT",
            "description": "Purchased submersible solar water pump",
            "receipt_url": "https://storage.vuneliq.org/receipts/pump-001.pdf",
        },
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    assert res.status_code == 201
    data = res.json()
    assert data["amount"] == 2_500_000
    assert data["category"] == "EQUIPMENT"
    assert data["project_id"] == str(project.id)
    assert data["receipt_url"] == "https://storage.vuneliq.org/receipts/pump-001.pdf"


def create_admin_token(client: TestClient, db: Session, email: str = "admin_impact@vuneliq.org") -> str:
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


def test_admin_can_log_expense_for_any_project(client: TestClient, db_session: Session):
    """Admins have platform-wide permission to log expenses on approved projects."""
    project, _ = seed_funded_project(db_session, amount_raised=5_000_000)
    admin_token = create_admin_token(client, db_session, f"admin_{uuid.uuid4().hex[:6]}@vuneliq.org")

    res = client.post(
        f"/api/projects/{project.id}/expenses",
        json={
            "amount": 1_000_000,
            "currency": "NGN",
            "category": "LOGISTICS",
            "description": "Transporting water drilling rig to site",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert res.status_code == 201
    assert res.json()["amount"] == 1_000_000


def test_non_owner_cannot_log_expense(client: TestClient, db_session: Session):
    """Rule 10: Another project owner cannot log expenses on a project they do not own."""
    project, _ = seed_funded_project(db_session, amount_raised=5_000_000)
    stranger_token = create_user_token(client, f"stranger_{uuid.uuid4().hex[:6]}@vuneliq.org", role="project_owner")

    res = client.post(
        f"/api/projects/{project.id}/expenses",
        json={
            "amount": 500_000,
            "currency": "NGN",
            "category": "LABOR",
            "description": "Unauthorized contractor fee",
        },
        headers={"Authorization": f"Bearer {stranger_token}"},
    )

    assert res.status_code == 403
    assert "access denied" in res.json()["detail"].lower()


def test_donor_cannot_log_expense(client: TestClient, db_session: Session):
    """Rule 10: Donors cannot log expenses."""
    project, _ = seed_funded_project(db_session, amount_raised=5_000_000)
    donor_token = create_user_token(client, f"donor_{uuid.uuid4().hex[:6]}@vuneliq.org", role="donor")

    res = client.post(
        f"/api/projects/{project.id}/expenses",
        json={"amount": 500_000, "category": "MATERIALS", "description": "Gravel and cement"},
        headers={"Authorization": f"Bearer {donor_token}"},
    )

    assert res.status_code == 403


def test_cannot_log_expense_to_unapproved_project(client: TestClient, db_session: Session):
    """Expenses cannot be logged against pending_review or suspended projects."""
    project, owner = seed_funded_project(db_session, amount_raised=0, status=ProjectStatus.PENDING_REVIEW)
    owner_token = create_user_token(client, owner.email)

    res = client.post(
        f"/api/projects/{project.id}/expenses",
        json={"amount": 100_000, "category": "PERMITS", "description": "Local council permit"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    assert res.status_code == 400
    assert "cannot log expenses" in res.json()["detail"].lower()


def test_reject_invalid_expense_amounts(client: TestClient, db_session: Session):
    """Amounts <= 0 are rejected with 422."""
    project, owner = seed_funded_project(db_session, amount_raised=5_000_000)
    owner_token = create_user_token(client, owner.email)

    # Zero amount
    res_zero = client.post(
        f"/api/projects/{project.id}/expenses",
        json={"amount": 0, "category": "OTHER", "description": "Zero cost item"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert res_zero.status_code == 422

    # Negative amount
    res_neg = client.post(
        f"/api/projects/{project.id}/expenses",
        json={"amount": -50_000, "category": "OTHER", "description": "Negative expense"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert res_neg.status_code == 422


def test_expense_currency_mismatch_rejected(client: TestClient, db_session: Session):
    """Expense currency must match the project's native currency."""
    project, owner = seed_funded_project(db_session, amount_raised=5_000_000)
    owner_token = create_user_token(client, owner.email)

    res = client.post(
        f"/api/projects/{project.id}/expenses",
        json={"amount": 100_000, "currency": "USD", "category": "EQUIPMENT", "description": "Imported valve"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    assert res.status_code == 400
    assert "currency mismatch" in res.json()["detail"].lower()


def test_rule_11_overspend_protection_rejected(client: TestClient, db_session: Session):
    """Rule 11: An expense exceeding the remaining unspent balance must be rejected."""
    # Project raised 50,000 NGN (5,000,000 kobo)
    project, owner = seed_funded_project(db_session, amount_raised=5_000_000)
    owner_token = create_user_token(client, owner.email)

    # 1. First expense of 3,500,000 kobo succeeds (1,500,000 kobo remaining)
    res1 = client.post(
        f"/api/projects/{project.id}/expenses",
        json={"amount": 3_500_000, "category": "LABOR", "description": "Drilling crew labor"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert res1.status_code == 201

    # 2. Second expense of 2,000,000 kobo attempts to overspend (3.5M + 2M = 5.5M > 5M raised)
    res2 = client.post(
        f"/api/projects/{project.id}/expenses",
        json={"amount": 2_000_000, "category": "MATERIALS", "description": "Excess pipes and casing"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert res2.status_code == 400
    assert "exceeds remaining unspent balance" in res2.json()["detail"].lower()


def test_public_can_view_project_expenses(client: TestClient, db_session: Session):
    """Anyone can publicly inspect expenses and verified receipts."""
    project, owner = seed_funded_project(db_session, amount_raised=5_000_000)
    owner_token = create_user_token(client, owner.email)

    client.post(
        f"/api/projects/{project.id}/expenses",
        json={"amount": 1_000_000, "category": "MATERIALS", "description": "Pipes purchased"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    # Public unauthenticated request
    res = client.get(f"/api/projects/{project.id}/expenses")
    assert res.status_code == 200
    expenses = res.json()
    assert len(expenses) == 1
    assert expenses[0]["description"] == "Pipes purchased"


def test_owner_can_publish_progress_report(client: TestClient, db_session: Session):
    """Owner can publish an impact milestone report."""
    project, owner = seed_funded_project(db_session, amount_raised=5_000_000)
    owner_token = create_user_token(client, owner.email)

    res = client.post(
        f"/api/projects/{project.id}/reports",
        json={
            "title": "Phase 1: Water Well Drilled to 65 Meters",
            "content": "The geological survey succeeded and clean drinking water was reached yesterday.",
            "milestone_completed": "Well Drilling Completed",
            "media_url": "https://storage.vuneliq.org/photos/well-site.jpg",
        },
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    assert res.status_code == 201
    data = res.json()
    assert data["title"] == "Phase 1: Water Well Drilled to 65 Meters"
    assert data["milestone_completed"] == "Well Drilling Completed"
    assert data["project_id"] == str(project.id)


def test_non_owner_cannot_publish_progress_report(client: TestClient, db_session: Session):
    """Rule 10: Non-owners cannot publish progress reports."""
    project, _ = seed_funded_project(db_session, amount_raised=5_000_000)
    stranger_token = create_user_token(client, f"stranger2_{uuid.uuid4().hex[:6]}@vuneliq.org", role="project_owner")

    res = client.post(
        f"/api/projects/{project.id}/reports",
        json={"title": "Unauthorized Report", "content": "Attempting to post fake news."},
        headers={"Authorization": f"Bearer {stranger_token}"},
    )

    assert res.status_code == 403


def test_public_can_view_progress_reports(client: TestClient, db_session: Session):
    """Public can view the timeline of progress updates."""
    project, owner = seed_funded_project(db_session, amount_raised=5_000_000)
    owner_token = create_user_token(client, owner.email)

    client.post(
        f"/api/projects/{project.id}/reports",
        json={"title": "Site Inspection", "content": "Community leaders met on site."},
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    # Public unauthenticated request
    res = client.get(f"/api/projects/{project.id}/reports")
    assert res.status_code == 200
    reports = res.json()
    assert len(reports) == 1
    assert reports[0]["title"] == "Site Inspection"


def test_financial_audit_endpoint_calculations(client: TestClient, db_session: Session):
    """
    Rule 11: Financial audit returns accurate total_spent, unspent_balance,
    expenditure_percentage, and funding_percentage.
    """
    # funding_target: 100,000 NGN (10,000,000 kobo), amount_raised: 50,000 NGN (5,000,000 kobo) -> 50% funded
    project, owner = seed_funded_project(db_session, amount_raised=5_000_000, funding_target=10_000_000)
    owner_token = create_user_token(client, owner.email)

    # Before expenses: 0 spent
    audit1 = client.get(f"/api/projects/{project.id}/financial-audit").json()
    assert audit1["total_spent"] == 0
    assert audit1["unspent_balance"] == 5_000_000
    assert audit1["expenditure_percentage"] == 0.0
    assert audit1["funding_percentage"] == 50.0

    # Log 2,000,000 kobo expense (40% of 5,000,000 raised)
    client.post(
        f"/api/projects/{project.id}/expenses",
        json={"amount": 2_000_000, "category": "LABOR", "description": "Crew labor"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    # After expense: 2M spent, 3M unspent, 40% expenditure
    audit2 = client.get(f"/api/projects/{project.id}/financial-audit").json()
    assert audit2["total_spent"] == 2_000_000
    assert audit2["unspent_balance"] == 3_000_000
    assert audit2["expenditure_percentage"] == 40.0
    assert audit2["funding_percentage"] == 50.0


def test_financial_audit_for_non_existent_project_returns_404(client: TestClient, db_session: Session):
    """Non-existent project UUID returns 404."""
    res = client.get(f"/api/projects/{uuid.uuid4()}/financial-audit")
    assert res.status_code == 404
