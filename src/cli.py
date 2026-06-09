import click
from .agent import AgentEngine

@click.group()
def cli():
    """Log File Anomaly Explainer CLI."""
    pass

@cli.command()
@click.argument('log_path', type=click.Path(exists=True))
@click.option('--output', '-o', default='report.md', help='Path to output the Markdown report.')
@click.option('--model', '-m', default='llama3', help='Ollama model to use.')
def analyze(log_path, output, model):
    """Analyze a log file for anomalies and generate a report."""
    click.echo(f"Analyzing {log_path} using model {model}...")
    
    agent = AgentEngine(model_name=model)
    
    try:
        analyses = agent.run_analysis(log_path)
        agent.generate_markdown_report(analyses, output)
        click.echo(f"Analysis complete. Report saved to {output}")
    except Exception as e:
        click.echo(f"An error occurred during analysis: {e}", err=True)

if __name__ == '__main__':
    cli()
