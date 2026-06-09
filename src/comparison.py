"""Module for comparing multiple log files."""
from typing import List, Dict
import pandas as pd


class FileComparator:
    """Compare and analyze multiple log files."""
    
    def __init__(self):
        pass
    
    def compare_files(self, files_data: List[Dict]) -> Dict:
        """
        Compare multiple files.
        
        Args:
            files_data: List of dicts with file_info, logs, and analyses
            
        Returns:
            Comparison analysis
        """
        if len(files_data) < 2:
            return {"error": "At least 2 files required for comparison"}
        
        try:
            comparison = {
                "file_count": len(files_data),
                "metrics": [],
                "common_errors": [],
                "unique_errors": {},
                "trend": {}
            }
            
            # Calculate metrics for each file
            for file_data in files_data:
                file_info = file_data.get('file_info', {})
                logs = file_data.get('logs', [])
                analyses = file_data.get('analyses', [])
                
                metrics = {
                    "filename": file_info.get('filename', 'Unknown'),
                    "file_id": file_info.get('id'),
                    "total_entries": len(logs),
                    "error_count": len(analyses),
                    "critical_count": len([l for l in logs if l.get('risk_level') == 'CRITICAL']),
                    "high_count": len([l for l in logs if l.get('risk_level') == 'HIGH']),
                    "error_rate": round((len(analyses) / len(logs)) * 100, 2) if logs else 0,
                    "upload_date": file_info.get('upload_date', 'N/A')
                }
                comparison["metrics"].append(metrics)
            
            # Find common errors
            comparison["common_errors"] = self._find_common_errors(files_data)
            
            # Find unique errors per file
            comparison["unique_errors"] = self._find_unique_errors(files_data)
            
            # Calculate trend
            comparison["trend"] = self._calculate_comparison_trend(comparison["metrics"])
            
            return comparison
        except Exception as e:
            return {"error": str(e)}
    
    def _find_common_errors(self, files_data: List[Dict]) -> List[Dict]:
        """Find errors common to multiple files."""
        if len(files_data) < 2:
            return []
        
        try:
            # Get error signatures from first file
            first_errors = set()
            for analysis in files_data[0].get('analyses', []):
                error = analysis.get('identified_error', '').lower().strip()
                if error:
                    first_errors.add(error[:50])  # Use first 50 chars as signature
            
            # Find intersection with other files
            common = []
            for error_sig in first_errors:
                in_all = True
                for file_data in files_data[1:]:
                    found = False
                    for analysis in file_data.get('analyses', []):
                        error = analysis.get('identified_error', '').lower().strip()
                        if error.startswith(error_sig[:30]):
                            found = True
                            break
                    if not found:
                        in_all = False
                        break
                
                if in_all:
                    common.append({
                        "error_signature": error_sig,
                        "files_affected": len(files_data)
                    })
            
            return common[:10]  # Top 10 common errors
        except Exception:
            return []
    
    def _find_unique_errors(self, files_data: List[Dict]) -> Dict[str, List[str]]:
        """Find errors unique to each file."""
        unique_errors = {}
        
        try:
            for i, file_data in enumerate(files_data):
                file_info = file_data.get('file_info', {})
                filename = file_info.get('filename', f'File {i+1}')
                
                file_errors = set()
                for analysis in file_data.get('analyses', []):
                    error = analysis.get('identified_error', '').lower().strip()
                    if error:
                        file_errors.add(error[:50])
                
                # Find errors not in other files
                unique = []
                for error in file_errors:
                    found_elsewhere = False
                    for j, other_data in enumerate(files_data):
                        if i == j:
                            continue
                        for analysis in other_data.get('analyses', []):
                            other_error = analysis.get('identified_error', '').lower().strip()
                            if other_error.startswith(error[:30]):
                                found_elsewhere = True
                                break
                        if found_elsewhere:
                            break
                    
                    if not found_elsewhere:
                        unique.append(error)
                
                if unique:
                    unique_errors[filename] = unique[:5]  # Top 5 unique errors
        except Exception:
            pass
        
        return unique_errors
    
    def _calculate_comparison_trend(self, metrics: List[Dict]) -> Dict:
        """Calculate trend across files."""
        try:
            if not metrics:
                return {}
            
            error_counts = [m['error_count'] for m in metrics]
            error_rates = [m['error_rate'] for m in metrics]
            
            trend = {
                "total_errors": sum(error_counts),
                "average_errors_per_file": round(sum(error_counts) / len(metrics), 2),
                "max_errors": max(error_counts),
                "min_errors": min(error_counts),
                "average_error_rate": round(sum(error_rates) / len(metrics), 2),
                "trend_direction": "increasing" if error_counts[-1] > error_counts[0] else "decreasing"
            }
            
            return trend
        except Exception:
            return {}
    
    def get_comparison_summary(self, comparison: Dict) -> str:
        """Generate a summary of file comparison."""
        summary = f"## Comparison Summary\n\n"
        summary += f"**Files Compared:** {comparison.get('file_count', 0)}\n\n"
        
        summary += "### Metrics Comparison\n"
        for metric in comparison.get('metrics', []):
            summary += f"- **{metric['filename']}**\n"
            summary += f"  - Total Entries: {metric['total_entries']}\n"
            summary += f"  - Error Count: {metric['error_count']}\n"
            summary += f"  - Error Rate: {metric['error_rate']}%\n"
        
        if comparison.get('common_errors'):
            summary += f"\n### Common Errors ({len(comparison['common_errors'])} found)\n"
            for error in comparison['common_errors'][:5]:
                summary += f"- {error['error_signature']}\n"
        
        if comparison.get('unique_errors'):
            summary += "\n### Unique Errors\n"
            for filename, errors in comparison['unique_errors'].items():
                summary += f"- **{filename}**: {', '.join(errors[:3])}\n"
        
        return summary
