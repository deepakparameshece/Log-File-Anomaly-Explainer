import sqlite3
import json
from datetime import datetime
from typing import List, Optional
import os

class DatabaseManager:
    def __init__(self, db_path: str = "log_analysis.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Table for storing uploaded files
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS uploaded_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    file_size INTEGER,
                    total_lines INTEGER,
                    error_count INTEGER DEFAULT 0
                )
            """)
            
            # Table for storing individual log entries
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS log_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id INTEGER,
                    line_number INTEGER,
                    timestamp TEXT,
                    log_level TEXT,
                    content TEXT,
                    risk_level TEXT DEFAULT 'LOW',
                    FOREIGN KEY (file_id) REFERENCES uploaded_files (id)
                )
            """)
            
            # Table for storing error analysis
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS error_analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id INTEGER,
                    log_entry_id INTEGER,
                    identified_error TEXT,
                    probable_cause TEXT,
                    suggested_fix TEXT,
                    error_context TEXT,
                    analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (file_id) REFERENCES uploaded_files (id),
                    FOREIGN KEY (log_entry_id) REFERENCES log_entries (id)
                )
            """)
            
            conn.commit()
    
    def store_uploaded_file(self, filename: str, file_size: int) -> int:
        """Store uploaded file information and return file_id"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO uploaded_files (filename, file_size)
                VALUES (?, ?)
            """, (filename, file_size))
            conn.commit()
            return cursor.lastrowid
    
    def store_log_entry(self, file_id: int, line_number: int, timestamp: str, 
                       log_level: str, content: str, risk_level: str):
        """Store individual log entry"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO log_entries (file_id, line_number, timestamp, log_level, content, risk_level)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (file_id, line_number, timestamp, log_level, content, risk_level))
            conn.commit()
            return cursor.lastrowid
    
    def store_error_analysis(self, file_id: int, log_entry_id: int, 
                           identified_error: str, probable_cause: str, 
                           suggested_fix: str, error_context: str):
        """Store error analysis results"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO error_analyses (file_id, log_entry_id, identified_error, 
                                          probable_cause, suggested_fix, error_context)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (file_id, log_entry_id, identified_error, probable_cause, suggested_fix, error_context))
            conn.commit()
            return cursor.lastrowid
    
    def get_uploaded_files(self) -> List[dict]:
        """Get all uploaded files"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM uploaded_files ORDER BY upload_date DESC
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_log_entries(self, file_id: int) -> List[dict]:
        """Get all log entries for a specific file"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM log_entries 
                WHERE file_id = ? 
                ORDER BY line_number
            """, (file_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_error_analyses(self, file_id: int) -> List[dict]:
        """Get all error analyses for a specific file"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ea.*, le.line_number, le.content as log_content
                FROM error_analyses ea
                LEFT JOIN log_entries le ON ea.log_entry_id = le.id
                WHERE ea.file_id = ?
                ORDER BY ea.analysis_date
            """, (file_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    def update_file_stats(self, file_id: int, total_lines: int, error_count: int):
        """Update file statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE uploaded_files 
                SET total_lines = ?, error_count = ?
                WHERE id = ?
            """, (total_lines, error_count, file_id))
            conn.commit()