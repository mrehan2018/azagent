from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
import requests
import time
import logging
import json

from prompt_router import get_prompt
from routes.student_routes import router as student_router
from routes.teacher_routes import router as teacher_router
from routes.parent_routes import router as parent_router
from cosmos_client import save_chat_to_cosmos, get_chat_history_from_user, create_chat_container_if_not_exists

# Initialize Azure OpenAI client with error handling
try:
    from openai import AzureOpenAI
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    
    if azure_endpoint and api_key:
        client = AzureOpenAI(
            api_key=api_key,
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
            azure_endpoint=azure_endpoint
        )
        print("Azure OpenAI client initialized successfully")
    else:
        client = None
        print("WARNING: Azure OpenAI credentials not configured")
except Exception as e:
    client = None
    print(f"Error initializing Azure OpenAI client: {e}")

doc_intel_endpoint = os.getenv("DOC_INTELLIGENCE_ENDPOINT")
doc_intel_key = os.getenv("DOC_INTELLIGENCE_KEY")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all API routes
app.include_router(student_router, prefix="/api/v1")
app.include_router(teacher_router, prefix="/api/v1")
app.include_router(parent_router, prefix="/api/v1")

class ChatRequest(BaseModel):
    user_role: str
    topic: str
    context: str

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "azure_openai_configured": client is not None,
        "frontend_available": os.path.exists("frontend"),
        "doc_intelligence_configured": bool(doc_intel_endpoint and doc_intel_key)
    }

@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    logging.info(f"=== CHAT ENDPOINT CALLED ===")
    logging.info(f"user_role: {req.user_role}")
    logging.info(f"topic: {req.topic}")
    logging.info(f"context: {req.context}")
    
    if not client:
        return {"error": "Azure OpenAI client not configured - check environment variables"}
    
    try:
        prompt = get_prompt(req.user_role, req.topic, req.context)
        response = client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-35-turbo"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=500
        )
        
        ai_reply = response.choices[0].message.content
        logging.info(f"AI Reply generated: {ai_reply[:100]}...")
        
        # Extract user_id from context
        try:
            context_data = json.loads(req.context)
            user_id = context_data.get("userId") or context_data.get("id", "unknown")
        except (json.JSONDecodeError, TypeError):
            user_id = req.context if req.context else "unknown"
        
        logging.info(f"Final user_id for saving: {user_id}")
        
        # Save chat using the simple function
        try:
            chat_saved = save_chat_to_cosmos(
                user_id=user_id,
                user_role=req.user_role,
                question=req.topic,
                answer=ai_reply
            )
            logging.info(f"Chat save result: {chat_saved}")
            
        except Exception as save_error:
            logging.error(f"FAILED TO SAVE CHAT: {save_error}")
            chat_saved = False
        
        return {
            "reply": ai_reply, 
            "user_id": user_id, 
            "chat_saved": chat_saved
        }
        
    except Exception as e:
        logging.error(f"Chat endpoint error: {str(e)}")
        return {"error": f"Chat error: {str(e)}"}

@app.post("/upload-test")
async def upload_test(file: UploadFile = File(...), role: str = Form(...), topic: str = Form(...)):
    if not client:
        return {"error": "Azure OpenAI client not configured"}
    
    if not (doc_intel_endpoint and doc_intel_key):
        return {"error": "Document Intelligence not configured"}
    
    try:
        # Send to Azure Document Intelligence
        ocr_url = f"{doc_intel_endpoint}/formrecognizer/documentModels/prebuilt-layout:analyze?api-version=2023-07-31"
        headers = {
            "Content-Type": "application/pdf",
            "Ocp-Apim-Subscription-Key": doc_intel_key
        }
        content = await file.read()
        response = requests.post(ocr_url, headers=headers, data=content)
        result_url = response.headers.get("operation-location")

        # Wait and fetch result
        for _ in range(10):
            time.sleep(2)
            poll = requests.get(result_url, headers={"Ocp-Apim-Subscription-Key": doc_intel_key}).json()
            if poll.get("status") == "succeeded":
                full_text = " ".join([line['content'] for page in poll['analyzeResult']['pages'] for line in page['lines']])
                break
        else:
            return {"error": "OCR timed out"}

        # Route to Azure OpenAI
        prompt = get_prompt(role, topic, full_text[:5000])
        response = client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-35-turbo"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=500
        )
        return {"reply": response.choices[0].message.content, "extracted_text": full_text[:500]}
    except Exception as e:
        return {"error": f"Processing error: {str(e)}"}

# Mount static files for frontend
if os.path.exists("frontend"):
    app.mount("/static", StaticFiles(directory="frontend"), name="static")
    print("Frontend static files mounted at /static")
else:
    print("Frontend directory not found")

# Serve index.html at root
@app.get("/")
async def root():
    if os.path.exists("frontend/index.html"):
        return FileResponse("frontend/index.html")
    else:
        return {
            "message": "GAIEF Demo API is running!", 
            "status": "healthy",
            "azure_openai_configured": client is not None,
            "frontend_available": os.path.exists("frontend")
        }

# Debug endpoints
@app.get("/debug/cosmos")
async def debug_cosmos():
    try:
        from cosmos_client import get_container
        
        # Test all containers
        results = {}
        
        for container_name in ["students", "teachers", "parents"]:
            try:
                container = get_container(container_name)
                query = "SELECT TOP 3 * FROM c"
                items = list(container.query_items(query, enable_cross_partition_query=True))
                results[container_name] = {
                    "count": len(items),
                    "sample_data": items
                }
            except Exception as e:
                results[container_name] = {"error": str(e)}
        
        return {
            "cosmos_status": "connected",
            "containers": results
        }
        
    except Exception as e:
        return {"error": f"Cosmos debug failed: {str(e)}"}

@app.get("/debug/student/{student_id}")
async def debug_student(student_id: str):
    try:
        from cosmos_client import get_container
        container = get_container("students")
        
        # Try multiple query approaches
        results = {}
        
        # Query 1: By userId
        query1 = f"SELECT * FROM c WHERE c.userId = '{student_id}'"
        items1 = list(container.query_items(query1, enable_cross_partition_query=True))
        results["query_by_userId"] = items1
        
        # Query 2: By id
        query2 = f"SELECT * FROM c WHERE c.id = '{student_id}'"
        items2 = list(container.query_items(query2, enable_cross_partition_query=True))
        results["query_by_id"] = items2
        
        # Query 3: Get all students (first 5)
        query3 = "SELECT TOP 5 * FROM c"
        items3 = list(container.query_items(query3, enable_cross_partition_query=True))
        results["all_students_sample"] = items3
        
        # Query 4: Search partial match
        query4 = f"SELECT * FROM c WHERE CONTAINS(c.id, '{student_id}') OR CONTAINS(c.userId, '{student_id}')"
        items4 = list(container.query_items(query4, enable_cross_partition_query=True))
        results["partial_match"] = items4
        
        return {
            "student_id_searched": student_id,
            "results": results,
            "total_queries": 4
        }
        
    except Exception as e:
        return {"error": f"Debug failed: {str(e)}"}

@app.get("/debug/test")
async def debug_test():
    return {
        "message": "Debug endpoint working",
        "timestamp": "2025-01-01",
        "environment": {
            "cosmos_endpoint": bool(os.getenv("COSMOS_ENDPOINT")),
            "cosmos_key": bool(os.getenv("COSMOS_KEY")),
            "cosmos_db": os.getenv("COSMOS_DB_NAME")
        }
    }

@app.post("/debug/test-chat-save")
async def debug_test_chat_save():
    """Test the simple chat saving functionality"""
    try:
        from cosmos_client import save_chat_to_cosmos
        
        # Test saving for student
        result = save_chat_to_cosmos(
            user_id="stu_12345",
            user_role="student", 
            question="Test question - what is my math progress?",
            answer="Test answer - Your math progress is 88%"
        )
        
        return {
            "status": "success" if result else "failed",
            "chat_saved": result,
            "message": "Check /debug/student/stu_12345 to verify"
        }
        
    except Exception as e:
        return {
            "status": "failed",
            "error": str(e)
        }

@app.get("/debug/chat-history/{user_id}")
async def debug_chat_history(user_id: str, user_role: str = "student"):
    """Get chat history using the simple approach"""
    try:
        from cosmos_client import get_chat_history_from_user
        
        chat_history = get_chat_history_from_user(user_id, user_role)
        
        return {
            "user_id": user_id,
            "user_role": user_role,
            "chat_history_count": len(chat_history),
            "chat_history": chat_history
        }
        
    except Exception as e:
        return {"error": f"Failed to get chat history: {str(e)}"}

@app.get("/test-chat-simple")
async def test_chat_simple():
    """Simple test to manually trigger a chat save"""
    try:
        # Simulate a chat request
        test_request = ChatRequest(
            user_role="student",
            topic="What is my math grade?",
            context='{"userId":"stu_12345","name":"Aisha Khan"}'
        )
        
        # Call your existing chat endpoint
        result = await chat_endpoint(test_request)
        
        return {
            "test_status": "completed",
            "chat_result": result,
            "message": "Check /debug/student/stu_12345 to see if chatHistory was updated"
        }
        
    except Exception as e:
        return {
            "test_status": "failed",
            "error": str(e)
        }

@app.get("/api/v1/parent-access/{parent_id}/student/{student_id}")
async def parent_access_student(parent_id: str, student_id: str):
    """Allow parents to access their child's data"""
    try:
        from cosmos_client import get_container, get_chat_history_from_user
        
        # Get parent data to verify relationship
        parent_container = get_container("parents")
        parent_doc = parent_container.read_item(item=parent_id, partition_key=parent_id)
        
        # Check if this parent has access to this student
        allowed_students = parent_doc.get("children", [])
        if student_id not in allowed_students:
            return {"error": "Access denied: You are not authorized to view this student's data"}
        
        # Get student data
        student_container = get_container("students")
        student_doc = student_container.read_item(item=student_id, partition_key=student_id)
        
        # Get chat history
        chat_history = get_chat_history_from_user(student_id, "student")
        
        return {
            "student_info": {
                "name": student_doc.get("name"),
                "grade": student_doc.get("grade"),
                "subjects": student_doc.get("subjects"),
                "progress": student_doc.get("progress")
            },
            "chat_summary": {
                "total_conversations": len(chat_history),
                "recent_activity": chat_history[:5] if chat_history else []
            },
            "parent_access": True
        }
        
    except Exception as e:
        return {"error": f"Failed to retrieve student data: {str(e)}"}
