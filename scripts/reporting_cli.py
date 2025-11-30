#!/usr/bin/env python3
"""
LinkedIn Reporting CLI

Generate reports and visualizations:
- Network visualizations (interactive HTML graphs)
- PDF performance reports (weekly/monthly)

Usage:
  python reporting_cli.py network-graph --output network.html
  python reporting_cli.py pdf-report --weeks 4 --output report.pdf
  python reporting_cli.py network-stats
"""

import sys
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.network_visualizer import NetworkVisualizer
from utils.pdf_report_generator import PDFReportGenerator
import yaml


def cmd_network_graph(args):
    """Generate interactive network visualization"""
    print("\n🔍 Generating Network Visualization...\n")

    viz = NetworkVisualizer()

    # Build graph
    viz.build_network_graph(
        min_quality_score=args.min_quality,
        include_inactive=args.include_inactive,
        max_connections=args.max_connections
    )

    # Create visualization
    output_file = viz.create_interactive_visualization(
        output_file=args.output,
        physics=not args.no_physics
    )

    print(f"\n✅ Network visualization created: {output_file}")
    print(f"\n💡 Open {output_file} in your browser to view the interactive graph!\n")


def cmd_network_stats(args):
    """Display network statistics"""
    print("\n📊 Network Statistics\n")

    viz = NetworkVisualizer()
    viz.build_network_graph()

    stats = viz.get_network_stats()

    print(f"Total Connections: {stats['total_connections']}")
    print(f"Total Companies: {stats['total_companies']}")
    print(f"Average Quality Score: {stats['avg_quality_score']}/10")
    print(f"Target Audience Count: {stats['target_audience_count']}")
    print(f"Network Density: {stats['network_density']}")
    print(f"\nTop 10 Companies:")
    for company, count in stats['top_companies']:
        print(f"  • {company}: {count} connections")

    print(f"\nEngagement Distribution:")
    for level, count in stats['engagement_distribution'].items():
        print(f"  • {level.title()}: {count}")

    print()


def cmd_key_connectors(args):
    """Identify key connectors in network"""
    print("\n🔑 Key Connectors (Betweenness Centrality)\n")

    viz = NetworkVisualizer()
    viz.build_network_graph()

    connectors = viz.get_key_connectors(top_n=args.top)

    for i, connector in enumerate(connectors, 1):
        print(f"{i}. {connector['name']}")
        print(f"   {connector['title']} at {connector['company']}")
        print(f"   Quality: {connector['quality_score']}/10 | Centrality: {connector['centrality']}")
        print(f"   Engagement: {connector['engagement'].title()}\n")


def cmd_pdf_report(args):
    """Generate PDF performance report"""
    print(f"\n📄 Generating {args.weeks}-Week Performance Report...\n")

    generator = PDFReportGenerator()

    output_file = generator.generate_weekly_report(
        output_file=args.output,
        weeks=args.weeks
    )

    print(f"\n✅ PDF report generated: {output_file}\n")


def main():
    parser = argparse.ArgumentParser(
        description='LinkedIn Reporting & Visualization CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Network graph command
    graph_parser = subparsers.add_parser('network-graph', help='Generate interactive network visualization')
    graph_parser.add_argument('--output', type=str, default='network_graph.html', help='Output HTML file')
    graph_parser.add_argument('--min-quality', type=float, default=0.0, help='Minimum quality score')
    graph_parser.add_argument('--include-inactive', action='store_true', help='Include inactive connections')
    graph_parser.add_argument('--max-connections', type=int, help='Maximum connections to include')
    graph_parser.add_argument('--no-physics', action='store_true', help='Disable physics simulation')

    # Network stats command
    stats_parser = subparsers.add_parser('network-stats', help='Display network statistics')

    # Key connectors command
    connectors_parser = subparsers.add_parser('key-connectors', help='Identify key connectors')
    connectors_parser.add_argument('--top', type=int, default=10, help='Number of top connectors')

    # PDF report command
    pdf_parser = subparsers.add_parser('pdf-report', help='Generate PDF performance report')
    pdf_parser.add_argument('--weeks', type=int, default=1, help='Number of weeks to include')
    pdf_parser.add_argument('--output', type=str, help='Output PDF file')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Execute command
    commands = {
        'network-graph': cmd_network_graph,
        'network-stats': cmd_network_stats,
        'key-connectors': cmd_key_connectors,
        'pdf-report': cmd_pdf_report
    }

    if args.command in commands:
        try:
            commands[args.command](args)
        except Exception as e:
            print(f"\n❌ Error: {str(e)}\n")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
