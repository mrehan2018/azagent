from fastapi import APIRouter, HTTPException
from cosmos_client import get_container

router = APIRouter()

@router.get("/parents/{parent_id}")
async def get_parent(parent_id: str):
    try:
        container = get_container("parents")
        
        # Use query instead of read_item to avoid partition key issues
        query = f"SELECT * FROM c WHERE c.id = '{parent_id}' OR c.userId = '{parent_id}'"
        items = list(container.query_items(query, enable_cross_partition_query=True))
        
        if items:
            return items[0]  # Return the first match
        else:
            raise HTTPException(status_code=404, detail=f"Parent {parent_id} not found")
            
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")