from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from openai import OpenAI
import os
import requests
import time

from prompt_router import get_prompt

# Initialize OpenAI client (new API)
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("WARNING: OPENAI_API_KEY not set!")

client = OpenAI(api_key=api_key) if api_key else None

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

class ChatRequest(BaseModel):
    user_role: str
    topic: str
    context: str

@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    if not client:
        return {"error": "OpenAI client not initialized - API key missing"}
    
    prompt = get_prompt(req.user_role, req.topic, req.context)
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=500
        )
        return {"reply": response.choices[0].message.content}
    except Exception as e:
        return {"error": str(e)}

@app.post("/upload-test")
async def upload_test(file: UploadFile = File(...), role: str = Form(...), topic: str = Form(...)):
    if not client:
        return {"error": "OpenAI client not initialized - API key missing"}
    
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

    # Route to GPT (updated API)
    prompt = get_prompt(role, topic, full_text[:5000])  # Truncate if needed
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=500
    )
    return {"reply": response.choices[0].message.content, "extracted_text": full_text[:500]}

# Mount the frontend at root - this should be LAST
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
