import os
import shutil
from fastapi import FastAPI, UploadFile, File, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from .agent import AgentEngine
from .report_generator import ReportGenerator

app = FastAPI(title="Log File Anomaly Explainer")

# Setup templates and static files
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# Initialize Agent Engine and Report Generator
agent = AgentEngine(model_name="llama3.2")
report_generator = ReportGenerator()

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.post("/api/analyze")
async def analyze_log(file: UploadFile = File(...)):
    if not file.filename.endswith('.log'):
        return JSONResponse(status_code=400, content={"error": "File must be a .log file."})
    
    # Save the uploaded file temporarily
    temp_file_path = f"temp_{file.filename}"
    with open(temp_file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        # Get file size
        file_size = os.path.getsize(temp_file_path)
        
        # Run full analysis with database storage
        result = agent.run_full_analysis(temp_file_path, file.filename, file_size)
        
        return JSONResponse(content={
            "success": True,
            "file_id": result["file_id"],
            "message": f"Analysis complete. Found {result['error_count']} errors in {result['total_logs']} log entries.",
            "total_logs": result["total_logs"],
            "error_count": result["error_count"]
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        # Cleanup
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

@app.get("/api/files")
async def get_uploaded_files():
    """Get all uploaded files"""
    try:
        files = agent.get_uploaded_files()
        return JSONResponse(content={"files": files})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/files/{file_id}/logs")
async def get_file_logs(file_id: int):
    """Get all log entries for a specific file"""
    try:
        logs = agent.get_file_logs(file_id)
        return JSONResponse(content={"logs": logs})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/files/{file_id}/analyses")
async def get_file_analyses(file_id: int):
    """Get error analyses for a specific file"""
    try:
        analyses = agent.get_file_analyses(file_id)
        return JSONResponse(content={"analyses": analyses})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/logs/{file_id}", response_class=HTMLResponse)
async def view_logs(request: Request, file_id: int):
    """View logs page for a specific file"""
    return templates.TemplateResponse(request=request, name="logs.html", context={"file_id": file_id})

@app.get("/api/files/{file_id}/download/{format}")
async def download_report(file_id: int, format: str):
    """Download analysis report in specified format (pdf, html, json, markdown)"""
    if format not in ['pdf', 'html', 'json', 'markdown']:
        raise HTTPException(status_code=400, detail="Invalid format. Supported formats: pdf, html, json, markdown")
    
    try:
        # Get file information
        files = agent.get_uploaded_files()
        file_info = next((f for f in files if f['id'] == file_id), None)
        if not file_info:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Get logs and analyses
        logs = agent.get_file_logs(file_id)
        analyses = agent.get_file_analyses(file_id)
        
        filename_base = os.path.splitext(file_info['filename'])[0]
        
        if format == 'pdf':
            pdf_data = report_generator.generate_pdf_report(file_info, logs, analyses)
            return Response(
                content=pdf_data,
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename={filename_base}_analysis.pdf"}
            )
        
        elif format == 'html':
            html_content = report_generator.generate_html_report(file_info, logs, analyses)
            return Response(
                content=html_content,
                media_type="text/html",
                headers={"Content-Disposition": f"attachment; filename={filename_base}_analysis.html"}
            )
        
        elif format == 'json':
            json_content = report_generator.generate_json_report(file_info, logs, analyses)
            return Response(
                content=json_content,
                media_type="application/json",
                headers={"Content-Disposition": f"attachment; filename={filename_base}_analysis.json"}
            )
        
        elif format == 'markdown':
            markdown_content = report_generator.generate_markdown_report(file_info, logs, analyses)
            return Response(
                content=markdown_content,
                media_type="text/markdown",
                headers={"Content-Disposition": f"attachment; filename={filename_base}_analysis.md"}
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating report: {str(e)}")

@app.get("/api/files/{file_id}/report-info")
async def get_report_info(file_id: int):
    """Get information about available report formats"""
    try:
        # Get file information to check if it exists
        files = agent.get_uploaded_files()
        file_info = next((f for f in files if f['id'] == file_id), None)
        if not file_info:
            raise HTTPException(status_code=404, detail="File not found")
        
        filename_base = os.path.splitext(file_info['filename'])[0]
        
        formats = {
            "pdf": {
                "name": "PDF Report",
                "description": "Formatted PDF document with charts and tables",
                "filename": f"{filename_base}_analysis.pdf",
                "icon": "📄"
            },
            "html": {
                "name": "HTML Report", 
                "description": "Styled HTML page that can be opened in any browser",
                "filename": f"{filename_base}_analysis.html",
                "icon": "🌐"
            },
            "json": {
                "name": "JSON Data",
                "description": "Structured data format for programmatic use",
                "filename": f"{filename_base}_analysis.json",
                "icon": "📋"
            },
            "markdown": {
                "name": "Markdown Document",
                "description": "Plain text format with markdown formatting",
                "filename": f"{filename_base}_analysis.md",
                "icon": "📝"
            }
        }
        
        return JSONResponse(content={"formats": formats})
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting report info: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.web:app", host="0.0.0.0", port=8000, reload=True)
