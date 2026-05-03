import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import tempfile
import os

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import Base, get_db
from app.main import app
from app.models import TicketStatus, Priority

_test_db_path = None
_test_engine = None
_test_session_local = None

async def override_get_db():
    global _test_session_local
    if _test_session_local is None:
        raise RuntimeError("Test database not initialized")
    
    async with _test_session_local() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

app.dependency_overrides[get_db] = override_get_db

@pytest_asyncio.fixture(scope="function")
async def test_db():
    global _test_db_path, _test_engine, _test_session_local
    
    with tempfile.TemporaryDirectory() as tmpdir:
        _test_db_path = os.path.join(tmpdir, "test_ticket_sla.db")
        TEST_DATABASE_URL = f"sqlite+aiosqlite:///{_test_db_path}"
        
        _test_engine = create_async_engine(
            TEST_DATABASE_URL,
            connect_args={"check_same_thread": False},
        )
        
        _test_session_local = async_sessionmaker(
            _test_engine, class_=AsyncSession, expire_on_commit=False
        )
        
        async with _test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        async with _test_session_local() as session:
            from app.models import SLAConfig
            from app.services import DEFAULT_SLA_CONFIGS
            
            for priority, config in DEFAULT_SLA_CONFIGS.items():
                new_config = SLAConfig(
                    priority=priority,
                    resolution_hours=config["resolution_hours"],
                    response_hours=config["response_hours"]
                )
                session.add(new_config)
            
            await session.commit()
            
            yield session
        
        async with _test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        
        _test_db_path = None
        _test_engine = None
        _test_session_local = None

@pytest_asyncio.fixture(scope="function")
async def client(test_db):
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver"
    ) as test_client:
        yield test_client

@pytest_asyncio.fixture
def sample_ticket_data():
    return {
        "title": "测试工单",
        "description": "这是一个测试工单的描述",
        "priority": "high"
    }

@pytest_asyncio.fixture
async def create_test_ticket(client, sample_ticket_data):
    async def _create_ticket(data=None):
        if data is None:
            data = sample_ticket_data
        response = await client.post("/tickets/", json=data)
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        return response.json()
    return _create_ticket

@pytest_asyncio.fixture
async def create_multiple_tickets(client):
    async def _create_tickets(count=5):
        tickets = []
        for i in range(count):
            data = {
                "title": f"测试工单 {i+1}",
                "description": f"这是第 {i+1} 个测试工单",
                "priority": "medium" if i % 2 == 0 else "high"
            }
            response = await client.post("/tickets/", json=data)
            assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
            tickets.append(response.json())
        return tickets
    return _create_tickets

@pytest_asyncio.fixture
def mock_datetime():
    def _mock_datetime(mock_time):
        mock_datetime = MagicMock()
        mock_datetime.utcnow.return_value = mock_time
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
        
        patcher = patch('app.services.datetime', mock_datetime)
        patcher2 = patch('app.main.datetime', mock_datetime)
        patcher.start()
        patcher2.start()
        
        def stop():
            patcher.stop()
            patcher2.stop()
        
        return stop
    
    return _mock_datetime
