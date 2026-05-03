from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from .database import Base

class TicketStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    ON_HOLD = "on_hold"
    RESOLVED = "resolved"
    CLOSED = "closed"

class Priority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(SQLEnum(TicketStatus), default=TicketStatus.OPEN, nullable=False)
    priority = Column(SQLEnum(Priority), default=Priority.MEDIUM, nullable=False)
    sla_deadline = Column(DateTime, nullable=True)
    response_sla_deadline = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    status_changes = relationship("StatusChangeLog", back_populates="ticket", cascade="all, delete-orphan")

class SLAConfig(Base):
    __tablename__ = "sla_configs"

    id = Column(Integer, primary_key=True, index=True)
    priority = Column(SQLEnum(Priority), unique=True, nullable=False)
    resolution_hours = Column(Integer, nullable=False)
    response_hours = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

class StatusChangeLog(Base):
    __tablename__ = "status_change_logs"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)
    from_status = Column(SQLEnum(TicketStatus), nullable=True)
    to_status = Column(SQLEnum(TicketStatus), nullable=False)
    changed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    ticket = relationship("Ticket", back_populates="status_changes")
