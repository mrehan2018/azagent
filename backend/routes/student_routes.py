from fastapi import APIRouter, HTTPException
from cosmos_client import get_container

router = APIRouter()

@router.get("/students/{student_id}")
async def get_student(student_id: str):
    container = get_container("students")
    try:
        item = container.read_item(item=student_id, partition_key=student_id)
        return item
    except Exception:
        raise HTTPException(status_code=404, detail="Student not found")