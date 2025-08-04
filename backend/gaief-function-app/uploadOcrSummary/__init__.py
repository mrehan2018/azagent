import os
import json
import logging
import azure.functions as func
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from openai import AzureOpenAI

# OCR Function using Azure Document Intelligence
def extract_text_from_file(file_data):
    logging.info("Starting OCR text extraction")
    
    endpoint = os.getenv("FORM_RECOGNIZER_ENDPOINT")
    key = os.getenv("FORM_RECOGNIZER_KEY")
    
    logging.info(f"Form Recognizer endpoint configured: {bool(endpoint)}")
    logging.info(f"Form Recognizer key configured: {bool(key)}")

    if not endpoint or not key:
        logging.error("FORM_RECOGNIZER credentials missing")
        raise Exception("FORM_RECOGNIZER credentials missing")

    try:
        client = DocumentAnalysisClient(
            endpoint=endpoint,
            credential=AzureKeyCredential(key)
        )
        logging.info("DocumentAnalysisClient created successfully")

        poller = client.begin_analyze_document("prebuilt-document", document=file_data)
        logging.info("Document analysis started")
        
        result = poller.result()
        logging.info(f"Document analysis completed. Pages found: {len(result.pages)}")

        full_text = ""
        line_count = 0
        for page_idx, page in enumerate(result.pages):
            logging.info(f"Processing page {page_idx + 1}, lines: {len(page.lines)}")
            for line in page.lines:
                full_text += line.content + "\n"
                line_count += 1

        logging.info(f"Text extraction completed. Total lines: {line_count}, Total characters: {len(full_text)}")
        return full_text
        
    except Exception as e:
        logging.error(f"OCR extraction failed: {str(e)}")
        raise Exception(f"OCR extraction failed: {str(e)}")

# Azure OpenAI Summarization (New syntax for openai>=1.0.0)
def summarize_text(text):
    logging.info("Starting text summarization")
    
    api_key = os.getenv("AZURE_OPENAI_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    
    logging.info(f"OpenAI endpoint configured: {bool(endpoint)}")
    logging.info(f"OpenAI key configured: {bool(api_key)}")
    logging.info(f"OpenAI deployment configured: {bool(deployment)}")
    logging.info(f"Text length to summarize: {len(text)} characters")

    if not all([api_key, endpoint, deployment]):
        logging.error("Azure OpenAI credentials missing")
        raise Exception("Azure OpenAI credentials missing")

    try:
        client = AzureOpenAI(
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version="2024-02-15-preview"
        )
        logging.info("AzureOpenAI client created successfully")

        # Truncate text if too long
        max_chars = 4000
        text_to_summarize = text[:max_chars] if len(text) > max_chars else text
        logging.info(f"Text truncated to {len(text_to_summarize)} characters for summarization")

        response = client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that summarizes student uploads."},
                {"role": "user", "content": text_to_summarize}
            ],
            temperature=0.7,
            max_tokens=300
        )
        
        summary = response.choices[0].message.content
        logging.info(f"Summarization completed. Summary length: {len(summary)} characters")
        return summary
        
    except Exception as e:
        logging.error(f"Summarization failed: {str(e)}")
        raise Exception(f"Summarization failed: {str(e)}")

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("=== uploadOCRSummary function triggered ===")
    logging.info(f"Request method: {req.method}")
    logging.info(f"Request URL: {req.url}")
    logging.info(f"Request headers: {dict(req.headers)}")
    
    try:
        if req.method == 'POST':
            logging.info("Processing POST request")
            
            # Handle file upload
            files = req.files
            logging.info(f"Files in request: {len(files) if files else 0}")
            
            if files:
                logging.info("File upload detected")
                
                # Process file
                file = next(iter(files.values()))
                logging.info(f"Processing file: {file.filename}")
                logging.info(f"File content type: {file.content_type}")
                
                file_content = file.read()
                logging.info(f"File read successfully. Size: {len(file_content)} bytes")
                
                try:
                    # Extract text and summarize
                    logging.info("Starting text extraction...")
                    extracted_text = extract_text_from_file(file_content)
                    
                    logging.info("Starting summarization...")
                    summary = summarize_text(extracted_text)
                    
                    response_data = {
                        "message": "Document processed successfully",
                        "filename": file.filename,
                        "extracted_text_length": len(extracted_text),
                        "extracted_text_preview": extracted_text[:200] + "..." if len(extracted_text) > 200 else extracted_text,
                        "summary": summary,
                        "status": "completed"
                    }
                    
                    logging.info("Document processing completed successfully")
                    return func.HttpResponse(
                        json.dumps(response_data),
                        mimetype="application/json",
                        status_code=200
                    )
                    
                except Exception as processing_error:
                    logging.error(f"Processing error: {str(processing_error)}")
                    return func.HttpResponse(
                        json.dumps({
                            "error": f"Processing failed: {str(processing_error)}",
                            "filename": file.filename,
                            "status": "failed"
                        }),
                        mimetype="application/json",
                        status_code=500
                    )
            else:
                logging.warning("No files found in POST request")
                return func.HttpResponse(
                    json.dumps({"error": "No file uploaded"}),
                    mimetype="application/json",
                    status_code=400
                )
        
        # GET request
        logging.info("Processing GET request")
        return func.HttpResponse(
            json.dumps({
                "message": "uploadOCRSummary function is running",
                "description": "Upload documents for OCR and AI summarization",
                "method": "POST",
                "expected_content": "multipart/form-data with file",
                "environment_check": {
                    "form_recognizer_configured": bool(os.getenv("FORM_RECOGNIZER_ENDPOINT") and os.getenv("FORM_RECOGNIZER_KEY")),
                    "openai_configured": bool(os.getenv("AZURE_OPENAI_ENDPOINT") and os.getenv("AZURE_OPENAI_KEY") and os.getenv("AZURE_OPENAI_DEPLOYMENT"))
                }
            }),
            mimetype="application/json",
            status_code=200
        )
        
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        logging.error(f"Error type: {type(e).__name__}")
        import traceback
        logging.error(f"Traceback: {traceback.format_exc()}")
        
        return func.HttpResponse(
            json.dumps({
                "error": f"Unexpected error: {str(e)}",
                "error_type": type(e).__name__,
                "status": "failed"
            }),
            mimetype="application/json",
            status_code=500
        )