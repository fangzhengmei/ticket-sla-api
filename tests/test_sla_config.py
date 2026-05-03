import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

class TestSLAConfig:
    @pytest.mark.asyncio
    async def test_default_sla_configs_exist(self, client):
        response = await client.get("/sla-configs/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) == 4
        
        priorities = [config["priority"] for config in data]
        assert "low" in priorities
        assert "medium" in priorities
        assert "high" in priorities
        assert "critical" in priorities

    @pytest.mark.asyncio
    async def test_get_sla_config_by_priority(self, client):
        response = await client.get("/sla-configs/high")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["priority"] == "high"
        assert data["resolution_hours"] > 0
        assert data["response_hours"] > 0

    @pytest.mark.asyncio
    async def test_get_nonexistent_sla_config(self, client):
        response = await client.get("/sla-configs/invalid")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_update_sla_config(self, client):
        new_resolution_hours = 48
        new_response_hours = 6
        
        response = await client.put(
            "/sla-configs/medium",
            json={"resolution_hours": new_resolution_hours, "response_hours": new_response_hours}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["resolution_hours"] == new_resolution_hours
        assert data["response_hours"] == new_response_hours

    @pytest.mark.asyncio
    async def test_update_sla_config_partial(self, client):
        new_resolution_hours = 72
        
        response = await client.put(
            "/sla-configs/low",
            json={"resolution_hours": new_resolution_hours}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["resolution_hours"] == new_resolution_hours

    @pytest.mark.asyncio
    async def test_create_duplicate_sla_config_fails(self, client):
        response = await client.put(
            "/sla-configs/high",
            json={"resolution_hours": 100}
        )
        assert response.status_code == 200
        
        response = await client.put(
            "/sla-configs/high",
            json={"resolution_hours": 200}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["resolution_hours"] == 200

    @pytest.mark.asyncio
    async def test_updated_sla_affects_new_tickets(self, client):
        new_resolution_hours = 10
        
        response = await client.put(
            "/sla-configs/critical",
            json={"resolution_hours": new_resolution_hours, "response_hours": 1}
        )
        assert response.status_code == 200
        
        response = await client.post("/tickets/", json={
            "title": "测试 SLA 工单",
            "priority": "critical"
        })
        assert response.status_code == 201
        data = response.json()
        
        created = datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
        deadline = datetime.fromisoformat(data["sla_deadline"].replace("Z", "+00:00"))
        hours_diff = (deadline - created).total_seconds() / 3600
        
        assert abs(hours_diff - new_resolution_hours) < 1

class TestOverdueQueries:
    @pytest.mark.asyncio
    async def test_empty_overdue_tickets(self, client):
        response = await client.get("/tickets/overdue/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 0
        assert len(data["items"]) == 0

    @pytest.mark.asyncio
    async def test_overdue_count_zero(self, client):
        response = await client.get("/tickets/overdue/count/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["overdue_count"] == 0

    @pytest.mark.asyncio
    async def test_active_tickets_in_overdue_query(self, client, test_db):
        from app.models import Ticket, Priority, TicketStatus
        from app.services import calculate_sla_deadline
        
        now = datetime.utcnow()
        past_deadline = now - timedelta(hours=10)
        
        ticket = Ticket(
            title="超时工单",
            description="这是一个超时的工单",
            priority=Priority.HIGH,
            status=TicketStatus.OPEN,
            sla_deadline=past_deadline,
            response_sla_deadline=past_deadline - timedelta(hours=5),
            created_at=now - timedelta(hours=20),
            updated_at=now
        )
        test_db.add(ticket)
        await test_db.commit()
        await test_db.refresh(ticket)
        
        response = await client.get("/tickets/overdue/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["ticket_id"] == ticket.id
        assert data["items"][0]["is_overdue"] == True

    @pytest.mark.asyncio
    async def test_resolved_tickets_not_in_overdue(self, client, test_db):
        from app.models import Ticket, Priority, TicketStatus
        from app.services import calculate_sla_deadline
        
        now = datetime.utcnow()
        past_deadline = now - timedelta(hours=10)
        
        ticket = Ticket(
            title="已解决工单",
            description="这是一个已解决的工单",
            priority=Priority.HIGH,
            status=TicketStatus.RESOLVED,
            sla_deadline=past_deadline,
            response_sla_deadline=past_deadline - timedelta(hours=5),
            created_at=now - timedelta(hours=20),
            updated_at=now
        )
        test_db.add(ticket)
        await test_db.commit()
        await test_db.refresh(ticket)
        
        response = await client.get("/tickets/overdue/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_closed_tickets_not_in_overdue(self, client, test_db):
        from app.models import Ticket, Priority, TicketStatus
        from app.services import calculate_sla_deadline
        
        now = datetime.utcnow()
        past_deadline = now - timedelta(hours=10)
        
        ticket = Ticket(
            title="已关闭工单",
            description="这是一个已关闭的工单",
            priority=Priority.HIGH,
            status=TicketStatus.CLOSED,
            sla_deadline=past_deadline,
            response_sla_deadline=past_deadline - timedelta(hours=5),
            created_at=now - timedelta(hours=20),
            updated_at=now
        )
        test_db.add(ticket)
        await test_db.commit()
        await test_db.refresh(ticket)
        
        response = await client.get("/tickets/overdue/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 0
