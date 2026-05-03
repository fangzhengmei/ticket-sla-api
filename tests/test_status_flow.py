import pytest
from datetime import datetime, timedelta

class TestTicketStatusFlow:
    @pytest.mark.asyncio
    async def test_initial_status_is_open(self, client, sample_ticket_data):
        response = await client.post("/tickets/", json=sample_ticket_data)
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["status"] == "open"

    @pytest.mark.asyncio
    async def test_open_to_in_progress(self, client, create_test_ticket):
        ticket = await create_test_ticket()
        
        response = await client.post(
            f"/tickets/{ticket['id']}/status/in_progress"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "in_progress"

    @pytest.mark.asyncio
    async def test_open_to_resolved(self, client, create_test_ticket):
        ticket = await create_test_ticket()
        
        response = await client.post(
            f"/tickets/{ticket['id']}/status/resolved"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "resolved"

    @pytest.mark.asyncio
    async def test_open_to_closed(self, client, create_test_ticket):
        ticket = await create_test_ticket()
        
        response = await client.post(
            f"/tickets/{ticket['id']}/status/closed"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "closed"

    @pytest.mark.asyncio
    async def test_in_progress_to_on_hold(self, client, create_test_ticket):
        ticket = await create_test_ticket()
        
        response = await client.post(
            f"/tickets/{ticket['id']}/status/in_progress"
        )
        assert response.status_code == 200
        
        response = await client.post(
            f"/tickets/{ticket['id']}/status/on_hold"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "on_hold"

    @pytest.mark.asyncio
    async def test_in_progress_to_resolved(self, client, create_test_ticket):
        ticket = await create_test_ticket()
        
        response = await client.post(
            f"/tickets/{ticket['id']}/status/in_progress"
        )
        assert response.status_code == 200
        
        response = await client.post(
            f"/tickets/{ticket['id']}/status/resolved"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "resolved"

    @pytest.mark.asyncio
    async def test_on_hold_to_in_progress(self, client, create_test_ticket):
        ticket = await create_test_ticket()
        
        response = await client.post(
            f"/tickets/{ticket['id']}/status/in_progress"
        )
        assert response.status_code == 200
        
        response = await client.post(
            f"/tickets/{ticket['id']}/status/on_hold"
        )
        assert response.status_code == 200
        
        response = await client.post(
            f"/tickets/{ticket['id']}/status/in_progress"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "in_progress"

    @pytest.mark.asyncio
    async def test_resolved_to_closed(self, client, create_test_ticket):
        ticket = await create_test_ticket()
        
        response = await client.post(
            f"/tickets/{ticket['id']}/status/resolved"
        )
        assert response.status_code == 200
        
        response = await client.post(
            f"/tickets/{ticket['id']}/status/closed"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "closed"

    @pytest.mark.asyncio
    async def test_resolved_to_in_progress(self, client, create_test_ticket):
        ticket = await create_test_ticket()
        
        response = await client.post(
            f"/tickets/{ticket['id']}/status/resolved"
        )
        assert response.status_code == 200
        
        response = await client.post(
            f"/tickets/{ticket['id']}/status/in_progress"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "in_progress"

    @pytest.mark.asyncio
    async def test_closed_to_in_progress(self, client, create_test_ticket):
        ticket = await create_test_ticket()
        
        response = await client.post(
            f"/tickets/{ticket['id']}/status/closed"
        )
        assert response.status_code == 200
        
        response = await client.post(
            f"/tickets/{ticket['id']}/status/in_progress"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "in_progress"

    @pytest.mark.asyncio
    async def test_status_history_recorded(self, client, create_test_ticket):
        ticket = await create_test_ticket()
        
        response = await client.post(
            f"/tickets/{ticket['id']}/status/in_progress"
        )
        assert response.status_code == 200
        
        response = await client.post(
            f"/tickets/{ticket['id']}/status/resolved"
        )
        assert response.status_code == 200
        
        response = await client.get(f"/tickets/{ticket['id']}")
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["status_changes"]) == 3
        
        initial_change = data["status_changes"][0]
        assert initial_change["from_status"] is None
        assert initial_change["to_status"] == "open"
        
        second_change = data["status_changes"][1]
        assert second_change["from_status"] == "open"
        assert second_change["to_status"] == "in_progress"
        
        third_change = data["status_changes"][2]
        assert third_change["from_status"] == "in_progress"
        assert third_change["to_status"] == "resolved"

    @pytest.mark.asyncio
    async def test_resolved_ticket_not_overdue(self, client, create_test_ticket):
        ticket = await create_test_ticket()
        
        response = await client.post(
            f"/tickets/{ticket['id']}/status/resolved"
        )
        assert response.status_code == 200
        
        response = await client.get(f"/tickets/{ticket['id']}")
        assert response.status_code == 200
        data = response.json()
        
        assert data["is_overdue"] == False
        assert data["is_response_overdue"] == False

    @pytest.mark.asyncio
    async def test_closed_ticket_not_overdue(self, client, create_test_ticket):
        ticket = await create_test_ticket()
        
        response = await client.post(
            f"/tickets/{ticket['id']}/status/closed"
        )
        assert response.status_code == 200
        
        response = await client.get(f"/tickets/{ticket['id']}")
        assert response.status_code == 200
        data = response.json()
        
        assert data["is_overdue"] == False
        assert data["is_response_overdue"] == False
