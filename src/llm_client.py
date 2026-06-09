import json
from pydantic import BaseModel, Field
import ollama

class ErrorAnalysis(BaseModel):
    identified_error: str = Field(description="The exact error that occurred.")
    probable_cause: str = Field(description="The probable root cause.")
    suggested_fix: str = Field(description="Suggested steps to fix the issue.")
    needs_more_info: bool = Field(description="True if the log snippet is ambiguous and you cannot determine the root cause, requiring internal KB.")

class OllamaClient:
    def __init__(self, model_name: str = "llama3"):
        self.model_name = model_name
        self.system_prompt = """You are an expert Senior DevOps Engineer and Site Reliability Engineer. 
Your task is to analyze the following extracted log snippet, which contains an error along with its surrounding context.
Analyze the log block to determine the exact error, probable root cause, and suggested fix.
If the log snippet is ambiguous and you cannot determine the root cause, set "needs_more_info" to true."""

    def analyze_log(self, log_content: str) -> ErrorAnalysis:
        prompt = f"Please analyze this log extract.\n\n### Log Extract\n{log_content}"
        
        response = ollama.chat(
            model=self.model_name,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt}
            ],
            format=ErrorAnalysis.model_json_schema()
        )
        
        try:
            return ErrorAnalysis.model_validate_json(response["message"]["content"])
        except Exception:
            # Fallback if parsing fails
            return ErrorAnalysis(
                identified_error="Parse failed",
                probable_cause="LLM returned invalid JSON structure.",
                suggested_fix="Try again or check LLM output.",
                needs_more_info=False
            )

    def refine_analysis(self, log_content: str, kb_info: str) -> ErrorAnalysis:
        prompt = f"""The previous analysis was ambiguous. Here is some internal documentation from our Knowledge Base related to similar errors.
Use this to refine your analysis.

### Internal Knowledge Base Info
{kb_info}

### Log Extract
{log_content}"""

        response = ollama.chat(
            model=self.model_name,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt}
            ],
            format=ErrorAnalysis.model_json_schema()
        )
        
        try:
            return ErrorAnalysis.model_validate_json(response["message"]["content"])
        except Exception:
            return ErrorAnalysis(
                identified_error="Parse failed on refinement",
                probable_cause="LLM returned invalid JSON structure.",
                suggested_fix="Try again or check LLM output.",
                needs_more_info=False
            )
