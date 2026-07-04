"""End-to-end flow for the document slices.

Drives the real HTTP endpoints and the background processing task through the
DI container, with in-memory fakes standing in for MinIO and arq/Redis and an
in-memory SQLite database. This exercises the upload -> queue -> process ->
status path, including the after-commit enqueue timing.
"""

from collections.abc import AsyncIterator
from uuid import UUID

import pytest
from dishka import Provider, Scope, make_async_container, provide
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from app.domain.entities.document import DocumentStatus
from app.domain.interfaces.job_queue import IJobQueue
from app.domain.interfaces.object_storage import IObjectStorage
from app.features.document.get.provider import GetDocumentProvider
from app.features.document.process.handler import ProcessDocumentHandler
from app.features.document.process.provider import ProcessDocumentProvider
from app.features.document.process.schemas import ProcessDocumentCommand
from app.features.document.upload.provider import UploadDocumentProvider
from app.features.registry.routers import ROUTERS
from app.infrastructure.database.after_commit import AfterCommitQueue
from app.infrastructure.database.bootstrap import create_all
from app.infrastructure.database.mapping import run_mappers
from app.infrastructure.errors.handlers import register_exception_handlers


class FakeObjectStorage(IObjectStorage):
    """Records stored objects in memory."""

    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        self.objects[key] = (data, content_type)

    async def get(self, key: str) -> bytes:
        return self.objects[key][0]

    async def delete(self, key: str) -> None:
        self.objects.pop(key, None)


class FakeJobQueue(IJobQueue):
    """Records enqueued document ids in memory."""

    def __init__(self) -> None:
        self.enqueued: list[UUID] = []

    async def enqueue_document_processing(self, document_id: UUID) -> None:
        self.enqueued.append(document_id)


class FakeInfraProvider(Provider):
    """Wires the in-memory engine and fake external adapters for tests."""

    def __init__(self, engine: AsyncEngine, storage: IObjectStorage, queue: IJobQueue) -> None:
        super().__init__()
        self._engine = engine
        self._storage = storage
        self._queue = queue

    after_commit = provide(AfterCommitQueue, scope=Scope.REQUEST)

    @provide(scope=Scope.APP)
    def sessionmaker(self) -> async_sessionmaker[AsyncSession]:
        return async_sessionmaker(self._engine, expire_on_commit=False)

    @provide(scope=Scope.REQUEST)
    async def session(
        self,
        sessionmaker: async_sessionmaker[AsyncSession],
        after_commit: AfterCommitQueue,
    ) -> AsyncIterator[AsyncSession]:
        async with sessionmaker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
        await after_commit.run()

    @provide(scope=Scope.REQUEST)
    def object_storage(self) -> IObjectStorage:
        return self._storage

    @provide(scope=Scope.REQUEST)
    def job_queue(self) -> IJobQueue:
        return self._queue


@pytest.fixture
async def context() -> AsyncIterator[tuple[AsyncClient, FakeObjectStorage, FakeJobQueue, object]]:
    run_mappers()
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    await create_all(engine)

    storage = FakeObjectStorage()
    queue = FakeJobQueue()
    container = make_async_container(
        FakeInfraProvider(engine, storage, queue),
        UploadDocumentProvider(),
        GetDocumentProvider(),
        ProcessDocumentProvider(),
    )

    app = FastAPI()
    for router in ROUTERS:
        app.include_router(router)
    register_exception_handlers(app)
    setup_dishka(container=container, app=app)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, storage, queue, container

    await container.close()
    await engine.dispose()


async def test_upload_stores_file_registers_document_and_enqueues(context) -> None:
    client, storage, queue, _ = context

    response = await client.post(
        "/documents",
        files={"file": ("report.pdf", b"%PDF-1.4 fake bytes", "application/pdf")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["filename"] == "report.pdf"
    assert body["content_type"] == "application/pdf"
    assert body["size"] == len(b"%PDF-1.4 fake bytes")
    assert body["status"] == DocumentStatus.PENDING.value

    # The file reached storage and the job was enqueued after commit.
    assert len(storage.objects) == 1
    assert queue.enqueued == [UUID(body["id"])]


async def test_get_returns_status_and_404_for_unknown(context) -> None:
    client, _, _, _ = context

    created = await client.post(
        "/documents",
        files={"file": ("a.txt", b"hello", "text/plain")},
    )
    document_id = created.json()["id"]

    ok = await client.get(f"/documents/{document_id}")
    assert ok.status_code == 200
    assert ok.json()["status"] == DocumentStatus.PENDING.value

    missing = await client.get("/documents/019f0000-0000-7000-8000-000000000000")
    assert missing.status_code == 404


async def test_process_task_moves_document_to_processed(context, monkeypatch) -> None:
    client, _, queue, container = context

    # This test is about the pending -> processing -> processed state machine,
    # not real NLP extraction (b"hello" isn't a parseable PDF/DOCX anyway) --
    # same fake-the-external-dependency approach as FakeObjectStorage/FakeJobQueue.
    from app.features.document.process import handler as handler_module

    async def fake_run_ingestion_pipeline(file_bytes: bytes, filename: str, content_type: str) -> dict:
        return {"n_nodes": 0, "n_edges": 0}

    monkeypatch.setattr(handler_module, "run_ingestion_pipeline", fake_run_ingestion_pipeline)

    created = await client.post(
        "/documents",
        files={"file": ("a.txt", b"hello", "text/plain")},
    )
    document_id = UUID(created.json()["id"])
    assert queue.enqueued == [document_id]

    # Simulate the worker picking up the enqueued job.
    async with container() as request_container:
        handler = await request_container.get(ProcessDocumentHandler)
        await handler(ProcessDocumentCommand(document_id=document_id))

    status_response = await client.get(f"/documents/{document_id}")
    assert status_response.json()["status"] == DocumentStatus.PROCESSED.value
