from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
import requests
import time

from prompt_router import get_prompt
from routes.student_routes import router as student_router
from routes.teacher_routes import router as teacher_router
from routes.parent_routes import router as parent_router

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

# Include the student, teacher, and parent routes
app.include_router(student_router, prefix="/api/v1", tags=["students"])
app.include_router(teacher_router, prefix="/api/v1", tags=["teachers"])
app.include_router(parent_router, prefix="/api/v1", tags=["parents"])

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
        return {"reply": response.choices[0].message.content}
    except Exception as e:
        return {"error": f"Azure OpenAI error: {str(e)}"}

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
        
        # Test students container
        students_container = get_container("students")
        students = list(students_container.query_items("SELECT TOP 3 * FROM c", enable_cross_partition_query=True))
        
        # Test parents container
        parents_container = get_container("parents")
        parents = list(parents_container.query_items("SELECT TOP 3 * FROM c", enable_cross_partition_query=True))
        
        return {
            "cosmos_configured": True,
            "students_count": len(students),
            "students_sample": students,
            "parents_count": len(parents), 
            "parents_sample": parents,
            "cosmos_endpoint": os.getenv("COSMOS_ENDPOINT"),
            "cosmos_db_name": os.getenv("COSMOS_DB_NAME")
        }
    except Exception as e:
        return {
            "cosmos_configured": False,
            "error": str(e),
            "cosmos_endpoint": bool(os.getenv("COSMOS_ENDPOINT")),
            "cosmos_key_set": bool(os.getenv("COSMOS_KEY")),
            "cosmos_db_name": os.getenv("COSMOS_DB_NAME")
        }

@app.get("/debug/student/{student_id}")
async def debug_student(student_id: str):
    try:
        from cosmos_client import get_container
        container = get_container("students")
        
        results = {}
        
        # Method 1: Try different partition key approaches
        try:
            item1 = container.read_item(item=student_id, partition_key=student_id)
            results["read_with_id"] = item1
        except Exception as e:
            results["read_with_id_error"] = str(e)
        
        # Method 2: Query approach
        try:
            query = f"SELECT * FROM c WHERE c.id = '{student_id}'"
            items = list(container.query_items(query, enable_cross_partition_query=True))
            results["query_by_id"] = items
        except Exception as e:
            results["query_by_id_error"] = str(e)
            
        # Method 3: Query by userId
        try:
            query = f"SELECT * FROM c WHERE c.userId = '{student_id}'"
            items = list(container.query_items(query, enable_cross_partition_query=True))
            results["query_by_userId"] = items
        except Exception as e:
            results["query_by_userId_error"] = str(e)
        
        return results
        
    except Exception as e:
        return {"error": f"General error: {str(e)}"}
