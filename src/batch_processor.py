"""Batch processing module for handling multiple files."""
import os
from typing import List, Dict, Callable
from pathlib import Path


class BatchProcessor:
    """Process multiple log files in batch."""
    
    def __init__(self, agent):
        self.agent = agent
        self.processed_files = []
        self.failed_files = []
    
    def process_batch(self, file_paths: List[str], progress_callback: Callable = None) -> Dict:
        """
        Process multiple log files.
        
        Args:
            file_paths: List of file paths to process
            progress_callback: Optional callback for progress updates
            
        Returns:
            Summary of batch processing results
        """
        self.processed_files = []
        self.failed_files = []
        
        total_files = len(file_paths)
        results = {
            "total_files": total_files,
            "successful": 0,
            "failed": 0,
            "processed_files": [],
            "failed_details": []
        }
        
        for i, file_path in enumerate(file_paths):
            try:
                if progress_callback:
                    progress_callback(f"Processing {i+1}/{total_files}: {os.path.basename(file_path)}")
                
                result = self._process_single_file(file_path)
                
                if result.get("success"):
                    results["successful"] += 1
                    results["processed_files"].append(result)
                    self.processed_files.append(file_path)
                else:
                    results["failed"] += 1
                    results["failed_details"].append({
                        "file": os.path.basename(file_path),
                        "error": result.get("error", "Unknown error")
                    })
                    self.failed_files.append(file_path)
            except Exception as e:
                results["failed"] += 1
                results["failed_details"].append({
                    "file": os.path.basename(file_path),
                    "error": str(e)
                })
                self.failed_files.append(file_path)
        
        return results
    
    def _process_single_file(self, file_path: str) -> Dict:
        """Process a single file."""
        try:
            # Validate file
            if not os.path.exists(file_path):
                return {"success": False, "error": "File not found"}
            
            if not file_path.endswith('.log'):
                return {"success": False, "error": "Invalid file format. Expected .log file"}
            
            file_size = os.path.getsize(file_path)
            filename = os.path.basename(file_path)
            
            # Run analysis
            analysis_result = self.agent.run_full_analysis(file_path, filename, file_size)
            
            return {
                "success": True,
                "filename": filename,
                "file_id": analysis_result.get('file_id'),
                "total_logs": analysis_result.get('total_logs', 0),
                "error_count": analysis_result.get('error_count', 0),
                "file_size": file_size
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_batch_statistics(self) -> Dict:
        """Get statistics for processed batch."""
        return {
            "total_processed": len(self.processed_files),
            "total_failed": len(self.failed_files),
            "success_rate": round((len(self.processed_files) / (len(self.processed_files) + len(self.failed_files)) * 100), 2) if (len(self.processed_files) + len(self.failed_files)) > 0 else 0,
            "processed_files": self.processed_files,
            "failed_files": self.failed_files
        }
    
    def get_batch_report(self, results: Dict) -> str:
        """Generate batch processing report."""
        report = "# Batch Processing Report\n\n"
        report += f"**Total Files:** {results['total_files']}\n"
        report += f"**Successful:** {results['successful']} ✅\n"
        report += f"**Failed:** {results['failed']} ❌\n"
        report += f"**Success Rate:** {round((results['successful'] / results['total_files'] * 100), 2) if results['total_files'] > 0 else 0}%\n\n"
        
        if results['processed_files']:
            report += "## Processed Files\n"
            for file_result in results['processed_files']:
                report += f"\n### {file_result['filename']}\n"
                report += f"- File ID: {file_result.get('file_id')}\n"
                report += f"- Total Log Entries: {file_result.get('total_logs')}\n"
                report += f"- Errors Found: {file_result.get('error_count')}\n"
                report += f"- File Size: {file_result.get('file_size')} bytes\n"
        
        if results['failed_details']:
            report += "\n## Failed Files\n"
            for failed in results['failed_details']:
                report += f"\n### {failed['file']}\n"
                report += f"- Error: {failed['error']}\n"
        
        return report
