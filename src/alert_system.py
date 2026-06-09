"""Alert system for monitoring and threshold configuration."""
import json
from typing import Dict, List
from datetime import datetime


class AlertSystem:
    """Manages alerts and threshold configurations."""
    
    DEFAULT_THRESHOLDS = {
        "critical_threshold": 10,  # Number of critical errors to trigger alert
        "high_threshold": 25,       # Number of high-risk errors
        "error_rate_threshold": 0.3, # Error ratio (30%)
        "response_time": "immediate"  # How to respond
    }
    
    def __init__(self, config_file: str = "alert_config.json"):
        self.config_file = config_file
        self.thresholds = self._load_config()
    
    def _load_config(self) -> Dict:
        """Load alert configuration from file."""
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return self.DEFAULT_THRESHOLDS.copy()
    
    def save_config(self, config: Dict) -> bool:
        """Save alert configuration."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            self.thresholds = config
            return True
        except Exception:
            return False
    
    def evaluate_alerts(self, logs: List[Dict], analyses: List[Dict]) -> Dict:
        """Evaluate if any alerts should be triggered."""
        alerts = {
            "triggered": [],
            "warnings": [],
            "level": "normal",
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # Check critical errors
            critical_count = len([l for l in logs if l.get('risk_level') == 'CRITICAL'])
            if critical_count >= self.thresholds.get("critical_threshold", 10):
                alerts["triggered"].append({
                    "type": "critical_threshold",
                    "message": f"Critical error threshold exceeded: {critical_count} critical errors found",
                    "severity": "critical",
                    "value": critical_count
                })
                alerts["level"] = "critical"
            
            # Check high-risk errors
            high_count = len([l for l in logs if l.get('risk_level') == 'HIGH'])
            if high_count >= self.thresholds.get("high_threshold", 25):
                alerts["triggered"].append({
                    "type": "high_threshold",
                    "message": f"High-risk error threshold exceeded: {high_count} high-risk errors",
                    "severity": "high",
                    "value": high_count
                })
                if alerts["level"] == "normal":
                    alerts["level"] = "high"
            
            # Check error rate
            if logs:
                error_count = len([l for l in logs if l.get('log_level') in ['ERROR', 'CRITICAL']])
                error_rate = error_count / len(logs)
                threshold = self.thresholds.get("error_rate_threshold", 0.3)
                
                if error_rate >= threshold:
                    alerts["warnings"].append({
                        "type": "high_error_rate",
                        "message": f"Error rate is {error_rate*100:.1f}% (threshold: {threshold*100:.1f}%)",
                        "severity": "medium",
                        "value": round(error_rate * 100, 2)
                    })
                    if alerts["level"] == "normal":
                        alerts["level"] = "warning"
            
            # Check analysis findings
            if len(analyses) > 5:
                alerts["warnings"].append({
                    "type": "many_errors_analyzed",
                    "message": f"{len(analyses)} error analyses completed",
                    "severity": "info",
                    "value": len(analyses)
                })
            
            return alerts
        except Exception as e:
            alerts["warnings"].append({
                "type": "evaluation_error",
                "message": f"Error during alert evaluation: {str(e)}",
                "severity": "info"
            })
            return alerts
    
    def get_alert_recommendations(self, alerts: Dict) -> List[str]:
        """Get action recommendations based on alerts."""
        recommendations = []
        
        if alerts["level"] == "critical":
            recommendations = [
                "🚨 IMMEDIATE ACTION REQUIRED",
                "1. Contact system administrator",
                "2. Review critical error logs in detail",
                "3. Check system resource utilization",
                "4. Verify all critical services are running",
                "5. Prepare rollback plan if necessary",
                "6. Enable enhanced logging for debugging"
            ]
        elif alerts["level"] == "high":
            recommendations = [
                "⚠️ URGENT ATTENTION NEEDED",
                "1. Review high-risk error analysis",
                "2. Identify common patterns",
                "3. Check recent deployments",
                "4. Monitor error trend",
                "5. Prepare mitigation strategies"
            ]
        elif alerts["level"] == "warning":
            recommendations = [
                "⚡ ATTENTION REQUIRED",
                "1. Monitor error rate trends",
                "2. Review recent configuration changes",
                "3. Plan preventive maintenance",
                "4. Consider performance optimization"
            ]
        else:
            recommendations = [
                "✅ System Status: Normal",
                "- Continue regular monitoring",
                "- Maintain current error handling",
                "- Review logs periodically"
            ]
        
        return recommendations
    
    def create_alert_report(self, alerts: Dict, recommendations: List[str]) -> str:
        """Generate an alert report."""
        report = f"""
# Alert Report
Generated: {alerts['timestamp']}
Status: {alerts['level'].upper()}

## Summary
- Alert Level: {alerts['level']}
- Triggered Alerts: {len(alerts['triggered'])}
- Warnings: {len(alerts['warnings'])}

## Triggered Alerts
"""
        for alert in alerts['triggered']:
            report += f"\n- **{alert['type']}**: {alert['message']}\n"
        
        if alerts['warnings']:
            report += "\n## Warnings\n"
            for warning in alerts['warnings']:
                report += f"\n- **{warning['type']}**: {warning['message']}\n"
        
        report += "\n## Recommendations\n"
        for rec in recommendations:
            report += f"{rec}\n"
        
        return report
