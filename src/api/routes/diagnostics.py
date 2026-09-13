from fastapi import APIRouter

router = APIRouter()

@router.get("/diagnostics")
async def get_diagnostics():
    return {"status": "ok", "message": "Diagnostics model metadata loaded"}