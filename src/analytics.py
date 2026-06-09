"""Advanced analytics and statistical analysis module for log data."""
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from collections import Counter
import statistics


class LogAnalytics:
    """Provides advanced analytics and statistical insights."""
    
    def __init__(self):
        pass
    
    def calculate_error_trends(self, logs: List[Dict], time_window: int = 60) -> Dict:
        """
        Calculate error trends over time.
        
        Args:
            logs: List of log entries
            time_window: Time window in minutes for trend calculation
            
        Returns:
            Dictionary with trend analysis data
        """
        if not logs:
            return {"error": "No logs provided"}
        
        try:
            df = pd.DataFrame(logs)
            
            # Convert timestamp to datetime if available
            if 'timestamp' in df.columns and df['timestamp'].dtype == 'object':
                df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
            
            # Get error logs only
            error_logs = df[df['log_level'].isin(['ERROR', 'CRITICAL'])] if 'log_level' in df.columns else df
            
            if error_logs.empty:
                return {"trend": "stable", "error_count": 0, "severity": "low"}
            
            # Calculate trend
            error_count = len(error_logs)
            
            # Determine severity trend
            if error_count > 50:
                severity = "critical"
            elif error_count > 20:
                severity = "high"
            elif error_count > 10:
                severity = "medium"
            else:
                severity = "low"
            
            return {
                "total_errors": error_count,
                "unique_error_types": len(error_logs['log_level'].unique()) if 'log_level' in error_logs.columns else 0,
                "severity": severity,
                "trend": "increasing" if error_count > 10 else "stable"
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_log_statistics(self, logs: List[Dict]) -> Dict:
        """Calculate comprehensive log statistics."""
        if not logs:
            return {}
        
        try:
            df = pd.DataFrame(logs)
            stats = {
                "total_entries": len(logs),
                "unique_log_levels": df['log_level'].nunique() if 'log_level' in df.columns else 0,
                "unique_risk_levels": df['risk_level'].nunique() if 'risk_level' in df.columns else 0,
                "log_level_distribution": df['log_level'].value_counts().to_dict() if 'log_level' in df.columns else {},
                "risk_level_distribution": df['risk_level'].value_counts().to_dict() if 'risk_level' in df.columns else {},
            }
            
            # Calculate percentages
            if df['log_level'].nunique() > 0:
                stats["log_level_percentages"] = (df['log_level'].value_counts(normalize=True) * 100).round(2).to_dict()
            
            if df['risk_level'].nunique() > 0:
                stats["risk_level_percentages"] = (df['risk_level'].value_counts(normalize=True) * 100).round(2).to_dict()
            
            return stats
        except Exception as e:
            return {"error": str(e)}
    
    def calculate_severity_score(self, logs: List[Dict], analyses: List[Dict]) -> Dict:
        """
        Calculate overall severity score for log file.
        
        Returns score from 0-100 and recommendations
        """
        if not logs:
            return {"score": 0, "level": "low", "recommendations": []}
        
        try:
            df = pd.DataFrame(logs)
            
            # Factor 1: Error ratio (0-40 points)
            error_count = len(df[df['log_level'].isin(['ERROR', 'CRITICAL'])]) if 'log_level' in df.columns else 0
            error_ratio_score = min(40, (error_count / len(logs)) * 100)
            
            # Factor 2: Critical entries (0-30 points)
            critical_count = len(df[df['risk_level'] == 'CRITICAL']) if 'risk_level' in df.columns else 0
            critical_score = min(30, critical_count * 5)
            
            # Factor 3: Analysis count (0-20 points)
            analysis_score = min(20, len(analyses) * 2)
            
            # Factor 4: High risk entries (0-10 points)
            high_risk_count = len(df[df['risk_level'] == 'HIGH']) if 'risk_level' in df.columns else 0
            high_risk_score = min(10, high_risk_count)
            
            total_score = error_ratio_score + critical_score + analysis_score + high_risk_score
            
            # Determine level
            if total_score >= 80:
                level = "critical"
                recommendations = [
                    "🚨 Immediate investigation required",
                    "Review critical errors in priority",
                    "Consider incident response procedures",
                    "Check system resource usage"
                ]
            elif total_score >= 60:
                level = "high"
                recommendations = [
                    "⚠️ Review errors within next hour",
                    "Identify patterns in high-risk entries",
                    "Monitor system performance",
                    "Prepare mitigation strategies"
                ]
            elif total_score >= 40:
                level = "medium"
                recommendations = [
                    "📌 Schedule error review",
                    "Monitor trends",
                    "Consider preventive measures",
                    "Update error handling"
                ]
            else:
                level = "low"
                recommendations = [
                    "✅ System running normally",
                    "Continue regular monitoring",
                    "Maintain current error handling"
                ]
            
            return {
                "score": round(total_score, 2),
                "level": level,
                "recommendations": recommendations,
                "factors": {
                    "error_ratio": round(error_ratio_score, 2),
                    "critical_issues": round(critical_score, 2),
                    "analysis_findings": round(analysis_score, 2),
                    "high_risk_items": round(high_risk_score, 2)
                }
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_risk_timeline(self, logs: List[Dict]) -> List[Dict]:
        """Get risk distribution over time ranges."""
        if not logs:
            return []
        
        try:
            df = pd.DataFrame(logs)
            
            # Group by risk level and get counts
            risk_timeline = []
            for risk_level in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
                count = len(df[df['risk_level'] == risk_level]) if 'risk_level' in df.columns else 0
                risk_timeline.append({
                    "risk_level": risk_level,
                    "count": count,
                    "percentage": round((count / len(logs)) * 100, 2) if logs else 0
                })
            
            return risk_timeline
        except Exception as e:
            return []
