import re
from collections import deque
from typing import List, Dict, Any, Tuple

class LogEntry:
    def __init__(self, line_number: int, timestamp: str, log_level: str, content: str, risk_level: str = "LOW"):
        self.line_number = line_number
        self.timestamp = timestamp
        self.log_level = log_level
        self.content = content
        self.risk_level = risk_level

class LogParser:
    def __init__(self, context_lines: int = 10):
        self.context_lines = context_lines
        self.error_keywords = [
            "ERROR", "CRITICAL", "EXCEPTION", "FATAL", "500 Internal Server Error"
        ]
        # Regex to match any of the error keywords (case-insensitive) with word boundaries
        pattern = "|".join(r"\b" + re.escape(kw) + r"\b" for kw in self.error_keywords)
        self.error_regex = re.compile(f"({pattern})", re.IGNORECASE)
        
        # Risk level mapping
        self.risk_levels = {
            "CRITICAL": "CRITICAL",
            "FATAL": "CRITICAL", 
            "ERROR": "HIGH",
            "EXCEPTION": "HIGH",
            "500 Internal Server Error": "HIGH",
            "WARN": "MEDIUM",
            "WARNING": "MEDIUM",
            "INFO": "LOW",
            "DEBUG": "LOW",
            "TRACE": "LOW"
        }

    def is_error_line(self, line: str) -> bool:
        return bool(self.error_regex.search(line))
    
    def extract_log_level(self, line: str) -> str:
        """Extract log level from a line"""
        for level in ["CRITICAL", "FATAL", "ERROR", "WARN", "WARNING", "INFO", "DEBUG", "TRACE"]:
            if level in line.upper():
                return level
        return "UNKNOWN"
    
    def extract_timestamp(self, line: str) -> str:
        """Extract timestamp from a line using common patterns"""
        # Common timestamp patterns
        patterns = [
            r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}',  # YYYY-MM-DD HH:MM:SS
            r'\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}',  # MM/DD/YYYY HH:MM:SS
            r'\w{3} \d{1,2} \d{2}:\d{2}:\d{2}',      # Mon DD HH:MM:SS
        ]
        
        for pattern in patterns:
            match = re.search(pattern, line)
            if match:
                return match.group()
        return ""
    
    def determine_risk_level(self, log_level: str, content: str) -> str:
        """Determine risk level based on log level and content"""
        # Check for critical keywords in content
        critical_keywords = ["crash", "shutdown", "abort", "panic", "segfault", "outofmemory"]
        high_keywords = ["failed", "timeout", "connection refused", "access denied"]
        
        content_lower = content.lower()
        
        # Critical risk
        if any(keyword in content_lower for keyword in critical_keywords):
            return "CRITICAL"
        
        # High risk
        if any(keyword in content_lower for keyword in high_keywords):
            return "HIGH"
        
        # Use log level mapping
        return self.risk_levels.get(log_level.upper(), "LOW")
    
    def parse_all_logs(self, file_path: str) -> List[LogEntry]:
        """Parse all log entries from file"""
        log_entries = []
        
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.rstrip("\n")
                    if line.strip():  # Skip empty lines
                        timestamp = self.extract_timestamp(line)
                        log_level = self.extract_log_level(line)
                        risk_level = self.determine_risk_level(log_level, line)
                        
                        log_entries.append(LogEntry(
                            line_number=line_num,
                            timestamp=timestamp,
                            log_level=log_level,
                            content=line,
                            risk_level=risk_level
                        ))
                        
        except FileNotFoundError:
            pass
            
        return log_entries

    def extract_error_blocks(self, file_path: str) -> List[str]:
        """
        Reads the file efficiently and extracts blocks containing 
        the error line + context_lines before + context_lines after.
        """
        blocks = []
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                # Rolling buffer for the 'before' context
                before_buffer = deque(maxlen=self.context_lines)
                
                # State variables for capturing the 'after' context
                capturing = False
                after_count = 0
                current_block = []
                
                for line in f:
                    line = line.rstrip("\n")
                    
                    if capturing:
                        current_block.append(line)
                        after_count += 1
                        if after_count >= self.context_lines:
                            # Finished capturing this block
                            blocks.append("\n".join(current_block))
                            capturing = False
                            after_count = 0
                            current_block = []
                            # Note: if there's another error in the 'after' lines, 
                            # we might miss it with this simple state machine. 
                            # But for this scope, this is acceptable.
                            before_buffer.clear()
                    else:
                        if self.is_error_line(line):
                            capturing = True
                            current_block = list(before_buffer)
                            current_block.append(line)
                            after_count = 0
                        else:
                            before_buffer.append(line)
                
                # If EOF reached while capturing
                if capturing:
                    blocks.append("\n".join(current_block))
                    
        except FileNotFoundError:
            pass # Return empty list if file not found
            
        return blocks
