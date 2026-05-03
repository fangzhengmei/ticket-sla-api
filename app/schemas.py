from pydantic import BaseModel, Field
from typing import Optional, List, Generic, TypeVar
from datetime import datetime
from .models import TicketStatus, Priority

T = TypeVar('T')

class TicketBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="工单标题")
    description: Optional[str] = Field(None, description="工单描述")
    priority: Priority = Field(default=Priority.MEDIUM, description="工单优先级")

class TicketCreate(TicketBase):
    pass

class TicketUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255, description="工单标题")
    description: Optional[str] = Field(None, description="工单描述")
    priority: Optional[Priority] = Field(None, description="工单优先级")
    status: Optional[TicketStatus] = Field(None, description="工单状态")

class StatusChangeLogResponse(BaseModel):
    id: int
    ticket_id: int
    from_status: Optional[TicketStatus]
    to_status: TicketStatus
    changed_at: datetime

    class Config:
        from_attributes = True

class TicketResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    status: TicketStatus
    priority: Priority
    sla_deadline: Optional[datetime]
    response_sla_deadline: Optional[datetime]
    is_overdue: bool = Field(default=False, description="是否超时")
    is_response_overdue: bool = Field(default=False, description="响应是否超时")
    created_at: datetime
    updated_at: datetime
    status_changes: List[StatusChangeLogResponse] = Field(default_factory=list, description="状态变更记录")

    class Config:
        from_attributes = True

class SLAConfigBase(BaseModel):
    priority: Priority = Field(..., description="优先级")
    resolution_hours: int = Field(..., ge=1, description="解决时间（小时）")
    response_hours: int = Field(..., ge=1, description="响应时间（小时）")

class SLAConfigResponse(SLAConfigBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class SLAConfigUpdate(BaseModel):
    resolution_hours: Optional[int] = Field(None, ge=1, description="解决时间（小时）")
    response_hours: Optional[int] = Field(None, ge=1, description="响应时间（小时）")

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int

class OverdueTicket(BaseModel):
    ticket_id: int
    ticket_title: str
    priority: Priority
    current_status: TicketStatus
    sla_deadline: Optional[datetime]
    response_sla_deadline: Optional[datetime]
    is_overdue: bool
    is_response_overdue: bool
    overdue_hours: float
    response_overdue_hours: float
    created_at: datetime

    class Config:
        from_attributes = True
