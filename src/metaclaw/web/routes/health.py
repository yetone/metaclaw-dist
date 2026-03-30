"""Health check endpoint."""

from fastapi import APIRouter

from metaclaw import __version__

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict:
    return {
        "status": "ok",
        "version": __version__,
        "service": "metaclaw",
    }


@router.get("/")
async def root() -> dict:
    return {
        "name": "MetaClaw",
        "version": __version__,
        "docs": "/docs",
    }
