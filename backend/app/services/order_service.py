r"""
Сервисный слой для Order — по п. 3.6, разделу 8 ТЗ, сессия B14 посессионного плана.

FSM статусов: draft -> pending_approval -> approved -> executed
                                        \-> rejected (терминальный)
(rejected и executed — терминальные статусы, дальнейших переходов из них нет).

Роли в жизненном цикле:
  - автор (order.author_id) — правит fields (пока draft/pending_approval),
    отправляет на согласование (draft -> pending_approval),
    отмечает исполнение (approved -> executed);
  - согласующий — approve/reject (pending_approval -> approved/rejected);
    кто именно может согласовывать конкретный Order, определяется
    DocumentTemplate.min_approver_role (см. _can_approve ниже) — специально
    НЕ хардкодится в api/orders.py, чтобы при появлении новых типов
    документов с другими правилами менять только этот файл (риск,
    отмеченный в посессионном плане для B14).

Версионирование (раздел 8 ТЗ): редактирование fields, когда Order уже
находится в pending_approval, — это фактически "отзыв на доработку":
старая версия полей архивируется в OrderHistory, статус сбрасывается
в draft, version увеличивается на 1. Правка fields, пока Order ещё
ни разу не отправлялся на согласование (статус draft), version не трогает
и в историю не пишет — версионируем только то, что уже "было на утверждении".
"""
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.order import Order, OrderStatus
from app.models.order_history import OrderHistory
from app.models.user import User, UserRole
from app.schemas.order import OrderCreate, OrderUpdate


class OrderPermissionError(Exception):
    """Поднимается, если пользователь пытается выполнить действие, на которое
    не имеет права (правка fields не-автором, approve/reject без нужной роли,
    executed не-автором). Обрабатывается в api/orders.py как 403 Forbidden."""


class OrderInvalidTransitionError(Exception):
    """Поднимается при попытке недопустимого перехода FSM (в т.ч. правка fields
    в терминальном статусе approved/executed/rejected). Обрабатывается в
    api/orders.py как 409 Conflict — по аналогии с бизнес-правилом блокировки
    списания Asset в asset_service."""


# Ранжировка ролей-согласующих. Роли, которых здесь нет (Engineer, User, Admin),
# согласовывать Order не могут ни при каком min_approver_role.
_APPROVER_RANKS: dict[UserRole, int] = {
    UserRole.IT_HEAD: 1,
    UserRole.EXECUTIVE: 2,
}

# Допустимые переходы FSM. Ключ — текущий статус, значение — множество
# статусов, в которые из него можно перейти одним PATCH.
_ALLOWED_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.DRAFT: {OrderStatus.PENDING_APPROVAL},
    OrderStatus.PENDING_APPROVAL: {OrderStatus.APPROVED, OrderStatus.REJECTED},
    OrderStatus.APPROVED: {OrderStatus.EXECUTED},
}

# Статусы, в которых редактирование fields в принципе допустимо.
_EDITABLE_STATUSES = {OrderStatus.DRAFT, OrderStatus.PENDING_APPROVAL}


def _can_approve(user_role: UserRole, min_approver_role: UserRole) -> bool:
    """Достаточно ли ранга роли пользователя, чтобы согласовать документ
    с данным DocumentTemplate.min_approver_role.

    Раздел 8 ТЗ: согласовывать может ТОЛЬКО IT-Head или Executive — это
    правило безусловное и не зависит от значения min_approver_role.
    min_approver_role лишь дополнительно сужает круг из этих двух ролей
    (например, "не ниже Executive"). Если в DocumentTemplate по ошибке
    указана любая другая роль (как обнаружилось на сид-шаблоне
    "Наряд на работу" с min_approver_role=Engineer) — она не должна
    расширять круг согласующих за пределы {IT-Head, Executive}, поэтому
    для неё явно берётся минимальный легальный порог (IT-Head).
    """
    if user_role not in _APPROVER_RANKS:
        return False
    required_rank = _APPROVER_RANKS.get(min_approver_role, _APPROVER_RANKS[UserRole.IT_HEAD])
    return _APPROVER_RANKS[user_role] >= required_rank


def _apply_filters(
    query: Any,
    *,
    status: OrderStatus | None,
    type_: Any | None,
) -> Any:
    """Применяет общий набор фильтров и к count-запросу, и к запросу за
    данными — чтобы условия не расходились между total и items (по аналогии
    с ticket_service._apply_filters)."""
    if status is not None:
        query = query.where(Order.status == status)
    if type_ is not None:
        query = query.where(Order.type == type_)
    return query


def list_orders(
    db: Session,
    *,
    status: OrderStatus | None = None,
    type_: Any | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Order], int]:
    """Возвращает (items, total) с учётом фильтров status/type и пагинации."""
    from sqlalchemy import func

    count_query = _apply_filters(
        select(func.count()).select_from(Order), status=status, type_=type_,
    )
    total = db.execute(count_query).scalar_one()

    query = select(Order).options(
        selectinload(Order.author),
        selectinload(Order.approver),
        selectinload(Order.template),
    )
    query = _apply_filters(query, status=status, type_=type_)
    query = query.order_by(Order.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    items = list(db.execute(query).scalars().all())

    return items, total


def get_order(db: Session, order_id: uuid.UUID) -> Order | None:
    """Возвращает Order по id с подгруженными author/approver/template."""
    query = (
        select(Order)
        .where(Order.id == order_id)
        .options(
            selectinload(Order.author),
            selectinload(Order.approver),
            selectinload(Order.template),
        )
    )
    return db.execute(query).scalar_one_or_none()


def get_order_history(db: Session, order_id: uuid.UUID) -> list[OrderHistory]:
    """Возвращает версии OrderHistory для документа в хронологическом порядке
    (по возрастанию version) — для Timeline на карточке (B14a)."""
    query = (
        select(OrderHistory)
        .where(OrderHistory.order_id == order_id)
        .options(selectinload(OrderHistory.changed_by_user))
        .order_by(OrderHistory.version)
    )
    return list(db.execute(query).scalars().all())


def create_order(db: Session, data: OrderCreate, author_id: uuid.UUID) -> Order:
    """Создаёт черновик Order. status всегда DRAFT, version всегда 1 —
    оба поля проставляются здесь, а не приходят из OrderCreate."""
    order = Order(
        type=data.type,
        template_id=data.template_id,
        fields=data.fields,
        author_id=author_id,
        status=OrderStatus.DRAFT,
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def _archive_current_version(db: Session, order: Order, changed_by: uuid.UUID) -> None:
    """Снимает снапшот текущей (ещё не изменённой) версии fields в OrderHistory,
    перед тем как поверх неё будут применены новые значения."""
    db.add(
        OrderHistory(
            order_id=order.id,
            version=order.version,
            fields=order.fields,
            changed_by=changed_by,
            changed_at=datetime.now(timezone.utc),
        )
    )


def update_order(
    db: Session,
    order: Order,
    data: OrderUpdate,
    current_user: User,
) -> Order:
    """Частично обновляет Order (PATCH-семантика — только переданные поля).

    Обрабатывает два независимых, но комбинируемых в одном запросе сценария:
      1. Правка fields (только автор, только пока статус в _EDITABLE_STATUSES).
         Если на момент правки статус был pending_approval — это "отзыв на
         доработку": архивируем текущую версию в OrderHistory, сбрасываем
         статус в draft, увеличиваем version. Если статус уже был draft —
         просто подставляем новые fields, без архивации и инкремента.
      2. Смена status (переход FSM). Проверяется ПОСЛЕ применения правки fields
         выше — так что автор может одним PATCH и отредактировать поля, и
         сразу отправить документ на согласование (fields + status=pending_approval).
         Права на конкретный переход зависят от его типа:
           - -> pending_approval: только автор;
           - -> approved / rejected: только тот, чья роль проходит
             _can_approve() относительно order.template.min_approver_role;
           - -> executed: только автор (см. пояснение в шапке файла).
    """
    update_data = data.model_dump(exclude_unset=True)

    if "fields" in update_data:
        if current_user.id != order.author_id:
            raise OrderPermissionError("Редактировать поля документа может только автор")
        if order.status not in _EDITABLE_STATUSES:
            raise OrderInvalidTransitionError(
                f"Нельзя редактировать поля документа в статусе {order.status.value}"
            )
        if order.status == OrderStatus.PENDING_APPROVAL:
            _archive_current_version(db, order, changed_by=current_user.id)
            order.status = OrderStatus.DRAFT
            order.version += 1
        order.fields = update_data["fields"]

    if "status" in update_data:
        target = update_data["status"]
        allowed = _ALLOWED_TRANSITIONS.get(order.status, set())
        if target not in allowed:
            raise OrderInvalidTransitionError(
                f"Переход {order.status.value} -> {target.value} недопустим"
            )

        if target == OrderStatus.PENDING_APPROVAL:
            if current_user.id != order.author_id:
                raise OrderPermissionError("Отправить документ на согласование может только автор")
            order.status = target

        elif target in (OrderStatus.APPROVED, OrderStatus.REJECTED):
            if not _can_approve(current_user.role, order.template.min_approver_role):
                raise OrderPermissionError(
                    "Недостаточно прав для согласования документа этого типа"
                )
            order.status = target
            order.approver_id = current_user.id
            if target == OrderStatus.APPROVED:
                order.approved_at = datetime.now(timezone.utc)

        elif target == OrderStatus.EXECUTED:
            if current_user.id != order.author_id:
                raise OrderPermissionError("Отметить документ исполненным может только автор")
            order.status = target

    db.commit()
    db.refresh(order)
    return order
