from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from .models import Ticket, SLAConfig, StatusChangeLog, TicketStatus, Priority
from .schemas import TicketCreate, TicketUpdate, SLAConfigUpdate

DEFAULT_SLA_CONFIGS = {
    Priority.LOW: {"resolution_hours": 168, "response_hours": 24},
    Priority.MEDIUM: {"resolution_hours": 72, "response_hours": 8},
    Priority.HIGH: {"resolution_hours": 24, "response_hours": 4},
    Priority.CRITICAL: {"resolution_hours": 4, "response_hours": 1},
}

VALID_STATUS_TRANSITIONS = {
    TicketStatus.OPEN: [TicketStatus.IN_PROGRESS, TicketStatus.RESOLVED, TicketStatus.CLOSED],
    TicketStatus.IN_PROGRESS: [TicketStatus.ON_HOLD, TicketStatus.RESOLVED, TicketStatus.OPEN],
    TicketStatus.ON_HOLD: [TicketStatus.IN_PROGRESS],
    TicketStatus.RESOLVED: [TicketStatus.IN_PROGRESS, TicketStatus.CLOSED],
    TicketStatus.CLOSED: [TicketStatus.IN_PROGRESS],
}

async def init_sla_configs(db: AsyncSession) -> None:
    for priority, config in DEFAULT_SLA_CONFIGS.items():
        result = await db.execute(
            select(SLAConfig).where(SLAConfig.priority == priority)
        )
        existing = result.scalar_one_or_none()
        
        if not existing:
            new_config = SLAConfig(
                priority=priority,
                resolution_hours=config["resolution_hours"],
                response_hours=config["response_hours"]
            )
            db.add(new_config)
    
    await db.commit()

def calculate_sla_deadline(
    created_at: datetime,
    sla_hours: int
) -> datetime:
    return created_at + timedelta(hours=sla_hours)

def is_overdue(deadline: Optional[datetime], current_time: Optional[datetime] = None) -> bool:
    if deadline is None:
        return False
    if current_time is None:
        current_time = datetime.utcnow()
    return current_time > deadline

def get_overdue_hours(deadline: Optional[datetime], current_time: Optional[datetime] = None) -> float:
    if deadline is None:
        return 0.0
    if current_time is None:
        current_time = datetime.utcnow()
    if current_time <= deadline:
        return 0.0
    delta = current_time - deadline
    return delta.total_seconds() / 3600.0

async def get_sla_config(db: AsyncSession, priority: Priority) -> Optional[SLAConfig]:
    result = await db.execute(
        select(SLAConfig).where(SLAConfig.priority == priority)
    )
    return result.scalar_one_or_none()

async def get_all_sla_configs(db: AsyncSession) -> List[SLAConfig]:
    result = await db.execute(select(SLAConfig))
    return result.scalars().all()

async def update_sla_config(
    db: AsyncSession,
    priority: Priority,
    update_data: SLAConfigUpdate
) -> Optional[SLAConfig]:
    config = await get_sla_config(db, priority)
    if not config:
        return None
    
    update_dict = update_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(config, key, value)
    
    await db.commit()
    return config

async def create_ticket(db: AsyncSession, ticket_data: TicketCreate) -> Ticket:
    sla_config = await get_sla_config(db, ticket_data.priority)
    if not sla_config:
        sla_config = SLAConfig(
            priority=ticket_data.priority,
            resolution_hours=DEFAULT_SLA_CONFIGS[ticket_data.priority]["resolution_hours"],
            response_hours=DEFAULT_SLA_CONFIGS[ticket_data.priority]["response_hours"]
        )
        db.add(sla_config)
        await db.flush()
    
    now = datetime.utcnow()
    new_ticket = Ticket(
        title=ticket_data.title,
        description=ticket_data.description,
        priority=ticket_data.priority,
        status=TicketStatus.OPEN,
        sla_deadline=calculate_sla_deadline(now, sla_config.resolution_hours),
        response_sla_deadline=calculate_sla_deadline(now, sla_config.response_hours),
        created_at=now,
        updated_at=now
    )
    db.add(new_ticket)
    await db.flush()
    
    initial_log = StatusChangeLog(
        ticket_id=new_ticket.id,
        from_status=None,
        to_status=TicketStatus.OPEN,
        changed_at=now
    )
    db.add(initial_log)
    
    await db.commit()
    
    return new_ticket

async def get_ticket(db: AsyncSession, ticket_id: int) -> Optional[Ticket]:
    result = await db.execute(
        select(Ticket)
        .options(selectinload(Ticket.status_changes))
        .where(Ticket.id == ticket_id)
    )
    return result.scalar_one_or_none()

async def get_tickets(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 10,
    status: Optional[TicketStatus] = None,
    priority: Optional[Priority] = None,
    include_overdue_only: bool = False
) -> Tuple[List[Ticket], int]:
    query = select(Ticket)
    
    if status:
        query = query.where(Ticket.status == status)
    if priority:
        query = query.where(Ticket.priority == priority)
    
    if include_overdue_only:
        now = datetime.utcnow()
        query = query.where(
            and_(
                Ticket.status.notin_([TicketStatus.RESOLVED, TicketStatus.CLOSED]),
                or_(
                    Ticket.sla_deadline < now,
                    Ticket.response_sla_deadline < now
                )
            )
        )
    
    count_query = select(func.count()).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total = count_result.scalar_one()
    
    query = query.options(selectinload(Ticket.status_changes))
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    tickets = result.scalars().all()
    
    return tickets, total

def is_ticket_overdue(ticket: Ticket, current_time: Optional[datetime] = None) -> bool:
    if ticket.status in [TicketStatus.RESOLVED, TicketStatus.CLOSED]:
        return False
    return is_overdue(ticket.sla_deadline, current_time)

def is_ticket_response_overdue(ticket: Ticket, current_time: Optional[datetime] = None) -> bool:
    if ticket.status in [TicketStatus.RESOLVED, TicketStatus.CLOSED]:
        return False
    if ticket.status != TicketStatus.OPEN:
        return False
    return is_overdue(ticket.response_sla_deadline, current_time)

async def update_ticket(db: AsyncSession, ticket_id: int, update_data: TicketUpdate) -> Optional[Ticket]:
    ticket = await get_ticket(db, ticket_id)
    if not ticket:
        return None
    
    old_status = ticket.status
    update_dict = update_data.model_dump(exclude_unset=True)
    
    if "status" in update_dict and update_dict["status"] != old_status:
        new_status = update_dict["status"]
        if not await validate_status_transition(db, ticket.id, old_status, new_status):
            return None
        
        status_log = StatusChangeLog(
            ticket_id=ticket.id,
            from_status=old_status,
            to_status=new_status,
            changed_at=datetime.utcnow()
        )
        db.add(status_log)
    
    for key, value in update_dict.items():
        if key == "priority" and value != ticket.priority:
            sla_config = await get_sla_config(db, value)
            if sla_config:
                ticket.sla_deadline = calculate_sla_deadline(ticket.created_at, sla_config.resolution_hours)
                ticket.response_sla_deadline = calculate_sla_deadline(ticket.created_at, sla_config.response_hours)
        setattr(ticket, key, value)
    
    ticket.updated_at = datetime.utcnow()
    await db.commit()
    
    return ticket

async def validate_status_transition(
    db: AsyncSession,
    ticket_id: int,
    from_status: TicketStatus,
    to_status: TicketStatus
) -> bool:
    if from_status == to_status:
        return True
    
    valid_transitions = VALID_STATUS_TRANSITIONS.get(from_status, [])
    return to_status in valid_transitions

async def update_ticket_status(
    db: AsyncSession,
    ticket_id: int,
    new_status: TicketStatus
) -> Optional[Ticket]:
    update_data = TicketUpdate(status=new_status)
    return await update_ticket(db, ticket_id, update_data)

async def delete_ticket(db: AsyncSession, ticket_id: int) -> bool:
    ticket = await get_ticket(db, ticket_id)
    if not ticket:
        return False
    
    await db.execute(
        delete(StatusChangeLog).where(StatusChangeLog.ticket_id == ticket_id)
    )
    
    await db.delete(ticket)
    await db.commit()
    return True

async def get_overdue_tickets(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 10
) -> Tuple[List[Ticket], int]:
    return await get_tickets(
        db,
        page=page,
        page_size=page_size,
        include_overdue_only=True
    )

async def get_overdue_count(db: AsyncSession) -> int:
    now = datetime.utcnow()
    query = select(func.count()).select_from(
        select(Ticket).where(
            and_(
                Ticket.status.notin_([TicketStatus.RESOLVED, TicketStatus.CLOSED]),
                or_(
                    Ticket.sla_deadline < now,
                    Ticket.response_sla_deadline < now
                )
            )
        ).subquery()
    )
    result = await db.execute(query)
    return result.scalar_one()
