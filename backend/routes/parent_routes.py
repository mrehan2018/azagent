from fastapi import APIRouter, HTTPException
from cosmos_client import get_container

router = APIRouter()

@router.get("/parents/{parent_id}")
async def get_parent(parent_id: str):
    try:
        container = get_container("parents")
        
        # Using parent_id for both item and partition_key (assuming parents also use userId as partition key)
        item = container.read_item(item=parent_id, partition_key=parent_id)
        return item
        
    except Exception as e:
        # Check if it's a "not found" error
        if "NotFound" in str(type(e)) or "404" in str(e):
            raise HTTPException(status_code=404, detail=f"Parent {parent_id} not found")
        else:
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")