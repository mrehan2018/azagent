from fastapi import APIRouter, HTTPException
from cosmos_client import get_container

router = APIRouter()

@router.get("/teachers/{teacher_id}")
async def get_teacher(teacher_id: str):
    try:
        container = get_container("teachers")
        
        # Using teacher_id for both item and partition_key (assuming teachers also use userId as partition key)
        item = container.read_item(item=teacher_id, partition_key=teacher_id)
        return item
        
    except Exception as e:
        # Check if it's a "not found" error
        if "NotFound" in str(type(e)) or "404" in str(e):
            raise HTTPException(status_code=404, detail=f"Teacher {teacher_id} not found")
        else:
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")