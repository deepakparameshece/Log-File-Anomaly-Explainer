"""Debug utilities for troubleshooting data retrieval issues."""
import sqlite3
from typing import List, Dict


def inspect_database(db_path: str = "log_analysis.db") -> Dict:
    """Inspect the database and return comprehensive statistics."""
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Get file count
            cursor.execute("SELECT COUNT(*) FROM uploaded_files")
            file_count = cursor.fetchone()[0]
            
            # Get log entry count
            cursor.execute("SELECT COUNT(*) FROM log_entries")
            log_count = cursor.fetchone()[0]
            
            # Get analysis count
            cursor.execute("SELECT COUNT(*) FROM error_analyses")
            analysis_count = cursor.fetchone()[0]
            
            # Get files with their stats
            cursor.execute("""
                SELECT id, filename, total_lines, error_count, upload_date 
                FROM uploaded_files 
                ORDER BY id DESC
            """)
            files = cursor.fetchall()
            
            # Get logs per file
            cursor.execute("""
                SELECT file_id, COUNT(*) as count 
                FROM log_entries 
                GROUP BY file_id
            """)
            logs_per_file = dict(cursor.fetchall())
            
            # Get analyses per file
            cursor.execute("""
                SELECT file_id, COUNT(*) as count 
                FROM error_analyses 
                GROUP BY file_id
            """)
            analyses_per_file = dict(cursor.fetchall())
            
            return {
                "total_files": file_count,
                "total_logs": log_count,
                "total_analyses": analysis_count,
                "files": files,
                "logs_per_file": logs_per_file,
                "analyses_per_file": analyses_per_file
            }
    except Exception as e:
        return {"error": str(e)}


def get_file_data(file_id: int, db_path: str = "log_analysis.db") -> Dict:
    """Get detailed data for a specific file."""
    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get file info
            cursor.execute("SELECT * FROM uploaded_files WHERE id = ?", (file_id,))
            file_info = dict(cursor.fetchone() or {})
            
            # Get log entries
            cursor.execute("""
                SELECT * FROM log_entries 
                WHERE file_id = ? 
                ORDER BY line_number LIMIT 10
            """, (file_id,))
            sample_logs = [dict(row) for row in cursor.fetchall()]
            
            # Get analyses
            cursor.execute("""
                SELECT * FROM error_analyses 
                WHERE file_id = ? 
                ORDER BY analysis_date LIMIT 10
            """, (file_id,))
            sample_analyses = [dict(row) for row in cursor.fetchall()]
            
            return {
                "file_info": file_info,
                "sample_logs": sample_logs,
                "sample_analyses": sample_analyses,
                "log_count": len(sample_logs),
                "analysis_count": len(sample_analyses)
            }
    except Exception as e:
        return {"error": str(e)}


def validate_file_data(file_id: int, db_path: str = "log_analysis.db") -> Dict:
    """Validate data integrity for a file."""
    issues = []
    warnings = []
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Check if file exists
            cursor.execute("SELECT id FROM uploaded_files WHERE id = ?", (file_id,))
            if not cursor.fetchone():
                issues.append(f"File with ID {file_id} not found")
                return {"valid": False, "issues": issues, "warnings": warnings}
            
            # Check log entries
            cursor.execute("SELECT COUNT(*) FROM log_entries WHERE file_id = ?", (file_id,))
            log_count = cursor.fetchone()[0]
            if log_count == 0:
                warnings.append("No log entries found for this file")
            
            # Check analyses
            cursor.execute("SELECT COUNT(*) FROM error_analyses WHERE file_id = ?", (file_id,))
            analysis_count = cursor.fetchone()[0]
            if analysis_count == 0:
                warnings.append("No error analyses found for this file")
            
            # Check for orphaned analyses (log entries without analyses)
            cursor.execute("""
                SELECT COUNT(*) FROM log_entries 
                WHERE file_id = ? AND id NOT IN (
                    SELECT log_entry_id FROM error_analyses WHERE file_id = ?
                )
            """, (file_id, file_id))
            orphaned = cursor.fetchone()[0]
            if orphaned > 0:
                warnings.append(f"{orphaned} log entries have no associated analyses")
            
            # Check for log entries without content
            cursor.execute("""
                SELECT COUNT(*) FROM log_entries 
                WHERE file_id = ? AND (content IS NULL OR content = '')
            """, (file_id,))
            empty_content = cursor.fetchone()[0]
            if empty_content > 0:
                warnings.append(f"{empty_content} log entries have empty content")
            
            return {
                "valid": len(issues) == 0,
                "issues": issues,
                "warnings": warnings,
                "stats": {
                    "total_logs": log_count,
                    "total_analyses": analysis_count,
                    "orphaned_logs": orphaned,
                    "empty_content": empty_content
                }
            }
    except Exception as e:
        issues.append(f"Error during validation: {str(e)}")
        return {"valid": False, "issues": issues, "warnings": warnings}
