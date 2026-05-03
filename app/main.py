from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from contextlib import asynccontextmanager
import math
import traceback
from datetime import datetime
from .database import init_db, get_db
from .models import TicketStatus, Priority
from .schemas import (
    TicketCreate, TicketUpdate, TicketResponse,
    SLAConfigResponse, SLAConfigUpdate,
    PaginatedResponse, OverdueTicket
)
from .services import (
    init_sla_configs, create_ticket, get_ticket, get_tickets,
    update_ticket, delete_ticket, get_sla_config, get_all_sla_configs,
    update_sla_config, get_overdue_tickets, get_overdue_count,
    is_ticket_overdue, is_ticket_response_overdue, get_overdue_hours
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    async for db in get_db():
        await init_sla_configs(db)
        break
    yield

app = FastAPI(
    title="Ticket SLA API",
    description="轻量工单 SLA API，支持工单状态管理、SLA 截止时间计算和超时查询",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def build_ticket_response(ticket) -> TicketResponse:
    current_time = datetime.utcnow()
    status_changes = []
    try:
        if hasattr(ticket, 'status_changes') and ticket.status_changes:
            status_changes = list(ticket.status_changes)
    except Exception:
        pass
    
    return TicketResponse(
        id=ticket.id,
        title=ticket.title,
        description=ticket.description,
        status=ticket.status,
        priority=ticket.priority,
        sla_deadline=ticket.sla_deadline,
        response_sla_deadline=ticket.response_sla_deadline,
        is_overdue=is_ticket_overdue(ticket, current_time),
        is_response_overdue=is_ticket_response_overdue(ticket, current_time),
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        status_changes=status_changes
    )

def build_overdue_ticket(ticket) -> OverdueTicket:
    current_time = datetime.utcnow()
    return OverdueTicket(
        ticket_id=ticket.id,
        ticket_title=ticket.title,
        priority=ticket.priority,
        current_status=ticket.status,
        sla_deadline=ticket.sla_deadline,
        response_sla_deadline=ticket.response_sla_deadline,
        is_overdue=is_ticket_overdue(ticket, current_time),
        is_response_overdue=is_ticket_response_overdue(ticket, current_time),
        overdue_hours=get_overdue_hours(ticket.sla_deadline, current_time),
        response_overdue_hours=get_overdue_hours(ticket.response_sla_deadline, current_time),
        created_at=ticket.created_at
    )

@app.post("/tickets/", response_model=TicketResponse, status_code=201, summary="创建工单")
async def create_ticket_endpoint(
    ticket_data: TicketCreate,
    db: AsyncSession = Depends(get_db)
):
    try:
        ticket = await create_ticket(db, ticket_data)
        ticket = await get_ticket(db, ticket.id)
        return build_ticket_response(ticket)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建工单失败: {str(e)}")

@app.get("/tickets/", response_model=PaginatedResponse[TicketResponse], summary="获取工单列表")
async def list_tickets_endpoint(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    status: Optional[TicketStatus] = Query(None, description="按状态过滤"),
    priority: Optional[Priority] = Query(None, description="按优先级过滤"),
    db: AsyncSession = Depends(get_db)
):
    tickets, total = await get_tickets(
        db, page=page, page_size=page_size, status=status, priority=priority
    )
    total_pages = math.ceil(total / page_size) if page_size > 0 else 0
    
    ticket_responses = [build_ticket_response(ticket) for ticket in tickets]
    
    return PaginatedResponse(
        items=ticket_responses,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )

@app.get("/tickets/{ticket_id}", response_model=TicketResponse, summary="获取单个工单")
async def get_ticket_endpoint(
    ticket_id: int,
    db: AsyncSession = Depends(get_db)
):
    ticket = await get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="工单不存在")
    return build_ticket_response(ticket)

@app.put("/tickets/{ticket_id}", response_model=TicketResponse, summary="更新工单")
async def update_ticket_endpoint(
    ticket_id: int,
    update_data: TicketUpdate,
    db: AsyncSession = Depends(get_db)
):
    ticket = await update_ticket(db, ticket_id, update_data)
    if not ticket:
        raise HTTPException(status_code=404, detail="工单不存在或状态流转无效")
    ticket = await get_ticket(db, ticket.id)
    return build_ticket_response(ticket)

@app.delete("/tickets/{ticket_id}", status_code=204, summary="删除工单")
async def delete_ticket_endpoint(
    ticket_id: int,
    db: AsyncSession = Depends(get_db)
):
    success = await delete_ticket(db, ticket_id)
    if not success:
        raise HTTPException(status_code=404, detail="工单不存在")
    return None

@app.post("/tickets/{ticket_id}/status/{new_status}", response_model=TicketResponse, summary="更新工单状态")
async def update_ticket_status_endpoint(
    ticket_id: int,
    new_status: TicketStatus,
    db: AsyncSession = Depends(get_db)
):
    update_data = TicketUpdate(status=new_status)
    ticket = await update_ticket(db, ticket_id, update_data)
    if not ticket:
        raise HTTPException(status_code=404, detail="工单不存在或状态流转无效")
    ticket = await get_ticket(db, ticket.id)
    return build_ticket_response(ticket)

@app.get("/sla-configs/", response_model=List[SLAConfigResponse], summary="获取所有 SLA 配置")
async def get_sla_configs_endpoint(db: AsyncSession = Depends(get_db)):
    configs = await get_all_sla_configs(db)
    return configs

@app.get("/sla-configs/{priority}", response_model=SLAConfigResponse, summary="获取指定优先级的 SLA 配置")
async def get_sla_config_endpoint(
    priority: Priority,
    db: AsyncSession = Depends(get_db)
):
    config = await get_sla_config(db, priority)
    if not config:
        raise HTTPException(status_code=404, detail="SLA 配置不存在")
    return config

@app.put("/sla-configs/{priority}", response_model=SLAConfigResponse, summary="更新 SLA 配置")
async def update_sla_config_endpoint(
    priority: Priority,
    update_data: SLAConfigUpdate,
    db: AsyncSession = Depends(get_db)
):
    config = await update_sla_config(db, priority, update_data)
    if not config:
        raise HTTPException(status_code=404, detail="SLA 配置不存在")
    return config

@app.get("/tickets/overdue/", response_model=PaginatedResponse[OverdueTicket], summary="获取超时工单列表")
async def get_overdue_tickets_endpoint(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db)
):
    tickets, total = await get_overdue_tickets(db, page=page, page_size=page_size)
    total_pages = math.ceil(total / page_size) if page_size > 0 else 0
    
    overdue_tickets = [build_overdue_ticket(ticket) for ticket in tickets]
    
    return PaginatedResponse(
        items=overdue_tickets,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )

@app.get("/tickets/overdue/count/", response_model=dict, summary="获取超时工单数量")
async def get_overdue_count_endpoint(db: AsyncSession = Depends(get_db)):
    count = await get_overdue_count(db)
    return {"overdue_count": count}

@app.get("/health/", response_model=dict, summary="健康检查")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
