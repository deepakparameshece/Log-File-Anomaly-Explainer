import os
from src.parser import LogParser

def test_extract_error_blocks():
    # Setup
    parser = LogParser(context_lines=2) # use smaller context for easy testing
    fixture_path = "fixtures/sample_crash.log"
    
    # Execution
    blocks = parser.extract_error_blocks(fixture_path)
    
    # Assertions
    assert len(blocks) == 2
    
    # Block 1 should contain DatabaseConnectionError
    assert "DatabaseConnectionError" in blocks[0]
    assert "Handling request POST /api/payment" in blocks[0]
    
    # Block 2 should contain OutOfMemoryError
    assert "OutOfMemoryError" in blocks[1]
    assert "CRITICAL System crashed" in blocks[1]

def test_extract_error_blocks_empty_file(tmp_path):
    parser = LogParser(context_lines=5)
    empty_log = tmp_path / "empty.log"
    empty_log.write_text("")
    
    blocks = parser.extract_error_blocks(str(empty_log))
    assert blocks == []

def test_extract_error_blocks_no_errors(tmp_path):
    parser = LogParser(context_lines=5)
    clean_log = tmp_path / "clean.log"
    clean_log.write_text("INFO 1\nINFO 2\nDEBUG 3\n")
    
    blocks = parser.extract_error_blocks(str(clean_log))
    assert blocks == []
