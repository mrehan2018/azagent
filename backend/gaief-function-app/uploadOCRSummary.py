import azure.functions as func
import datetime
import json
import logging

app = func.FunctionApp()

@app.route(route="uploadOCRSummary", auth_level=func.AuthLevel.ANONYMOUS)
def uploadOCRSummary(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('uploadOCRSummary HTTP trigger function processed a request.')

    try:
        # Check if request has a file upload
        if req.method == 'POST':
            # Get file from request
            file_data = None
            content_type = req.headers.get('content-type', '')
            
            if 'multipart/form-data' in content_type:
                # Handle file upload
                try:
                    files = req.files
                    if files:
                        file_data = next(iter(files.values()))
                        logging.info(f"Received file: {file_data.filename}")
                        
                        # Process the file here
                        # TODO: Add OCR processing logic
                        # TODO: Add AI summarization logic
                        
                        return func.HttpResponse(
                            json.dumps({
                                "message": "File uploaded successfully",
                                "filename": file_data.filename,
                                "status": "processing",
                                "timestamp": datetime.datetime.utcnow().isoformat()
                            }),
                            mimetype="application/json",
                            status_code=200
                        )
                except Exception as e:
                    logging.error(f"Error processing file upload: {str(e)}")
                    return func.HttpResponse(
                        json.dumps({"error": f"File processing error: {str(e)}"}),
                        mimetype="application/json",
                        status_code=400
                    )
            
            elif 'application/json' in content_type:
                # Handle JSON request
                try:
                    req_body = req.get_json()
                    text_content = req_body.get('text', '')
                    
                    if text_content:
                        # TODO: Add AI summarization for text content
                        return func.HttpResponse(
                            json.dumps({
                                "message": "Text processed successfully",
                                "summary": f"Summary of: {text_content[:100]}...",
                                "timestamp": datetime.datetime.utcnow().isoformat()
                            }),
                            mimetype="application/json",
                            status_code=200
                        )
                except Exception as e:
                    logging.error(f"Error processing JSON: {str(e)}")
                    return func.HttpResponse(
                        json.dumps({"error": f"JSON processing error: {str(e)}"}),
                        mimetype="application/json",
                        status_code=400
                    )
        
        # GET request or fallback
        return func.HttpResponse(
            json.dumps({
                "message": "uploadOCRSummary function is running",
                "description": "POST files or text for OCR and summarization",
                "endpoints": {
                    "file_upload": "POST with multipart/form-data",
                    "text_processing": "POST with JSON {'text': 'your text'}"
                },
                "timestamp": datetime.datetime.utcnow().isoformat()
            }),
            mimetype="application/json",
            status_code=200
        )
        
    except Exception as e:
        logging.error(f"Unexpected error in uploadOCRSummary: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": f"Unexpected error: {str(e)}"}),
            mimetype="application/json",
            status_code=500
        )