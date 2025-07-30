from fastapi import APIRouter, HTTPException
from cosmos_client import get_container

router = APIRouter()

@router.get("/parents/{parent_id}")
async def get_parent(parent_id: str):
    container = get_container("parents")
    try:
        item = container.read_item(item=parent_id, partition_key=parent_id)
        return item
    except Exception:
        raise HTTPException(status_code=404, detail="Parent not found")