"""
Тесты /api/orders (п. 3.6, 4.4 ТЗ, раздел 8 ТЗ, сессия B14):
- создание черновика (POST), status всегда draft, version всегда 1
- версионирование: правка fields в draft не меняет version; правка после
  pending_approval сбрасывает в draft, version += 1, старая версия
  архивируется в OrderHistory
- права на редактирование fields — только автор
- переходы FSM: draft -> pending_approval -> approved/rejected -> executed,
  запрет переходов вне этой схемы (409)
- согласование ограничено ролями IT-Head/Executive независимо от
  DocumentTemplate.min_approver_role (регрессия на баг, найденный в
  ручном тестировании B14 — шаблон с min_approver_role=Engineer не должен
  разрешать Engineer согласовывать документ)
- ранжировка согласующих: IT-Head не может согласовать документ с порогом
  Executive, но Executive может согласовать документ с порогом IT-Head
- доступ по ролям на уровне роутера: User — 403
- фильтр по status в GET /api/orders
- 404 на несуществующий order_id
"""
import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.models.department import Department
from app.models.document_template import DocumentTemplate, DocumentTemplateType
from app.models.order_history import OrderHistory
from app.models.user import User, UserRole


def _auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(user.id, user.role.value)
    return {"Authorization": f"Bearer {token}"}


def _make_user(db_session: Session, department: Department, role: UserRole) -> User:
    user = User(
        full_name=f"Тестовый {role.value}",
        department_id=department.id,
        role=role,
        login=f"test_{role.name.lower()}_{uuid.uuid4().hex[:8]}",
        password_hash=hash_password("TestPassword123!"),
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _make_template(
    db_session: Session,
    *,
    type_: DocumentTemplateType = DocumentTemplateType.WORK_ORDER,
    min_approver_role: UserRole = UserRole.IT_HEAD,
) -> DocumentTemplate:
    template = DocumentTemplate(
        name=f"Тестовый шаблон {type_.value}",
        type=type_,
        file_path=f"/app/templates/orders/test_{uuid.uuid4().hex[:8]}.docx",
        field_schema={},
        min_approver_role=min_approver_role,
    )
    db_session.add(template)
    db_session.commit()
    db_session.refresh(template)
    return template


def _create_order(
    client: TestClient, author: User, template: DocumentTemplate, fields: dict | None = None
) -> dict:
    response = client.post(
        "/api/orders",
        json={
            "type": template.type.value,
            "template_id": str(template.id),
            "fields": fields or {"field": "значение"},
        },
        headers=_auth_headers(author),
    )
    assert response.status_code == 201
    return response.json()


def test_create_order_sets_status_draft_and_version_1(
    client: TestClient, db_session: Session, engineer_user: User
) -> None:
    template = _make_template(db_session)

    order = _create_order(client, engineer_user, template)

    assert order["status"] == "draft"
    assert order["version"] == 1
    assert order["author"]["id"] == str(engineer_user.id)
    assert order["approver"] is None


def test_list_orders_forbidden_for_user_role(
    client: TestClient, db_session: Session, department: Department
) -> None:
    shadow_user = _make_user(db_session, department, UserRole.USER)

    response = client.get("/api/orders", headers=_auth_headers(shadow_user))

    assert response.status_code == 403


def test_edit_fields_in_draft_does_not_bump_version(
    client: TestClient, db_session: Session, engineer_user: User
) -> None:
    template = _make_template(db_session)
    order = _create_order(client, engineer_user, template)

    response = client.patch(
        f"/api/orders/{order['id']}",
        json={"fields": {"field": "новое значение"}},
        headers=_auth_headers(engineer_user),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "draft"
    assert body["version"] == 1


def test_edit_fields_after_pending_approval_resets_to_draft_and_archives_history(
    client: TestClient, db_session: Session, engineer_user: User
) -> None:
    template = _make_template(db_session)
    order = _create_order(client, engineer_user, template, fields={"field": "исходное"})
    headers = _auth_headers(engineer_user)
    client.patch(f"/api/orders/{order['id']}", json={"status": "pending_approval"}, headers=headers)

    response = client.patch(
        f"/api/orders/{order['id']}",
        json={"fields": {"field": "правка после отправки"}},
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "draft"
    assert body["version"] == 2

    history = (
        db_session.query(OrderHistory)
        .filter(OrderHistory.order_id == uuid.UUID(order["id"]))
        .one()
    )
    assert history.version == 1
    assert history.fields == {"field": "исходное"}
    assert history.changed_by == engineer_user.id


def test_non_author_cannot_edit_fields(
    client: TestClient, db_session: Session, department: Department, engineer_user: User
) -> None:
    template = _make_template(db_session)
    order = _create_order(client, engineer_user, template)
    other_engineer = _make_user(db_session, department, UserRole.ENGINEER)

    response = client.patch(
        f"/api/orders/{order['id']}",
        json={"fields": {"field": "чужая правка"}},
        headers=_auth_headers(other_engineer),
    )

    assert response.status_code == 403


def test_engineer_cannot_approve_even_when_template_min_approver_role_is_engineer(
    client: TestClient, db_session: Session, department: Department, engineer_user: User
) -> None:
    """Регрессия на баг B14: DocumentTemplate.min_approver_role=Engineer не должен
    расширять круг согласующих за пределы {IT-Head, Executive} (раздел 8 ТЗ —
    правило безусловное)."""
    template = _make_template(db_session, min_approver_role=UserRole.ENGINEER)
    order = _create_order(client, engineer_user, template)
    headers = _auth_headers(engineer_user)
    client.patch(f"/api/orders/{order['id']}", json={"status": "pending_approval"}, headers=headers)

    other_engineer = _make_user(db_session, department, UserRole.ENGINEER)
    response = client.patch(
        f"/api/orders/{order['id']}",
        json={"status": "approved"},
        headers=_auth_headers(other_engineer),
    )

    assert response.status_code == 403


def test_it_head_can_approve_when_template_requires_it_head(
    client: TestClient, db_session: Session, department: Department, engineer_user: User
) -> None:
    template = _make_template(db_session, min_approver_role=UserRole.IT_HEAD)
    order = _create_order(client, engineer_user, template)
    headers = _auth_headers(engineer_user)
    client.patch(f"/api/orders/{order['id']}", json={"status": "pending_approval"}, headers=headers)

    it_head = _make_user(db_session, department, UserRole.IT_HEAD)
    response = client.patch(
        f"/api/orders/{order['id']}",
        json={"status": "approved"},
        headers=_auth_headers(it_head),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "approved"
    assert body["approver"]["id"] == str(it_head.id)
    assert body["approved_at"] is not None


def test_it_head_cannot_approve_when_template_requires_executive(
    client: TestClient, db_session: Session, department: Department, engineer_user: User
) -> None:
    """Ранжировка согласующих: порог Executive не проходится ролью IT-Head."""
    template = _make_template(db_session, min_approver_role=UserRole.EXECUTIVE)
    order = _create_order(client, engineer_user, template)
    headers = _auth_headers(engineer_user)
    client.patch(f"/api/orders/{order['id']}", json={"status": "pending_approval"}, headers=headers)

    it_head = _make_user(db_session, department, UserRole.IT_HEAD)
    response = client.patch(
        f"/api/orders/{order['id']}",
        json={"status": "approved"},
        headers=_auth_headers(it_head),
    )

    assert response.status_code == 403


def test_executive_can_approve_when_template_requires_it_head(
    client: TestClient, db_session: Session, department: Department, engineer_user: User
) -> None:
    """Ранжировка согласующих: более высокая роль (Executive) проходит
    более низкий порог (IT-Head)."""
    template = _make_template(db_session, min_approver_role=UserRole.IT_HEAD)
    order = _create_order(client, engineer_user, template)
    headers = _auth_headers(engineer_user)
    client.patch(f"/api/orders/{order['id']}", json={"status": "pending_approval"}, headers=headers)

    executive = _make_user(db_session, department, UserRole.EXECUTIVE)
    response = client.patch(
        f"/api/orders/{order['id']}",
        json={"status": "approved"},
        headers=_auth_headers(executive),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "approved"


def test_author_marks_approved_order_as_executed(
    client: TestClient, db_session: Session, department: Department, engineer_user: User
) -> None:
    template = _make_template(db_session)
    order = _create_order(client, engineer_user, template)
    author_headers = _auth_headers(engineer_user)
    client.patch(f"/api/orders/{order['id']}", json={"status": "pending_approval"}, headers=author_headers)
    it_head = _make_user(db_session, department, UserRole.IT_HEAD)
    client.patch(f"/api/orders/{order['id']}", json={"status": "approved"}, headers=_auth_headers(it_head))

    response = client.patch(
        f"/api/orders/{order['id']}", json={"status": "executed"}, headers=author_headers
    )

    assert response.status_code == 200
    assert response.json()["status"] == "executed"


def test_invalid_transition_from_terminal_status_returns_409(
    client: TestClient, db_session: Session, department: Department, engineer_user: User
) -> None:
    template = _make_template(db_session)
    order = _create_order(client, engineer_user, template)
    author_headers = _auth_headers(engineer_user)
    client.patch(f"/api/orders/{order['id']}", json={"status": "pending_approval"}, headers=author_headers)
    it_head = _make_user(db_session, department, UserRole.IT_HEAD)
    client.patch(f"/api/orders/{order['id']}", json={"status": "approved"}, headers=_auth_headers(it_head))
    client.patch(f"/api/orders/{order['id']}", json={"status": "executed"}, headers=author_headers)

    response = client.patch(
        f"/api/orders/{order['id']}", json={"status": "approved"}, headers=author_headers
    )

    assert response.status_code == 409


def test_patch_order_not_found(client: TestClient, engineer_user: User) -> None:
    response = client.patch(
        f"/api/orders/{uuid.uuid4()}",
        json={"status": "pending_approval"},
        headers=_auth_headers(engineer_user),
    )

    assert response.status_code == 404


def test_list_orders_filters_by_status(
    client: TestClient, db_session: Session, department: Department, engineer_user: User
) -> None:
    template = _make_template(db_session)
    executed_order = _create_order(client, engineer_user, template)
    draft_order = _create_order(client, engineer_user, template)
    author_headers = _auth_headers(engineer_user)
    client.patch(
        f"/api/orders/{executed_order['id']}", json={"status": "pending_approval"}, headers=author_headers
    )
    it_head = _make_user(db_session, department, UserRole.IT_HEAD)
    client.patch(
        f"/api/orders/{executed_order['id']}", json={"status": "approved"}, headers=_auth_headers(it_head)
    )
    client.patch(
        f"/api/orders/{executed_order['id']}", json={"status": "executed"}, headers=author_headers
    )

    all_response = client.get("/api/orders", headers=author_headers)
    assert all_response.json()["total"] == 2

    filtered_response = client.get("/api/orders?status=executed", headers=author_headers)

    assert filtered_response.status_code == 200
    body = filtered_response.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == executed_order["id"]
    assert draft_order["id"] not in [item["id"] for item in body["items"]]


# --- GET /api/document-templates (B14a) ---


def test_list_document_templates_returns_all(
    client: TestClient, db_session: Session, engineer_user: User
) -> None:
    _make_template(db_session, type_=DocumentTemplateType.PURCHASE_REQUEST)
    _make_template(db_session, type_=DocumentTemplateType.WORK_ORDER)

    response = client.get("/api/document-templates", headers=_auth_headers(engineer_user))

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert {"id", "name", "type", "field_schema", "min_approver_role"} <= body[0].keys()


def test_list_document_templates_forbidden_for_user_role(
    client: TestClient, db_session: Session, department: Department
) -> None:
    shadow_user = _make_user(db_session, department, UserRole.USER)

    response = client.get("/api/document-templates", headers=_auth_headers(shadow_user))

    assert response.status_code == 403


# --- GET /api/orders/{id}/history (B14a) ---


def test_order_history_returns_versions_in_order(
    client: TestClient, db_session: Session, engineer_user: User
) -> None:
    template = _make_template(db_session)
    order = _create_order(client, engineer_user, template, fields={"field": "v1"})
    headers = _auth_headers(engineer_user)
    client.patch(f"/api/orders/{order['id']}", json={"status": "pending_approval"}, headers=headers)
    client.patch(f"/api/orders/{order['id']}", json={"fields": {"field": "v2"}}, headers=headers)
    client.patch(f"/api/orders/{order['id']}", json={"status": "pending_approval"}, headers=headers)
    client.patch(f"/api/orders/{order['id']}", json={"fields": {"field": "v3"}}, headers=headers)

    response = client.get(f"/api/orders/{order['id']}/history", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert body[0]["version"] == 1
    assert body[0]["fields"] == {"field": "v1"}
    assert body[1]["version"] == 2
    assert body[1]["fields"] == {"field": "v2"}
    assert body[0]["changed_by_user"]["id"] == str(engineer_user.id)


def test_order_history_empty_for_never_edited_order(
    client: TestClient, db_session: Session, engineer_user: User
) -> None:
    template = _make_template(db_session)
    order = _create_order(client, engineer_user, template)

    response = client.get(
        f"/api/orders/{order['id']}/history", headers=_auth_headers(engineer_user)
    )

    assert response.status_code == 200
    assert response.json() == []


def test_order_history_not_found_for_unknown_order_id(
    client: TestClient, engineer_user: User
) -> None:
    response = client.get(
        f"/api/orders/{uuid.uuid4()}/history", headers=_auth_headers(engineer_user)
    )

    assert response.status_code == 404
