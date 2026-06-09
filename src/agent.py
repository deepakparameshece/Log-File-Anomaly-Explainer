import json
import os
from typing import List
from .parser import LogParser, LogEntry
from .llm_client import OllamaClient, ErrorAnalysis
from .database import DatabaseManager

class AgentEngine:
    def __init__(self, model_name: str = "llama3"):
        self.parser = LogParser()
        self.llm_client = OllamaClient(model_name=model_name)
        self.kb_path = "error_knowledge_base.json"
        self.db = DatabaseManager()

    def _load_kb(self) -> dict:
        if not os.path.exists(self.kb_path):
            return {}
        try:
            with open(self.kb_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _get_relevant_kb_info(self, error_summary: str) -> str:
        kb = self._load_kb()
        # Basic matching logic: check if any KB key is in the error summary
        relevant_entries = []
        for key, value in kb.items():
            if key.lower() in error_summary.lower():
                relevant_entries.append(f"Error Type: {key}\nDescription: {value['description']}\nResolution: {value['resolution']}")
        
        if relevant_entries:
            return "\n\n".join(relevant_entries)
        
        # Fallback to dumping the whole KB if it's small, 
        # or just say no specific match found.
        return json.dumps(kb, indent=2)

    def run_full_analysis(self, log_path: str, filename: str, file_size: int) -> dict:
        """Run complete analysis and store everything in database"""
        # Store uploaded file in database
        file_id = self.db.store_uploaded_file(filename, file_size)
        
        # Parse all log entries
        all_logs = self.parser.parse_all_logs(log_path)
        
        # Store all log entries in database
        error_entries = []
        for log_entry in all_logs:
            log_entry_id = self.db.store_log_entry(
                file_id=file_id,
                line_number=log_entry.line_number,
                timestamp=log_entry.timestamp,
                log_level=log_entry.log_level,
                content=log_entry.content,
                risk_level=log_entry.risk_level
            )
            
            # If this is an error entry, store it for analysis
            if self.parser.is_error_line(log_entry.content):
                error_entries.append((log_entry_id, log_entry))
        
        # Analyze errors using existing method
        error_blocks = self.parser.extract_error_blocks(log_path)
        error_analyses = []
        
        for i, block in enumerate(error_blocks):
            analysis = self.llm_client.analyze_log(block)
            
            if analysis.needs_more_info:
                kb_info = self._get_relevant_kb_info(analysis.identified_error)
                analysis = self.llm_client.refine_analysis(block, kb_info)
            
            # Find corresponding log entry for this error block
            log_entry_id = None
            if i < len(error_entries):
                log_entry_id = error_entries[i][0]
            
            # Store error analysis in database
            self.db.store_error_analysis(
                file_id=file_id,
                log_entry_id=log_entry_id,
                identified_error=analysis.identified_error,
                probable_cause=analysis.probable_cause,
                suggested_fix=analysis.suggested_fix,
                error_context=block
            )
            
            error_analyses.append(analysis)
        
        # Update file statistics
        self.db.update_file_stats(file_id, len(all_logs), len(error_analyses))
        
        return {
            "file_id": file_id,
            "total_logs": len(all_logs),
            "error_count": len(error_analyses),
            "analyses": error_analyses
        }

    def generate_markdown_report(self, analyses: list[ErrorAnalysis], output_path: str):
        if not analyses:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("# Log File Anomaly Report\n\nNo errors found in the provided log file.\n")
            return

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("# Log File Anomaly Report\n\n")
            for i, analysis in enumerate(analyses, 1):
                f.write(f"## Anomaly #{i}\n\n")
                f.write(f"### Identified Error\n{analysis.identified_error}\n\n")
                f.write(f"### Probable Cause\n{analysis.probable_cause}\n\n")
                f.write(f"### Suggested Fix / Remediation Steps\n{analysis.suggested_fix}\n\n")
                f.write("---\n\n")
    def run_analysis(self, log_path: str) -> list[ErrorAnalysis]:
        """Legacy method for backward compatibility"""
        error_blocks = self.parser.extract_error_blocks(log_path)
        
        if not error_blocks:
            return []

        results = []
        for block in error_blocks:
            analysis = self.llm_client.analyze_log(block)
            
            if analysis.needs_more_info:
                kb_info = self._get_relevant_kb_info(analysis.identified_error)
                analysis = self.llm_client.refine_analysis(block, kb_info)
            
            results.append(analysis)
            
        return results
    
    def get_file_logs(self, file_id: int) -> List[dict]:
        """Get all log entries for a file"""
        return self.db.get_log_entries(file_id)
    
    def get_file_analyses(self, file_id: int) -> List[dict]:
        """Get all error analyses for a file"""
        return self.db.get_error_analyses(file_id)
    
    def get_uploaded_files(self) -> List[dict]:
        """Get all uploaded files"""
        return self.db.get_uploaded_files()