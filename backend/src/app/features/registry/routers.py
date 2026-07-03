"""Aggregated HTTP routers — the only place that lists every controller router."""

from fastapi import APIRouter

from app.features.health.check.controller import router as health_check_router

ROUTERS: list[APIRouter] = [
    health_check_router,
]
