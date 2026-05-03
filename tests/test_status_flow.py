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


class TestStatusTransitionRejection:
    @pytest.mark.asyncio
    async def test_open_to_on_hold_rejected(self, client, create_test_ticket):
        ticket = await create_test_ticket()
        
        response = await client.post(
            f"/tickets/{ticket['id']}/status/on_hold"
        )
        
        assert response.status_code == 400
        data = response.json()
        
        assert data["error_type"] == "status_transition_error"
        assert data["from_status"] == "open"
        assert data["to_status"] == "on_hold"
        assert "有效目标状态" in data["detail"]
        
        response = await client.get(f"/tickets/{ticket['id']}")
        data = response.json()
        assert data["status"] == "open"
        assert len(data["status_changes"]) == 1

    @pytest.mark.asyncio
    async def test_in_progress_to_closed_rejected(self, client, create_test_ticket):
        ticket = await create_test_ticket()
        
        response = await client.post(
            f"/tickets/{ticket['id']}/status/in_progress"
        )
        assert response.status_code == 200
        
        response = await client.post(
            f"/tickets/{ticket['id']}/status/closed"
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error_type"] == "status_transition_error"
        assert data["from_status"] == "in_progress"
        assert data["to_status"] == "closed"
        
        response = await client.get(f"/tickets/{ticket['id']}")
        data = response.json()
        assert data["status"] == "in_progress"
        assert len(data["status_changes"]) == 2

    @pytest.mark.asyncio
    async def test_on_hold_to_open_rejected(self, client, create_test_ticket):
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
            f"/tickets/{ticket['id']}/status/open"
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error_type"] == "status_transition_error"
        assert data["from_status"] == "on_hold"
        assert data["to_status"] == "open"
        
        response = await client.get(f"/tickets/{ticket['id']}")
        data = response.json()
        assert data["status"] == "on_hold"
        assert len(data["status_changes"]) == 3

    @pytest.mark.asyncio
    async def test_on_hold_to_resolved_rejected(self, client, create_test_ticket):
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
            f"/tickets/{ticket['id']}/status/resolved"
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error_type"] == "status_transition_error"
        assert data["from_status"] == "on_hold"
        assert data["to_status"] == "resolved"
        
        response = await client.get(f"/tickets/{ticket['id']}")
        data = response.json()
        assert data["status"] == "on_hold"
        assert len(data["status_changes"]) == 3

    @pytest.mark.asyncio
    async def test_resolved_to_on_hold_rejected(self, client, create_test_ticket):
        ticket = await create_test_ticket()
        
        response = await client.post(
            f"/tickets/{ticket['id']}/status/resolved"
        )
        assert response.status_code == 200
        
        response = await client.post(
            f"/tickets/{ticket['id']}/status/on_hold"
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error_type"] == "status_transition_error"
        assert data["from_status"] == "resolved"
        assert data["to_status"] == "on_hold"
        
        response = await client.get(f"/tickets/{ticket['id']}")
        data = response.json()
        assert data["status"] == "resolved"
        assert len(data["status_changes"]) == 2

    @pytest.mark.asyncio
    async def test_closed_to_resolved_rejected(self, client, create_test_ticket):
        ticket = await create_test_ticket()
        
        response = await client.post(
            f"/tickets/{ticket['id']}/status/closed"
        )
        assert response.status_code == 200
        
        response = await client.post(
            f"/tickets/{ticket['id']}/status/resolved"
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error_type"] == "status_transition_error"
        assert data["from_status"] == "closed"
        assert data["to_status"] == "resolved"
        
        response = await client.get(f"/tickets/{ticket['id']}")
        data = response.json()
        assert data["status"] == "closed"
        assert len(data["status_changes"]) == 2

    @pytest.mark.asyncio
    async def test_closed_to_open_rejected(self, client, create_test_ticket):
        ticket = await create_test_ticket()
        
        response = await client.post(
            f"/tickets/{ticket['id']}/status/closed"
        )
        assert response.status_code == 200
        
        response = await client.post(
            f"/tickets/{ticket['id']}/status/open"
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error_type"] == "status_transition_error"
        assert data["from_status"] == "closed"
        assert data["to_status"] == "open"
        
        response = await client.get(f"/tickets/{ticket['id']}")
        data = response.json()
        assert data["status"] == "closed"
        assert len(data["status_changes"]) == 2

    @pytest.mark.asyncio
    async def test_update_ticket_with_invalid_status_rejected(self, client, create_test_ticket):
        ticket = await create_test_ticket()
        
        response = await client.put(
            f"/tickets/{ticket['id']}",
            json={
                "title": "新标题",
                "status": "on_hold"
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error_type"] == "status_transition_error"
        
        response = await client.get(f"/tickets/{ticket['id']}")
        data = response.json()
        assert data["status"] == "open"
        assert data["title"] == "测试工单"
        assert len(data["status_changes"]) == 1

    @pytest.mark.asyncio
    async def test_distinguish_nonexistent_ticket_from_invalid_transition(self, client):
        ticket_id = 999999
        
        response = await client.post(
            f"/tickets/{ticket_id}/status/in_progress"
        )
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "工单不存在"
        assert "error_type" not in data

    @pytest.mark.asyncio
    async def test_same_status_transition_allowed(self, client, create_test_ticket):
        ticket = await create_test_ticket()
        
        response = await client.post(
            f"/tickets/{ticket['id']}/status/open"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "open"
        
        response = await client.get(f"/tickets/{ticket['id']}")
        data = response.json()
        assert len(data["status_changes"]) == 1

    @pytest.mark.asyncio
    async def test_valid_transition_after_rejected_attempt(self, client, create_test_ticket):
        ticket = await create_test_ticket()
        
        response = await client.post(
            f"/tickets/{ticket['id']}/status/on_hold"
        )
        assert response.status_code == 400
        
        response = await client.post(
            f"/tickets/{ticket['id']}/status/in_progress"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "in_progress"
        
        response = await client.get(f"/tickets/{ticket['id']}")
        data = response.json()
        assert data["status"] == "in_progress"
        assert len(data["status_changes"]) == 2
        assert data["status_changes"][1]["from_status"] == "open"
        assert data["status_changes"][1]["to_status"] == "in_progress"
