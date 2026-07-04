"""Aggregated HTTP routers — the only place that lists every controller router."""

from fastapi import APIRouter

from app.features.auth.login.controller import router as login_router
from app.features.auth.logout.controller import router as logout_router
from app.features.auth.me.controller import router as me_router
from app.features.auth.refresh.controller import router as refresh_router
from app.features.dashboard.provenance.controller import router as provenance_router
from app.features.dashboard.summary.controller import router as dashboard_summary_router
from app.features.document.delete.controller import router as document_delete_router
from app.features.document.get.controller import router as document_get_router
from app.features.document.list.controller import router as document_list_router
from app.features.document.upload.controller import router as document_upload_router
from app.features.health.check.controller import router as health_check_router
from app.features.users.create.controller import router as create_user_router
from app.features.users.list.controller import router as list_users_router

from app.features.graph.controller import router as graph_router
from app.features.query.ask.controller import router as query_ask_router
from app.features.query.history.controller import router as answers_history_router
from fastapi import APIRouter

ROUTERS: list[APIRouter] = [
    health_check_router,
    login_router,
    refresh_router,
    logout_router,
    me_router,
    create_user_router,
    list_users_router,
    document_upload_router,
    document_list_router,
    document_get_router,
    document_delete_router,
    query_ask_router,
    answers_history_router,
    graph_router,
    dashboard_summary_router,
    provenance_router,
]
