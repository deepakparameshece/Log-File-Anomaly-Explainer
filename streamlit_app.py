import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os
import tempfile
import io
import base64
from typing import Dict, List

# Import our existing modules
from src.agent import AgentEngine
from src.report_generator import ReportGenerator
from src.debug_utils import inspect_database, get_file_data, validate_file_data
from src.analytics import LogAnalytics
from src.pattern_recognition import PatternRecognizer
from src.alert_system import AlertSystem
from src.comparison import FileComparator
from src.batch_processor import BatchProcessor

# Configure page
st.set_page_config(
    page_title="Log Anomaly Explainer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'agent' not in st.session_state:
    st.session_state.agent = AgentEngine(model_name="llama3.2")
    st.session_state.report_generator = ReportGenerator()
    st.session_state.analytics = LogAnalytics()
    st.session_state.pattern_recognizer = PatternRecognizer()
    st.session_state.alert_system = AlertSystem()
    st.session_state.comparator = FileComparator()
    st.session_state.batch_processor = BatchProcessor(st.session_state.agent)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #2563eb, #059669);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .metric-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    
    .risk-critical { color: #ef4444; font-weight: bold; }
    .risk-high { color: #f97316; font-weight: bold; }
    .risk-medium { color: #eab308; font-weight: bold; }
    .risk-low { color: #10b981; font-weight: bold; }
    
    .log-entry {
        background: #f1f5f9;
        border-left: 4px solid #3b82f6;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 5px;
    }
    
    .error-analysis {
        background: #fef2f2;
        border: 1px solid #fecaca;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    .stDownloadButton > button {
        background: linear-gradient(90deg, #2563eb, #059669);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

def main():
    # Header
    st.markdown('<h1 class="main-header">📊 Log Anomaly Explainer</h1>', unsafe_allow_html=True)
    st.markdown("---")

    # Sidebar navigation
    with st.sidebar:
        st.image("https://via.placeholder.com/200x100/2563eb/ffffff?text=Log+Analyzer", width=200)
        
        page = st.selectbox(
            "Navigation",
            ["📤 Upload & Analyze", "📁 View Files", "📊 Dashboard", "🔍 Pattern Analysis", 
             "📈 Advanced Analytics", "🚨 Alerts", "🔄 Compare Files", "⚙️ Batch Process"],
            index=0
        )
        
        st.markdown("---")
        st.markdown("### About")
        st.markdown("Upload log files to get intelligent error analysis using local AI.")
        
        # Show statistics in sidebar
        files = st.session_state.agent.get_uploaded_files()
        st.metric("Total Files Analyzed", len(files))

    # Main content based on navigation
    if page == "📤 Upload & Analyze":
        show_upload_page()
    elif page == "📁 View Files":
        show_files_page()
    elif page == "📊 Dashboard":
        show_dashboard_page()
    elif page == "🔍 Pattern Analysis":
        show_pattern_analysis_page()
    elif page == "📈 Advanced Analytics":
        show_advanced_analytics_page()
    elif page == "🚨 Alerts":
        show_alerts_page()
    elif page == "🔄 Compare Files":
        show_comparison_page()
    elif page == "⚙️ Batch Process":
        show_batch_process_page()

def show_upload_page():
    st.header("Upload Log File")
    st.write("Upload a `.log` file to analyze errors and anomalies using AI.")
    
    uploaded_file = st.file_uploader(
        "Choose a log file",
        type=['log'],
        help="Upload any .log file for analysis"
    )
    
    if uploaded_file is not None:
        # Display file information
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Filename", uploaded_file.name)
        with col2:
            st.metric("Size", f"{uploaded_file.size} bytes")
        with col3:
            file_type = "Log File"
            st.metric("Type", file_type)
        
        # Analyze button
        if st.button("🔍 Analyze Log File", type="primary"):
            with st.spinner("Analyzing log file... This may take a few moments."):
                # Save temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.log') as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_file_path = tmp_file.name
                
                try:
                    # Run analysis
                    result = st.session_state.agent.run_full_analysis(
                        tmp_file_path, 
                        uploaded_file.name, 
                        uploaded_file.size
                    )
                    
                    # Show results
                    st.success("✅ Analysis completed!")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Total Log Entries", result['total_logs'])
                    with col2:
                        st.metric("Analysis Complete", "✅ Ready")
                    
                    if result['error_count'] > 0:
                        st.info(f"Found {result['error_count']} errors that need attention!")
                        
                        # Option to view detailed analysis
                        if st.button("📋 View Detailed Analysis"):
                            st.session_state.selected_file_id = result['file_id']
                            st.session_state.selected_filename = uploaded_file.name
                            st.rerun()
                    else:
                        st.info("No critical errors found in this log file.")
                    
                except Exception as e:
                    st.error(f"Error analyzing file: {str(e)}")
                finally:
                    # Cleanup
                    if os.path.exists(tmp_file_path):
                        os.remove(tmp_file_path)
    
    # Show detailed analysis if file was selected
    if hasattr(st.session_state, 'selected_file_id'):
        st.markdown("---")
        show_detailed_analysis(st.session_state.selected_file_id, st.session_state.selected_filename)

def show_files_page():
    st.header("Uploaded Files")
    st.write("View and analyze previously uploaded log files.")
    
    files = st.session_state.agent.get_uploaded_files()
    
    if not files:
        st.info("No files uploaded yet. Go to the Upload & Analyze page to upload your first log file.")
        return
    
    # Convert to DataFrame for better display
    files_df = pd.DataFrame(files)
    files_df['upload_date'] = pd.to_datetime(files_df['upload_date'])
    files_df = files_df.sort_values('upload_date', ascending=False)
    
    # Display files with actions
    for _, file in files_df.iterrows():
        with st.expander(f"📄 {file['filename']} - {file['upload_date'].strftime('%Y-%m-%d %H:%M')}", expanded=False):
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("File Size", f"{file['file_size']} bytes")
            with col2:
                st.metric("Total Lines", file.get('total_lines', 'N/A'))
            with col3:
                st.metric("Error Count", file.get('error_count', 'N/A'))
            with col4:
                if st.button("📋 View Detailed Analysis", key=f"details_{file['id']}"):
                    st.session_state.selected_file_id = file['id']
                    st.session_state.selected_filename = file['filename']
                    st.rerun()

    # Show detailed analysis for a selected file
    if hasattr(st.session_state, 'selected_file_id'):
        st.markdown("---")
        show_detailed_analysis(st.session_state.selected_file_id, st.session_state.selected_filename)

def show_dashboard_page():
    st.header("Analytics Dashboard")
    st.write("Overview of all analyzed log files and error patterns.")
    
    files = st.session_state.agent.get_uploaded_files()
    
    if not files:
        st.info("No data available. Upload some log files first.")
        return
    
    # Prepare data
    files_df = pd.DataFrame(files)
    files_df['upload_date'] = pd.to_datetime(files_df['upload_date'])
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Files", len(files))
    with col2:
        total_errors = files_df['error_count'].sum() if 'error_count' in files_df else 0
        st.metric("Total Errors", total_errors)
    with col3:
        total_lines = files_df['total_lines'].sum() if 'total_lines' in files_df else 0
        st.metric("Total Log Lines", f"{total_lines:,}")
    with col4:
        avg_errors = files_df['error_count'].mean() if 'error_count' in files_df else 0
        st.metric("Avg Errors/File", f"{avg_errors:.1f}")
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        # Files uploaded over time
        if len(files_df) > 1:
            fig_timeline = px.scatter(
                files_df,
                x='upload_date',
                y='error_count',
                size='total_lines',
                hover_name='filename',
                title="Files Upload Timeline",
                labels={'upload_date': 'Upload Date', 'error_count': 'Errors Found'}
            )
            st.plotly_chart(fig_timeline, use_container_width=True)
        else:
            st.info("Upload more files to see timeline analysis.")
    
    with col2:
        # Error distribution
        if 'error_count' in files_df and files_df['error_count'].sum() > 0:
            error_categories = pd.cut(files_df['error_count'], 
                                    bins=[-1, 0, 5, 15, float('inf')], 
                                    labels=['No Errors', 'Low (1-5)', 'Medium (6-15)', 'High (15+)'])
            error_dist = error_categories.value_counts()
            
            fig_pie = px.pie(
                values=error_dist.values,
                names=error_dist.index,
                title="Error Distribution Across Files"
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("No errors found in uploaded files.")

def show_detailed_analysis(file_id: int, filename: str):
    st.header(f"Detailed Analysis: {filename}")
    
    # Add a back button to clear selection
    if st.button("← Back to Files"):
        st.session_state.pop('selected_file_id', None)
        st.session_state.pop('selected_filename', None)
        st.rerun()
    
    st.markdown("---")
    
    try:
        # Get data
        logs = st.session_state.agent.get_file_logs(file_id)
        analyses = st.session_state.agent.get_file_analyses(file_id)
        
        # Debug info
        with st.expander("ℹ️ Debug Info"):
            st.write(f"**File ID:** {file_id}")
            st.write(f"**Total Logs Retrieved:** {len(logs) if logs else 0}")
            st.write(f"**Total Analyses Retrieved:** {len(analyses) if analyses else 0}")
            
            # Database validation
            st.subheader("Database Validation")
            validation = validate_file_data(file_id)
            if validation["valid"]:
                st.success("✅ Database validation passed")
            else:
                st.error("❌ Database issues found")
                for issue in validation["issues"]:
                    st.error(f"- {issue}")
            
            for warning in validation["warnings"]:
                st.warning(f"- {warning}")
            
            if "stats" in validation:
                st.json(validation["stats"])
            
            # Show sample raw data
            st.subheader("Sample Raw Data")
            raw_data = get_file_data(file_id)
            if "error" not in raw_data:
                st.write("**File Info:**")
                st.json(raw_data.get("file_info", {}))
                
                if raw_data.get("sample_logs"):
                    st.write(f"**Sample Logs (showing {len(raw_data['sample_logs'])})**")
                    st.json(raw_data["sample_logs"][:3])
                
                if raw_data.get("sample_analyses"):
                    st.write(f"**Sample Analyses (showing {len(raw_data['sample_analyses'])})**")
                    st.json(raw_data["sample_analyses"][:3])
            else:
                st.error(f"Error retrieving data: {raw_data.get('error')}")
        
        if not logs and not analyses:
            st.warning("⚠️ No data found for this file. The analysis may still be in progress or the file may not have been processed successfully.")
            return
        
        # Tabs for different views
        tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "📝 Log Entries", "🚨 Error Analysis", "📥 Export Reports"])
        
        with tab1:
            show_analysis_overview(logs, analyses)
        
        with tab2:
            show_log_entries(logs)
        
        with tab3:
            show_error_analysis(analyses)
        
        with tab4:
            show_export_options(file_id, filename, logs, analyses)
            
    except Exception as e:
        st.error(f"Error loading analysis: {str(e)}")
        import traceback
        st.error(traceback.format_exc())


def show_analysis_overview(logs: List[Dict], analyses: List[Dict]):
    st.subheader("Analysis Overview")
    
    if not logs:
        st.warning("No log data available.")
        return
    
    # Convert to DataFrame
    try:
        logs_df = pd.DataFrame(logs)
    except Exception as e:
        st.error(f"Error processing log data: {str(e)}")
        return
    
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Entries", len(logs))
    with col2:
        st.metric("Error Analyses", len(analyses) if analyses else 0)
    with col3:
        critical_count = len([l for l in logs if l.get('risk_level') == 'CRITICAL'])
        st.metric("Critical Issues", critical_count)
    with col4:
        high_count = len([l for l in logs if l.get('risk_level') == 'HIGH'])
        st.metric("High Risk Issues", high_count)
    
    # Risk level distribution
    col1, col2 = st.columns(2)
    
    with col1:
        if 'risk_level' in logs_df.columns:
            risk_counts = logs_df['risk_level'].value_counts()
            if len(risk_counts) > 0:
                fig_risk = px.pie(
                    values=risk_counts.values,
                    names=risk_counts.index,
                    title="Risk Level Distribution",
                    color_discrete_map={
                        'CRITICAL': '#ef4444',
                        'HIGH': '#f97316',
                        'MEDIUM': '#eab308',
                        'LOW': '#10b981'
                    }
                )
                st.plotly_chart(fig_risk, use_container_width=True)
            else:
                st.info("No risk level data available")
        else:
            st.warning("Risk level column not found in logs")
    
    with col2:
        if 'log_level' in logs_df.columns:
            level_counts = logs_df['log_level'].value_counts()
            if len(level_counts) > 0:
                fig_level = px.bar(
                    x=level_counts.index,
                    y=level_counts.values,
                    title="Log Level Distribution",
                    labels={'x': 'Log Level', 'y': 'Count'}
                )
                st.plotly_chart(fig_level, use_container_width=True)
            else:
                st.info("No log level data available")
        else:
            st.warning("Log level column not found in logs")


def show_log_entries(logs: List[Dict]):
    st.subheader("Log Entries")
    
    if not logs:
        st.warning("No log entries found.")
        return
    
    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        risk_filter = st.selectbox(
            "Filter by Risk Level",
            ["All", "CRITICAL", "HIGH", "MEDIUM", "LOW"],
            key="risk_filter_select"
        )
    with col2:
        level_filter = st.selectbox(
            "Filter by Log Level",
            ["All", "ERROR", "WARN", "INFO", "DEBUG"],
            key="level_filter_select"
        )
    with col3:
        show_count = st.slider("Show entries", 10, min(len(logs), 500), 50, key="log_count_slider")
    
    # Apply filters
    filtered_logs = logs
    if risk_filter != "All":
        filtered_logs = [l for l in filtered_logs if l.get('risk_level') == risk_filter]
    if level_filter != "All":
        filtered_logs = [l for l in filtered_logs if l.get('log_level') == level_filter]
    
    # Display logs
    st.info(f"Showing {min(len(filtered_logs), show_count)} of {len(filtered_logs)} entries")
    
    if not filtered_logs:
        st.warning("No log entries match the selected filters.")
        return
    
    for i, log in enumerate(filtered_logs[:show_count]):
        risk_level = log.get('risk_level', 'LOW')
        risk_class = f"risk-{risk_level.lower()}"
        
        with st.container():
            col1, col2, col3 = st.columns([1, 2, 1])
            with col1:
                st.markdown(f"**Line {log.get('line_number', 'N/A')}**")
            with col2:
                st.markdown(f"**{log.get('log_level', 'UNKNOWN')}**")
            with col3:
                st.markdown(f'<span class="{risk_class}">{risk_level}</span>', 
                           unsafe_allow_html=True)
            
            # Log content
            log_content = log.get('content', '')
            if log_content:
                st.code(log_content, language=None)
            else:
                st.warning("No content available for this log entry.")
            
            if log.get('timestamp'):
                st.caption(f"Timestamp: {log['timestamp']}")
        
        st.markdown("---")


def show_error_analysis(analyses: List[Dict]):
    st.subheader("Error Analysis")
    
    if not analyses:
        st.info("No error analyses available. This usually means no critical errors were found.")
        return
    
    for i, analysis in enumerate(analyses, 1):
        with st.expander(f"🚨 Error Analysis #{i}", expanded=True):
            if analysis.get('line_number'):
                st.markdown(f"**📍 Line:** {analysis['line_number']}")
            
            st.markdown("**🔍 Identified Error:**")
            st.write(analysis.get('identified_error', 'N/A'))
            
            st.markdown("**💡 Probable Cause:**")
            st.write(analysis.get('probable_cause', 'N/A'))
            
            st.markdown("**🛠️ Suggested Fix:**")
            st.write(analysis.get('suggested_fix', 'N/A'))
            
            if analysis.get('analysis_date'):
                st.caption(f"Analyzed on: {analysis['analysis_date']}")

def show_export_options(file_id: int, filename: str, logs: List[Dict], analyses: List[Dict]):
    st.subheader("Export Reports")
    st.write("Download comprehensive analysis reports in various formats.")
    
    # Get file info
    files = st.session_state.agent.get_uploaded_files()
    file_info = next((f for f in files if f['id'] == file_id), None)
    
    if not file_info:
        st.error("File information not found.")
        return
    
    # Export options
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📄 PDF Report")
        st.write("Professional formatted report with charts and tables")
        if st.button("Download PDF", key="pdf_download"):
            try:
                pdf_data = st.session_state.report_generator.generate_pdf_report(file_info, logs, analyses)
                st.download_button(
                    label="📥 Download PDF",
                    data=pdf_data,
                    file_name=f"{os.path.splitext(filename)[0]}_analysis.pdf",
                    mime="application/pdf"
                )
            except Exception as e:
                st.error(f"Error generating PDF: {e}")
        
        st.markdown("### 📋 JSON Data")
        st.write("Structured data format for programmatic use")
        if st.button("Download JSON", key="json_download"):
            try:
                json_data = st.session_state.report_generator.generate_json_report(file_info, logs, analyses)
                st.download_button(
                    label="📥 Download JSON",
                    data=json_data,
                    file_name=f"{os.path.splitext(filename)[0]}_analysis.json",
                    mime="application/json"
                )
            except Exception as e:
                st.error(f"Error generating JSON: {e}")
    
    with col2:
        st.markdown("### 🌐 HTML Report")
        st.write("Styled HTML page that can be opened in any browser")
        if st.button("Download HTML", key="html_download"):
            try:
                html_data = st.session_state.report_generator.generate_html_report(file_info, logs, analyses)
                st.download_button(
                    label="📥 Download HTML",
                    data=html_data,
                    file_name=f"{os.path.splitext(filename)[0]}_analysis.html",
                    mime="text/html"
                )
            except Exception as e:
                st.error(f"Error generating HTML: {e}")
        
        st.markdown("### 📝 Markdown")
        st.write("Plain text format with markdown formatting")
        if st.button("Download Markdown", key="md_download"):
            try:
                md_data = st.session_state.report_generator.generate_markdown_report(file_info, logs, analyses)
                st.download_button(
                    label="📥 Download Markdown",
                    data=md_data,
                    file_name=f"{os.path.splitext(filename)[0]}_analysis.md",
                    mime="text/markdown"
                )
            except Exception as e:
                st.error(f"Error generating Markdown: {e}")

def show_pattern_analysis_page():
    st.header("🔍 Error Pattern Analysis")
    st.write("Identify common error patterns and group related errors.")
    
    files = st.session_state.agent.get_uploaded_files()
    if not files:
        st.info("No files analyzed yet. Upload some log files first.")
        return
    
    options = [f"{f['filename']} (id={f['id']})" for f in files]
    selected_option = st.selectbox("Select a file to analyze patterns", options)
    selected_file_id = int(selected_option.split("(id=")[-1].strip(")"))
    file_obj = next((f for f in files if f['id'] == selected_file_id), None)
    
    if file_obj:
        analyses = st.session_state.agent.get_file_analyses(file_obj['id'])
        logs = st.session_state.agent.get_file_logs(file_obj['id'])
        
        if not analyses:
            st.warning("No error analyses available for this file.")
            return
        
        tab1, tab2, tab3, tab4 = st.tabs(["📊 Patterns", "🏷️ Categories", "🔗 Error Chains", "📋 Summary"])
        
        with tab1:
            st.subheader("Error Patterns")
            patterns = st.session_state.pattern_recognizer.extract_error_patterns(analyses)
            
            if patterns:
                for i, pattern in enumerate(patterns[:10], 1):
                    with st.expander(f"Pattern {i}: {pattern['pattern']} ({pattern['count']} occurrences)"):
                        st.metric("Frequency", pattern['count'])
                        
                        if pattern['probable_causes']:
                            st.write("**Probable Causes:**")
                            for cause in pattern['probable_causes'][:3]:
                                st.write(f"- {cause}")
                        
                        if pattern['suggested_fixes']:
                            st.write("**Suggested Fixes:**")
                            for fix in pattern['suggested_fixes'][:3]:
                                st.write(f"- {fix}")
            else:
                st.info("No patterns identified.")
        
        with tab2:
            st.subheader("Error Categories")
            categories = st.session_state.pattern_recognizer.categorize_errors(analyses)
            
            col1, col2 = st.columns(2)
            with col1:
                if categories:
                    fig = px.bar(
                        x=list(categories.keys()),
                        y=[len(v) for v in categories.values()],
                        title="Errors by Category",
                        labels={"x": "Category", "y": "Count"}
                    )
                    st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.write("**Error Count by Category**")
                for category, errors in categories.items():
                    st.write(f"- **{category}**: {len(errors)} errors")
        
        with tab3:
            st.subheader("Error Chains")
            chains = st.session_state.pattern_recognizer.get_error_chain(analyses)
            
            if chains:
                st.info(f"Found {len(chains)} error chains")
                for i, chain in enumerate(chains[:5], 1):
                    with st.expander(f"Chain {i} ({len(chain)} related errors)"):
                        for j, error in enumerate(chain, 1):
                            st.write(f"{j}. {error.get('identified_error', 'Unknown')}")
            else:
                st.info("No error chains identified.")
        
        with tab4:
            st.subheader("Pattern Summary")
            freq = st.session_state.pattern_recognizer.get_error_frequency(analyses)
            
            summary_text = "### Top Error Types\n"
            for error, count in list(freq.items())[:10]:
                summary_text += f"- **{error}**: {count} occurrences\n"
            
            st.markdown(summary_text)

def show_advanced_analytics_page():
    st.header("📈 Advanced Analytics")
    st.write("Deep dive analytics and statistical insights.")
    
    files = st.session_state.agent.get_uploaded_files()
    if not files:
        st.info("No files analyzed yet. Upload some log files first.")
        return
    
    options = [f"{f['filename']} (id={f['id']})" for f in files]
    selected_option = st.selectbox("Select a file for analytics", options, key="analytics_select")
    selected_file_id = int(selected_option.split("(id=")[-1].strip(")"))
    file_obj = next((f for f in files if f['id'] == selected_file_id), None)
    
    if file_obj:
        logs = st.session_state.agent.get_file_logs(file_obj['id'])
        analyses = st.session_state.agent.get_file_analyses(file_obj['id'])
        
        tab1, tab2, tab3 = st.tabs(["📊 Statistics", "⚠️ Severity Score", "📉 Trends"])
        
        with tab1:
            st.subheader("Log Statistics")
            stats = st.session_state.analytics.get_log_statistics(logs)
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Entries", stats.get('total_entries', 0))
            with col2:
                st.metric("Unique Log Levels", stats.get('unique_log_levels', 0))
            with col3:
                st.metric("Unique Risk Levels", stats.get('unique_risk_levels', 0))
            with col4:
                st.metric("Analyses", len(analyses))
            
            col1, col2 = st.columns(2)
            with col1:
                if stats.get('log_level_distribution'):
                    fig = px.pie(
                        values=list(stats['log_level_distribution'].values()),
                        names=list(stats['log_level_distribution'].keys()),
                        title="Log Level Distribution"
                    )
                    st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                if stats.get('risk_level_distribution'):
                    fig = px.pie(
                        values=list(stats['risk_level_distribution'].values()),
                        names=list(stats['risk_level_distribution'].keys()),
                        title="Risk Level Distribution"
                    )
                    st.plotly_chart(fig, use_container_width=True)
        
        with tab2:
            st.subheader("Severity Assessment")
            severity = st.session_state.analytics.calculate_severity_score(logs, analyses)
            
            if 'error' not in severity:
                # Display severity score
                col1, col2, col3 = st.columns([1, 1, 2])
                with col1:
                    st.metric("Severity Score", severity['score'], delta=None)
                with col2:
                    level = severity['level']
                    color = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(level, "⚪")
                    st.metric("Level", f"{color} {level.upper()}")
                with col3:
                    pass
                
                # Display factors
                st.write("**Scoring Factors:**")
                factors = severity.get('factors', {})
                fig = px.bar(
                    x=list(factors.keys()),
                    y=list(factors.values()),
                    title="Severity Score Breakdown",
                    labels={"x": "Factor", "y": "Points"}
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Display recommendations
                st.write("**Recommendations:**")
                for rec in severity.get('recommendations', []):
                    st.write(rec)
        
        with tab3:
            st.subheader("Error Trends")
            trends = st.session_state.analytics.calculate_error_trends(logs)
            
            if 'error' not in trends:
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Errors", trends.get('total_errors', 0))
                with col2:
                    st.metric("Unique Error Types", trends.get('unique_error_types', 0))
                with col3:
                    st.metric("Severity", trends.get('severity', 'Unknown').upper())
                
                timeline = st.session_state.analytics.get_risk_timeline(logs)
                if timeline:
                    fig = px.bar(
                        x=[t['risk_level'] for t in timeline],
                        y=[t['count'] for t in timeline],
                        title="Risk Timeline",
                        labels={"x": "Risk Level", "y": "Count"}
                    )
                    st.plotly_chart(fig, use_container_width=True)

def show_alerts_page():
    st.header("🚨 Alert System")
    st.write("Configure alert thresholds and view current alerts.")
    
    tab1, tab2 = st.tabs(["⚙️ Configuration", "🔔 Current Alerts"])
    
    with tab1:
        st.subheader("Alert Thresholds")
        
        col1, col2 = st.columns(2)
        with col1:
            critical = st.number_input("Critical Threshold", value=st.session_state.alert_system.thresholds.get("critical_threshold", 10), min_value=1)
            high = st.number_input("High Threshold", value=st.session_state.alert_system.thresholds.get("high_threshold", 25), min_value=1)
        
        with col2:
            error_rate = st.slider("Error Rate Threshold (%)", value=int(st.session_state.alert_system.thresholds.get("error_rate_threshold", 0.3) * 100), min_value=1, max_value=100)
        
        if st.button("Save Configuration"):
            config = {
                "critical_threshold": critical,
                "high_threshold": high,
                "error_rate_threshold": error_rate / 100
            }
            if st.session_state.alert_system.save_config(config):
                st.success("✅ Configuration saved!")
            else:
                st.error("Failed to save configuration")
    
    with tab2:
        st.subheader("Active Alerts")
        
        files = st.session_state.agent.get_uploaded_files()
        if files:
            options = [f"{f['filename']} (id={f['id']})" for f in files]
            selected_option = st.selectbox("Select file to check alerts", options, key="alert_file_select")
            selected_file_id = int(selected_option.split("(id=")[-1].strip(")"))
            file_obj = next((f for f in files if f['id'] == selected_file_id), None)
            
            if file_obj:
                logs = st.session_state.agent.get_file_logs(file_obj['id'])
                analyses = st.session_state.agent.get_file_analyses(file_obj['id'])
                
                alerts = st.session_state.alert_system.evaluate_alerts(logs, analyses)
                recommendations = st.session_state.alert_system.get_alert_recommendations(alerts)
                
                # Display alert level
                level_colors = {"critical": "🔴", "high": "🟠", "warning": "🟡", "normal": "🟢"}
                st.write(f"### {level_colors.get(alerts['level'], '⚪')} Alert Level: {alerts['level'].upper()}")
                
                if alerts['triggered']:
                    st.warning("**Triggered Alerts:**")
                    for alert in alerts['triggered']:
                        col1, col2 = st.columns([1, 3])
                        with col1:
                            st.write(f"🔴 {alert['severity'].upper()}")
                        with col2:
                            st.write(alert['message'])
                
                if alerts['warnings']:
                    st.info("**Warnings:**")
                    for warning in alerts['warnings']:
                        st.write(f"- {warning['message']}")
                
                st.subheader("Recommendations")
                for rec in recommendations:
                    st.write(rec)

def show_comparison_page():
    st.header("🔄 Compare Files")
    st.write("Compare multiple log files to identify similarities and differences.")
    
    files = st.session_state.agent.get_uploaded_files()
    if len(files) < 2:
        st.warning("At least 2 files are needed for comparison. Upload more files first.")
        return
    
    options = [f"{f['filename']} (id={f['id']})" for f in files]
    selected_files = st.multiselect("Select files to compare", options, max_selections=5)
    
    if len(selected_files) >= 2 and st.button("Compare Selected Files"):
        files_data = []
        for selected_option in selected_files:
            file_id = int(selected_option.split("(id=")[-1].strip(")"))
            file_obj = next((f for f in files if f['id'] == file_id), None)
            if file_obj:
                logs = st.session_state.agent.get_file_logs(file_obj['id'])
                analyses = st.session_state.agent.get_file_analyses(file_obj['id'])
                files_data.append({
                    "file_info": file_obj,
                    "logs": logs,
                    "analyses": analyses
                })
        
        comparison = st.session_state.comparator.compare_files(files_data)
        
        if 'error' not in comparison:
            tab1, tab2, tab3 = st.tabs(["📊 Metrics", "🔗 Common Errors", "🎯 Unique Errors"])
            
            with tab1:
                st.subheader("Comparison Metrics")
                metrics_df = pd.DataFrame(comparison['metrics'])
                st.dataframe(metrics_df, use_container_width=True)
                
                if comparison['trend']:
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Total Errors", comparison['trend'].get('total_errors', 0))
                    with col2:
                        st.metric("Average/File", comparison['trend'].get('average_errors_per_file', 0))
                    with col3:
                        st.metric("Trend", comparison['trend'].get('trend_direction', 'N/A'))
                    with col4:
                        st.metric("Avg Error Rate", f"{comparison['trend'].get('average_error_rate', 0)}%")
            
            with tab2:
                st.subheader(f"Common Errors ({len(comparison['common_errors'])})")
                if comparison['common_errors']:
                    for i, error in enumerate(comparison['common_errors'], 1):
                        st.write(f"{i}. {error['error_signature']}")
                else:
                    st.info("No common errors found across selected files.")
            
            with tab3:
                st.subheader("Unique Errors by File")
                if comparison['unique_errors']:
                    for filename, errors in comparison['unique_errors'].items():
                        with st.expander(f"{filename} ({len(errors)} unique)"):
                            for error in errors:
                                st.write(f"- {error}")
                else:
                    st.info("No unique errors identified.")

def show_batch_process_page():
    st.header("⚙️ Batch Process")
    st.write("Process multiple log files at once.")
    
    st.info("Upload one or more log files to process them in batch.")
    
    uploaded_files = st.file_uploader(
        "Choose log files",
        type=['log'],
        accept_multiple_files=True,
        help="Upload multiple .log files at once"
    )
    
    if uploaded_files:
        st.write(f"**Files selected:** {len(uploaded_files)}")
        
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("🚀 Start Batch Processing"):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Save files temporarily
                temp_files = []
                for file in uploaded_files:
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.log') as tmp:
                        tmp.write(file.getvalue())
                        temp_files.append(tmp.name)
                
                try:
                    def progress_callback(msg):
                        status_text.write(f"**Status:** {msg}")
                    
                    results = st.session_state.batch_processor.process_batch(temp_files, progress_callback)
                    
                    progress_bar.progress(100)
                    
                    # Display results
                    st.success("✅ Batch processing complete!")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Processed", results['successful'])
                    with col2:
                        st.metric("Failed", results['failed'])
                    with col3:
                        success_rate = round((results['successful'] / results['total_files'] * 100), 2) if results['total_files'] > 0 else 0
                        st.metric("Success Rate", f"{success_rate}%")
                    
                    # Detailed results
                    tab1, tab2 = st.tabs(["✅ Successful", "❌ Failed"])
                    
                    with tab1:
                        if results['processed_files']:
                            for file_result in results['processed_files']:
                                with st.expander(f"📄 {file_result['filename']}"):
                                    st.write(f"- **File ID:** {file_result['file_id']}")
                                    st.write(f"- **Total Entries:** {file_result['total_logs']}")
                                    st.write(f"- **Errors Found:** {file_result['error_count']}")
                    
                    with tab2:
                        if results['failed_details']:
                            for failed in results['failed_details']:
                                st.error(f"❌ {failed['file']}: {failed['error']}")
                        else:
                            st.info("No failures!")
                    
                    # Download report
                    report = st.session_state.batch_processor.get_batch_report(results)
                    st.download_button(
                        label="📥 Download Batch Report",
                        data=report,
                        file_name="batch_processing_report.md",
                        mime="text/markdown"
                    )
                
                finally:
                    # Cleanup
                    for temp_file in temp_files:
                        if os.path.exists(temp_file):
                            os.remove(temp_file)

if __name__ == "__main__":
    main()
