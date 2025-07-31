from fastapi import APIRouter, HTTPException
from cosmos_client import get_container

router = APIRouter()

@router.get("/teachers/{teacher_id}")
async def get_teacher(teacher_id: str):
    try:
        container = get_container("teachers")
        
        # Use query instead of read_item to avoid partition key issues
        query = f"SELECT * FROM c WHERE c.id = '{teacher_id}' OR c.userId = '{teacher_id}'"
        items = list(container.query_items(query, enable_cross_partition_query=True))
        
        if items:
            return items[0]  # Return the first match
        else:
            raise HTTPException(status_code=404, detail=f"Teacher {teacher_id} not found")
            
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")