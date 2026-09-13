from fastapi import APIRouter
from .health import router as health_router
from .diagnostics import router as diagnostics_router
from .optimize import router as optimize_router

router = APIRouter()
router.include_router(health_router)
router.include_router(diagnostics_router)
router.include_router(optimize_router)