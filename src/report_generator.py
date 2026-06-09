import json
import os
from datetime import datetime
from typing import List, Dict, Any
from io import BytesIO
import markdown2
from jinja2 import Template
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors

class ReportGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.custom_styles = self._create_custom_styles()
        
    def _create_custom_styles(self):
        """Create custom styles for PDF generation"""
        return {
            'title': ParagraphStyle(
                'CustomTitle',
                parent=self.styles['Heading1'],
                fontSize=24,
                spaceAfter=30,
                textColor=colors.darkblue
            ),
            'heading': ParagraphStyle(
                'CustomHeading',
                parent=self.styles['Heading2'],
                fontSize=16,
                spaceAfter=12,
                textColor=colors.darkred
            ),
            'subheading': ParagraphStyle(
                'CustomSubheading',
                parent=self.styles['Heading3'],
                fontSize=12,
                spaceAfter=8,
                textColor=colors.darkgreen
            )
        }

    def generate_markdown_report(self, file_info: Dict, logs: List[Dict], analyses: List[Dict]) -> str:
        """Generate a Markdown report"""
        template = Template("""
# Log File Analysis Report

## File Information
- **Filename:** {{ file_info.filename }}
- **Upload Date:** {{ file_info.upload_date }}
- **File Size:** {{ file_info.file_size }} bytes
- **Total Lines:** {{ file_info.total_lines }}
- **Error Count:** {{ file_info.error_count }}

## Summary
This report contains the analysis of {{ file_info.total_lines }} log entries from the file "{{ file_info.filename }}".
{% if file_info.error_count > 0 %}{{ file_info.error_count }} critical errors were identified and analyzed.{% else %}No critical errors were found in this log file.{% endif %}

## Risk Level Distribution
{% set risk_counts = {} %}
{% for log in logs %}
{% set _ = risk_counts.update({log.risk_level: risk_counts.get(log.risk_level, 0) + 1}) %}
{% endfor %}
{% for risk, count in risk_counts.items() %}
- **{{ risk }}:** {{ count }} entries
{% endfor %}

## Log Level Distribution
{% set level_counts = {} %}
{% for log in logs %}
{% set _ = level_counts.update({log.log_level: level_counts.get(log.log_level, 0) + 1}) %}
{% endfor %}
{% for level, count in level_counts.items() %}
- **{{ level }}:** {{ count }} entries
{% endfor %}

{% if analyses %}
## Error Analysis

{% for analysis in analyses %}
### Error #{{ loop.index }}
{% if analysis.line_number %}
**Line:** {{ analysis.line_number }}
{% endif %}

**Identified Error:**
{{ analysis.identified_error }}

**Probable Cause:**
{{ analysis.probable_cause }}

**Suggested Fix:**
{{ analysis.suggested_fix }}

---
{% endfor %}
{% endif %}

## High Risk Log Entries
{% set high_risk_logs = logs | selectattr('risk_level', 'in', ['CRITICAL', 'HIGH']) | list %}
{% if high_risk_logs %}
{% for log in high_risk_logs %}
### Line {{ log.line_number }} - {{ log.risk_level }} Risk
**Time:** {{ log.timestamp or 'N/A' }}  
**Level:** {{ log.log_level }}

```
{{ log.content }}
```

{% endfor %}
{% else %}
No high-risk log entries found.
{% endif %}

---
*Report generated on {{ report_date }}*
        """)
        
        return template.render(
            file_info=file_info,
            logs=logs,
            analyses=analyses,
            report_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )

    def generate_html_report(self, file_info: Dict, logs: List[Dict], analyses: List[Dict]) -> str:
        """Generate an HTML report"""
        markdown_content = self.generate_markdown_report(file_info, logs, analyses)
        
        # Convert markdown to HTML
        html_content = markdown2.markdown(markdown_content, extras=['tables', 'fenced-code-blocks'])
        
        # Wrap in HTML template
        html_template = Template("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Log Analysis Report - {{ file_info.filename }}</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            max-width: 900px;
            margin: 0 auto;
            padding: 2rem;
            color: #333;
        }
        h1 { color: #2563eb; border-bottom: 3px solid #2563eb; padding-bottom: 0.5rem; }
        h2 { color: #dc2626; margin-top: 2rem; }
        h3 { color: #059669; }
        code { 
            background: #f3f4f6; 
            padding: 0.25rem 0.5rem; 
            border-radius: 0.25rem;
            font-family: 'Monaco', 'Menlo', monospace;
        }
        pre {
            background: #1f2937;
            color: #f9fafb;
            padding: 1rem;
            border-radius: 0.5rem;
            overflow-x: auto;
        }
        pre code {
            background: none;
            padding: 0;
            color: inherit;
        }
        ul { padding-left: 1.5rem; }
        li { margin: 0.25rem 0; }
        hr { border: none; border-top: 2px solid #e5e7eb; margin: 2rem 0; }
        .report-meta {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 0.5rem;
            padding: 1rem;
            margin-bottom: 2rem;
        }
    </style>
</head>
<body>
    <div class="report-meta">
        <strong>Report Generated:</strong> {{ report_date }}<br>
        <strong>File:</strong> {{ file_info.filename }}
    </div>
    {{ html_content | safe }}
</body>
</html>
        """)
        
        return html_template.render(
            file_info=file_info,
            html_content=html_content,
            report_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )

    def generate_pdf_report(self, file_info: Dict, logs: List[Dict], analyses: List[Dict]) -> bytes:
        """Generate a PDF report"""
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=letter,
            rightMargin=72, 
            leftMargin=72,
            topMargin=72, 
            bottomMargin=18
        )
        
        # Build story
        story = []
        
        # Title
        story.append(Paragraph(f"Log File Analysis Report", self.custom_styles['title']))
        story.append(Spacer(1, 12))
        
        # File Information
        story.append(Paragraph("File Information", self.custom_styles['heading']))
        file_info_data = [
            ['Filename', file_info['filename']],
            ['Upload Date', file_info['upload_date']],
            ['File Size', f"{file_info['file_size']} bytes"],
            ['Total Lines', str(file_info['total_lines'])],
            ['Error Count', str(file_info['error_count'])],
        ]
        
        file_table = Table(file_info_data, colWidths=[2*inch, 4*inch])
        file_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(file_table)
        story.append(Spacer(1, 12))
        
        # Summary
        story.append(Paragraph("Summary", self.custom_styles['heading']))
        summary_text = f"This report contains the analysis of {file_info['total_lines']} log entries from the file \"{file_info['filename']}\"."
        if file_info['error_count'] > 0:
            summary_text += f" {file_info['error_count']} critical errors were identified and analyzed."
        else:
            summary_text += " No critical errors were found in this log file."
        story.append(Paragraph(summary_text, self.styles['Normal']))
        story.append(Spacer(1, 12))
        
        # Risk Level Distribution
        story.append(Paragraph("Risk Level Distribution", self.custom_styles['heading']))
        risk_counts = {}
        for log in logs:
            risk_level = log['risk_level']
            risk_counts[risk_level] = risk_counts.get(risk_level, 0) + 1
        
        risk_data = [['Risk Level', 'Count']]
        for risk, count in risk_counts.items():
            risk_data.append([risk, str(count)])
        
        risk_table = Table(risk_data, colWidths=[2*inch, 1*inch])
        risk_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(risk_table)
        story.append(Spacer(1, 12))
        
        # Error Analysis
        if analyses:
            story.append(Paragraph("Error Analysis", self.custom_styles['heading']))
            for i, analysis in enumerate(analyses, 1):
                story.append(Paragraph(f"Error #{i}", self.custom_styles['subheading']))
                if analysis.get('line_number'):
                    story.append(Paragraph(f"<b>Line:</b> {analysis['line_number']}", self.styles['Normal']))
                story.append(Paragraph(f"<b>Identified Error:</b> {analysis['identified_error']}", self.styles['Normal']))
                story.append(Paragraph(f"<b>Probable Cause:</b> {analysis['probable_cause']}", self.styles['Normal']))
                story.append(Paragraph(f"<b>Suggested Fix:</b> {analysis['suggested_fix']}", self.styles['Normal']))
                story.append(Spacer(1, 12))
        
        # Generate PDF
        doc.build(story)
        pdf_data = buffer.getvalue()
        buffer.close()
        
        return pdf_data

    def generate_json_report(self, file_info: Dict, logs: List[Dict], analyses: List[Dict]) -> str:
        """Generate a JSON report"""
        # Calculate statistics
        risk_counts = {}
        level_counts = {}
        
        for log in logs:
            risk_level = log['risk_level']
            log_level = log['log_level']
            risk_counts[risk_level] = risk_counts.get(risk_level, 0) + 1
            level_counts[log_level] = level_counts.get(log_level, 0) + 1
        
        high_risk_logs = [log for log in logs if log['risk_level'] in ['CRITICAL', 'HIGH']]
        
        report_data = {
            "report_metadata": {
                "generated_at": datetime.now().isoformat(),
                "report_type": "log_analysis",
                "version": "1.0"
            },
            "file_information": file_info,
            "statistics": {
                "total_entries": len(logs),
                "error_count": len(analyses),
                "risk_distribution": risk_counts,
                "level_distribution": level_counts,
                "high_risk_entries": len(high_risk_logs)
            },
            "error_analyses": analyses,
            "high_risk_logs": high_risk_logs[:50],  # Limit to first 50 for size
            "all_logs_summary": {
                "total_count": len(logs),
                "note": "For complete log data, use the logs endpoint"
            }
        }
        
        return json.dumps(report_data, indent=2, default=str)