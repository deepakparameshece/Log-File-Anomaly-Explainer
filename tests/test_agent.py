import os
from unittest.mock import patch, MagicMock
from src.agent import AgentEngine
from src.llm_client import ErrorAnalysis

@patch('src.llm_client.ollama.chat')
def test_agent_run_analysis(mock_chat, tmp_path):
    # Mock the LLM response
    mock_chat.return_value = {
        "message": {
            "content": '{"identified_error": "FakeError", "probable_cause": "Fake Cause", "suggested_fix": "Fake Fix", "needs_more_info": false}'
        }
    }
    
    # Create a small log file
    log_file = tmp_path / "test.log"
    log_file.write_text("INFO 1\nERROR FakeError\nINFO 2\n")
    
    agent = AgentEngine(model_name="llama3")
    analyses = agent.run_analysis(str(log_file))
    
    assert len(analyses) == 1
    assert analyses[0].identified_error == "FakeError"
    assert not analyses[0].needs_more_info
    
    # Generate report
    report_path = tmp_path / "report.md"
    agent.generate_markdown_report(analyses, str(report_path))
    
    report_content = report_path.read_text()
    assert "FakeError" in report_content
    assert "Fake Cause" in report_content
    assert "Fake Fix" in report_content

@patch('src.llm_client.ollama.chat')
def test_agent_refinement(mock_chat, tmp_path):
    # First response needs more info, second response resolves it
    mock_chat.side_effect = [
        {
            "message": {
                "content": '{"identified_error": "DatabaseConnectionError", "probable_cause": "Unknown", "suggested_fix": "Unknown", "needs_more_info": true}'
            }
        },
        {
            "message": {
                "content": '{"identified_error": "DatabaseConnectionError", "probable_cause": "Firewall", "suggested_fix": "Open Port", "needs_more_info": false}'
            }
        }
    ]
    
    log_file = tmp_path / "test2.log"
    log_file.write_text("ERROR DatabaseConnectionError\n")
    
    agent = AgentEngine()
    
    # Mock KB loading to avoid dependency on CWD
    agent._load_kb = MagicMock(return_value={"DatabaseConnectionError": {"description": "desc", "resolution": "res"}})
    
    analyses = agent.run_analysis(str(log_file))
    
    assert len(analyses) == 1
    assert analyses[0].probable_cause == "Firewall"
    assert analyses[0].suggested_fix == "Open Port"
    assert mock_chat.call_count == 2
