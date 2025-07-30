from fastapi import APIRouter, HTTPException
from cosmos_client import get_container

router = APIRouter()

@router.get("/students/{student_id}")
async def get_student(student_id: str):
    try:
        container = get_container("students")
        
        # Using student_id for both item and partition_key (since userId = id in your data)
        item = container.read_item(item=student_id, partition_key=student_id)
        return item
        
    except Exception as e:
        # Check if it's a "not found" error
        if "NotFound" in str(type(e)) or "404" in str(e):
            raise HTTPException(status_code=404, detail=f"Student {student_id} not found")
        else:
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")