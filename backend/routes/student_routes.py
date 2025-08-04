from fastapi import APIRouter, HTTPException
from cosmos_client import get_container

router = APIRouter()

@router.get("/students/{student_id}")
async def get_student(student_id: str):
    try:
        container = get_container("students")
        
        # Try read_item first (faster if partition key matches)
        try:
            # First attempt: partition key = /id
            item = container.read_item(item=student_id, partition_key=student_id)
            return item
        except Exception:
            try:
                # Second attempt: partition key = /userId (common scenario)
                item = container.read_item(item=student_id, partition_key=student_id)
                return item
            except Exception:
                # Fallback: use query approach (works across all partition keys)
                query = f"SELECT * FROM c WHERE c.id = '{student_id}' OR c.userId = '{student_id}'"
                items = list(container.query_items(query, enable_cross_partition_query=True))
                
                if items:
                    return items[0]
                else:
                    raise HTTPException(status_code=404, detail=f"Student {student_id} not found")
                    
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")