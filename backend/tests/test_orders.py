"""
Тесты /api/orders (п. 3.6, 4.4 ТЗ, раздел 8 ТЗ, сессии B14, B14a, B16):
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
- ранжировка согласующих: IT-Head не может согласовывать документ с порогом
  Executive, но Executive может согласовывать документ с порогом IT-Head
- доступ по ролям на уровне роутера: User — 403
- фильтры по status и type, пагинация в GET /api/orders
- 404 на несуществующий order_id
- B16: ветка reject, недопустимые переходы FSM (409), правка fields в
  терминальных статусах (409), права не-автора и Admin, комбинированный PATCH
  (fields + status), сквозное версионирование
"""
import uuid

import pytest
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
        field_schema=[],
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


# --- B16: добор покрытия жизненного цикла и прав (раздел 8 ТЗ) ---


def _order_in_status(
    client: TestClient,
    db_session: Session,
    department: Department,
    author: User,
    template: DocumentTemplate,
    target: str,
) -> dict:
    """Проводит новый Order по легальному пути FSM до нужного статуса.

    Каждый шаг проверяется на 200, чтобы ошибка подготовки не маскировалась под
    результат самого теста. Возвращает исходный dict заказа (id не меняется)."""
    order = _create_order(client, author, template)
    if target == "draft":
        return order

    author_headers = _auth_headers(author)
    response = client.patch(
        f"/api/orders/{order['id']}", json={"status": "pending_approval"}, headers=author_headers
    )
    assert response.status_code == 200
    if target == "pending_approval":
        return order

    approver = _make_user(db_session, department, UserRole.IT_HEAD)
    resolution = "rejected" if target == "rejected" else "approved"
    response = client.patch(
        f"/api/orders/{order['id']}", json={"status": resolution}, headers=_auth_headers(approver)
    )
    assert response.status_code == 200
    if target in ("approved", "rejected"):
        return order

    response = client.patch(
        f"/api/orders/{order['id']}", json={"status": "executed"}, headers=author_headers
    )
    assert response.status_code == 200
    return order


def test_it_head_can_reject_and_approved_at_stays_empty(
    client: TestClient, db_session: Session, department: Department, engineer_user: User
) -> None:
    template = _make_template(db_session, min_approver_role=UserRole.IT_HEAD)
    order = _order_in_status(client, db_session, department, engineer_user, template, "pending_approval")
    it_head = _make_user(db_session, department, UserRole.IT_HEAD)

    response = client.patch(
        f"/api/orders/{order['id']}", json={"status": "rejected"}, headers=_auth_headers(it_head)
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "rejected"
    assert body["approver"]["id"] == str(it_head.id)
    assert body["approved_at"] is None


def test_it_head_cannot_reject_when_template_requires_executive(
    client: TestClient, db_session: Session, department: Department, engineer_user: User
) -> None:
    """Порог Executive действует и на reject, не только на approve (общая ветка _can_approve)."""
    template = _make_template(db_session, min_approver_role=UserRole.EXECUTIVE)
    order = _order_in_status(client, db_session, department, engineer_user, template, "pending_approval")
    it_head = _make_user(db_session, department, UserRole.IT_HEAD)

    response = client.patch(
        f"/api/orders/{order['id']}", json={"status": "rejected"}, headers=_auth_headers(it_head)
    )

    assert response.status_code == 403


@pytest.mark.parametrize(
    ("role", "target"),
    [
        (UserRole.ADMIN, "approved"),
        (UserRole.ADMIN, "rejected"),
        (UserRole.ENGINEER, "rejected"),
    ],
)
def test_role_outside_approvers_cannot_resolve_order(
    client: TestClient,
    db_session: Session,
    department: Department,
    engineer_user: User,
    role: UserRole,
    target: str,
) -> None:
    """Раздел 8 ТЗ: согласует/отклоняет только IT-Head или Executive. Admin проходит
    доступ к роутеру, но в _APPROVER_RANKS его нет — итоговый отказ на уровне сервиса."""
    template = _make_template(db_session, min_approver_role=UserRole.IT_HEAD)
    order = _order_in_status(client, db_session, department, engineer_user, template, "pending_approval")
    outsider = _make_user(db_session, department, role)

    response = client.patch(
        f"/api/orders/{order['id']}", json={"status": target}, headers=_auth_headers(outsider)
    )

    assert response.status_code == 403


@pytest.mark.parametrize(
    ("current", "target"),
    [
        ("draft", "approved"),
        ("draft", "rejected"),
        ("draft", "executed"),
        ("pending_approval", "executed"),
        ("approved", "rejected"),
        ("approved", "pending_approval"),
        ("rejected", "approved"),
        ("rejected", "pending_approval"),
        ("executed", "rejected"),
    ],
)
def test_transition_outside_fsm_returns_409(
    client: TestClient,
    db_session: Session,
    department: Department,
    engineer_user: User,
    current: str,
    target: str,
) -> None:
    template = _make_template(db_session)
    order = _order_in_status(client, db_session, department, engineer_user, template, current)

    response = client.patch(
        f"/api/orders/{order['id']}",
        json={"status": target},
        headers=_auth_headers(engineer_user),
    )

    assert response.status_code == 409


@pytest.mark.parametrize("current", ["approved", "rejected", "executed"])
def test_edit_fields_outside_editable_statuses_returns_409(
    client: TestClient,
    db_session: Session,
    department: Department,
    engineer_user: User,
    current: str,
) -> None:
    template = _make_template(db_session)
    order = _order_in_status(client, db_session, department, engineer_user, template, current)

    response = client.patch(
        f"/api/orders/{order['id']}",
        json={"fields": {"field": "правка после решения"}},
        headers=_auth_headers(engineer_user),
    )

    assert response.status_code == 409


def test_non_author_cannot_submit_for_approval(
    client: TestClient, db_session: Session, department: Department, engineer_user: User
) -> None:
    template = _make_template(db_session)
    order = _create_order(client, engineer_user, template)
    other_engineer = _make_user(db_session, department, UserRole.ENGINEER)

    response = client.patch(
        f"/api/orders/{order['id']}",
        json={"status": "pending_approval"},
        headers=_auth_headers(other_engineer),
    )

    assert response.status_code == 403


def test_approver_cannot_mark_order_executed(
    client: TestClient, db_session: Session, department: Department, engineer_user: User
) -> None:
    """Исполнение отмечает только автор (допущение B14), а не согласующий."""
    template = _make_template(db_session, min_approver_role=UserRole.IT_HEAD)
    order = _order_in_status(client, db_session, department, engineer_user, template, "approved")
    it_head = _make_user(db_session, department, UserRole.IT_HEAD)

    response = client.patch(
        f"/api/orders/{order['id']}", json={"status": "executed"}, headers=_auth_headers(it_head)
    )

    assert response.status_code == 403


def test_combined_patch_in_draft_edits_fields_and_submits_without_version_bump(
    client: TestClient, db_session: Session, engineer_user: User
) -> None:
    template = _make_template(db_session)
    order = _create_order(client, engineer_user, template, fields={"field": "старое"})

    response = client.patch(
        f"/api/orders/{order['id']}",
        json={"fields": {"field": "новое"}, "status": "pending_approval"},
        headers=_auth_headers(engineer_user),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "pending_approval"
    assert body["version"] == 1
    assert body["fields"] == {"field": "новое"}
    history_count = (
        db_session.query(OrderHistory)
        .filter(OrderHistory.order_id == uuid.UUID(order["id"]))
        .count()
    )
    assert history_count == 0


def test_combined_patch_in_pending_approval_archives_and_resubmits(
    client: TestClient, db_session: Session, department: Department, engineer_user: User
) -> None:
    """Правка fields + status=pending_approval одним PATCH из pending_approval:
    старая версия архивируется, version=2, итоговый статус снова pending_approval."""
    template = _make_template(db_session)
    order = _order_in_status(client, db_session, department, engineer_user, template, "pending_approval")

    response = client.patch(
        f"/api/orders/{order['id']}",
        json={"fields": {"field": "доработано"}, "status": "pending_approval"},
        headers=_auth_headers(engineer_user),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "pending_approval"
    assert body["version"] == 2
    history = (
        db_session.query(OrderHistory)
        .filter(OrderHistory.order_id == uuid.UUID(order["id"]))
        .one()
    )
    assert history.version == 1
    assert history.fields == {"field": "значение"}


def test_version_reaches_3_after_two_rework_cycles(
    client: TestClient, db_session: Session, engineer_user: User
) -> None:
    template = _make_template(db_session)
    order = _create_order(client, engineer_user, template, fields={"field": "v1"})
    headers = _auth_headers(engineer_user)

    client.patch(f"/api/orders/{order['id']}", json={"status": "pending_approval"}, headers=headers)
    client.patch(f"/api/orders/{order['id']}", json={"fields": {"field": "v2"}}, headers=headers)
    client.patch(f"/api/orders/{order['id']}", json={"status": "pending_approval"}, headers=headers)
    response = client.patch(
        f"/api/orders/{order['id']}", json={"fields": {"field": "v3"}}, headers=headers
    )

    assert response.status_code == 200
    body = response.json()
    assert body["version"] == 3
    assert body["status"] == "draft"


def test_list_orders_filters_by_type(
    client: TestClient, db_session: Session, engineer_user: User
) -> None:
    purchase_template = _make_template(db_session, type_=DocumentTemplateType.PURCHASE_REQUEST)
    work_template = _make_template(db_session, type_=DocumentTemplateType.WORK_ORDER)
    purchase_order = _create_order(client, engineer_user, purchase_template)
    _create_order(client, engineer_user, work_template)
    _create_order(client, engineer_user, work_template)

    response = client.get(
        f"/api/orders?type={DocumentTemplateType.PURCHASE_REQUEST.value}",
        headers=_auth_headers(engineer_user),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == purchase_order["id"]


def test_list_orders_pagination(
    client: TestClient, db_session: Session, engineer_user: User
) -> None:
    template = _make_template(db_session)
    for _ in range(3):
        _create_order(client, engineer_user, template)
    headers = _auth_headers(engineer_user)

    page_1 = client.get("/api/orders?page=1&page_size=2", headers=headers).json()
    page_2 = client.get("/api/orders?page=2&page_size=2", headers=headers).json()

    assert page_1["total"] == 3
    assert page_2["total"] == 3
    assert len(page_1["items"]) == 2
    assert len(page_2["items"]) == 1
    ids_1 = {item["id"] for item in page_1["items"]}
    ids_2 = {item["id"] for item in page_2["items"]}
    assert ids_1.isdisjoint(ids_2)


def test_executive_can_list_orders(
    client: TestClient, db_session: Session, department: Department
) -> None:
    """Executive явно включён в доступ к роутеру (докстринг api/orders.py) —
    иначе он не смог бы дойти до согласования."""
    executive = _make_user(db_session, department, UserRole.EXECUTIVE)

    response = client.get("/api/orders", headers=_auth_headers(executive))

    assert response.status_code == 200
