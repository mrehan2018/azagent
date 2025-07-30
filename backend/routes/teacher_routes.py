from fastapi import APIRouter, HTTPException
from cosmos_client import get_container

router = APIRouter()

@router.get("/teachers/{teacher_id}")
async def get_teacher(teacher_id: str):
    container = get_container("teachers")
    try:
        item = container.read_item(item=teacher_id, partition_key=teacher_id)
        return item
    except Exception:
        raise HTTPException(status_code=404, detail="Teacher not found")