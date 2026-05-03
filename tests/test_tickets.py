import pytest
from datetime import datetime, timedelta

class TestTicketCRUD:
    @pytest.mark.asyncio
    async def test_create_ticket(self, client, sample_ticket_data):
        response = await client.post("/tickets/", json=sample_ticket_data)
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["title"] == sample_ticket_data["title"]
        assert data["description"] == sample_ticket_data["description"]
        assert data["priority"] == sample_ticket_data["priority"]
        assert data["status"] == "open"
        assert data["is_overdue"] == False
        assert data["is_response_overdue"] == False
        assert "sla_deadline" in data
        assert "response_sla_deadline" in data
        assert "created_at" in data
        assert "updated_at" in data
        assert "id" in data

    @pytest.mark.asyncio
    async def test_get_ticket(self, client, create_test_ticket):
        ticket = await create_test_ticket()
        
        response = await client.get(f"/tickets/{ticket['id']}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == ticket["id"]
        assert data["title"] == ticket["title"]

    @pytest.mark.asyncio
    async def test_get_nonexistent_ticket(self, client):
        response = await client.get("/tickets/999999")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_tickets(self, client, create_multiple_tickets):
        await create_multiple_tickets(5)
        
        response = await client.get("/tickets/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 5
        assert len(data["items"]) == 5
        assert data["page"] == 1
        assert data["page_size"] == 10
        assert data["total_pages"] == 1

    @pytest.mark.asyncio
    async def test_list_tickets_with_pagination(self, client, create_multiple_tickets):
        await create_multiple_tickets(15)
        
        response = await client.get("/tickets/?page=2&page_size=5")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 15
        assert len(data["items"]) == 5
        assert data["page"] == 2
        assert data["page_size"] == 5
        assert data["total_pages"] == 3

    @pytest.mark.asyncio
    async def test_list_tickets_filter_by_status(self, client, create_test_ticket):
        ticket = await create_test_ticket()
        
        response = await client.get("/tickets/?status=open")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 1
        assert data["items"][0]["status"] == "open"

    @pytest.mark.asyncio
    async def test_list_tickets_filter_by_priority(self, client, create_multiple_tickets):
        tickets = await create_multiple_tickets(6)
        
        response = await client.get("/tickets/?priority=high")
        
        assert response.status_code == 200
        data = response.json()
        
        for item in data["items"]:
            assert item["priority"] == "high"

    @pytest.mark.asyncio
    async def test_update_ticket_title(self, client, create_test_ticket):
        ticket = await create_test_ticket()
        new_title = "更新后的工单标题"
        
        response = await client.put(
            f"/tickets/{ticket['id']}",
            json={"title": new_title}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == new_title
        assert data["id"] == ticket["id"]

    @pytest.mark.asyncio
    async def test_update_ticket_priority(self, client, create_test_ticket):
        ticket = await create_test_ticket()
        
        response = await client.put(
            f"/tickets/{ticket['id']}",
            json={"priority": "critical"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["priority"] == "critical"
        assert data["updated_at"] != ticket["updated_at"]

    @pytest.mark.asyncio
    async def test_update_nonexistent_ticket(self, client):
        response = await client.put(
            "/tickets/999999",
            json={"title": "测试"}
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_ticket(self, client, create_test_ticket):
        ticket = await create_test_ticket()
        
        response = await client.delete(f"/tickets/{ticket['id']}")
        assert response.status_code == 204
        
        response = await client.get(f"/tickets/{ticket['id']}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_nonexistent_ticket(self, client):
        response = await client.delete("/tickets/999999")
        assert response.status_code == 404

class TestTicketSLA:
    @pytest.mark.asyncio
    async def test_ticket_has_sla_deadline(self, client, sample_ticket_data):
        response = await client.post("/tickets/", json=sample_ticket_data)
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["sla_deadline"] is not None
        assert data["response_sla_deadline"] is not None

    @pytest.mark.asyncio
    async def test_sla_deadline_based_on_priority(self, client):
        critical_ticket = await client.post("/tickets/", json={
            "title": "紧急工单",
            "priority": "critical"
        })
        assert critical_ticket.status_code == 201
        critical_data = critical_ticket.json()
        
        low_ticket = await client.post("/tickets/", json={
            "title": "低优先级工单",
            "priority": "low"
        })
        assert low_ticket.status_code == 201
        low_data = low_ticket.json()
        
        critical_created = datetime.fromisoformat(critical_data["created_at"].replace("Z", "+00:00"))
        critical_deadline = datetime.fromisoformat(critical_data["sla_deadline"].replace("Z", "+00:00"))
        critical_hours = (critical_deadline - critical_created).total_seconds() / 3600
        
        low_created = datetime.fromisoformat(low_data["created_at"].replace("Z", "+00:00"))
        low_deadline = datetime.fromisoformat(low_data["sla_deadline"].replace("Z", "+00:00"))
        low_hours = (low_deadline - low_created).total_seconds() / 3600
        
        assert critical_hours < low_hours

    @pytest.mark.asyncio
    async def test_initial_ticket_not_overdue(self, client, sample_ticket_data):
        response = await client.post("/tickets/", json=sample_ticket_data)
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["is_overdue"] == False
        assert data["is_response_overdue"] == False
