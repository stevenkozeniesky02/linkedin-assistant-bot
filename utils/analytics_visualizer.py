"""Analytics Visualization for Terminal

Provides rich terminal-based visualizations for analytics data:
- Performance charts
- Trend graphs
- Comparison tables
- Insight displays
"""

from typing import Dict, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text
from rich import box


class AnalyticsVisualizer:
    """Terminal-based analytics visualizations using Rich"""

    def __init__(self):
        self.console = Console()

    def display_complete_dashboard(self, dashboard_data: Dict, insights: List[str] = None):
        """Display the complete analytics dashboard

        Args:
            dashboard_data: Complete dashboard data from AnalyticsEngine
            insights: Optional AI-generated insights
        """
        self.console.clear()
        self.console.print("\n")
        self.console.print("[bold cyan]LinkedIn Analytics Dashboard[/bold cyan]", justify="center")
        self.console.print("=" * 80, style="cyan")
        self.console.print("\n")

        # Display each section
        self._display_engagement_rates(dashboard_data.get("engagement_rates", {}))
        self.console.print("\n")

        self._display_optimal_times(dashboard_data.get("optimal_times", {}))
        self.console.print("\n")

        self._display_content_performance(dashboard_data.get("content_performance", {}))
        self.console.print("\n")

        self._display_performance_trends(dashboard_data.get("performance_trends", {}))
        self.console.print("\n")

        self._display_comment_activity(dashboard_data.get("comment_activity", {}))
        self.console.print("\n")

        if insights:
            self._display_insights(insights)
            self.console.print("\n")

    def _display_engagement_rates(self, data: Dict):
        """Display engagement rate metrics"""
        if data.get("status") != "success":
            self.console.print("[yellow]Insufficient data for engagement analysis[/yellow]")
            return

        rates = data.get("engagement_rates", {})
        overall = rates.get("overall_rate", 0)
        benchmarks = data.get("benchmarks", {})
        status = benchmarks.get("your_status", "unknown")

        # Status color mapping
        status_colors = {
            "excellent": "green",
            "good": "blue",
            "average": "yellow",
            "needs_improvement": "red"
        }
        status_color = status_colors.get(status, "white")

        # Create engagement overview panel
        overview = Table(box=box.ROUNDED, show_header=False, padding=(0, 2))
        overview.add_column(style="cyan", width=30)
        overview.add_column(style="white", width=15)

        overview.add_row("Overall Engagement Rate", f"[bold {status_color}]{overall}%[/bold {status_color}]")
        overview.add_row("Status", f"[bold {status_color}]{status.upper()}[/bold {status_color}]")
        overview.add_row("", "")
        overview.add_row("Like Rate", f"{rates.get('like_rate', 0)}%")
        overview.add_row("Comment Rate", f"{rates.get('comment_rate', 0)}%")
        overview.add_row("Share Rate", f"{rates.get('share_rate', 0)}%")
        overview.add_row("Profile Click Rate", f"{rates.get('profile_click_rate', 0)}%")

        self.console.print(Panel(
            overview,
            title="[bold]Engagement Metrics[/bold]",
            border_style="cyan"
        ))

        # Display benchmark reference
        benchmark_table = Table(box=box.SIMPLE, show_header=True)
        benchmark_table.add_column("Status", style="bold")
        benchmark_table.add_column("Range", style="white")

        benchmark_table.add_row("[green]Excellent[/green]", "Above 5%")
        benchmark_table.add_row("[blue]Good[/blue]", "3-5%")
        benchmark_table.add_row("[yellow]Average[/yellow]", "1-3%")
        benchmark_table.add_row("[red]Needs Improvement[/red]", "Below 1%")

        self.console.print("\n[dim]Benchmark Reference:[/dim]")
        self.console.print(benchmark_table)

    def _display_optimal_times(self, data: Dict):
        """Display optimal posting times"""
        if data.get("status") != "success":
            self.console.print("[yellow]Insufficient data for posting time analysis[/yellow]")
            return

        best_hours = data.get("best_hours", [])
        best_days = data.get("best_days", [])

        # Create two-column layout
        times_table = Table(box=box.ROUNDED, show_header=True)
        times_table.add_column("Best Hours", style="cyan", width=20)
        times_table.add_column("Avg Engagement", justify="right", style="green", width=15)
        times_table.add_column("Posts", justify="right", style="dim", width=10)

        for hour_data in best_hours[:5]:
            times_table.add_row(
                hour_data["hour"],
                f"{hour_data['avg_engagement']:.1f}",
                str(hour_data["post_count"])
            )

        days_table = Table(box=box.ROUNDED, show_header=True)
        days_table.add_column("Best Days", style="cyan", width=20)
        days_table.add_column("Avg Engagement", justify="right", style="green", width=15)
        days_table.add_column("Posts", justify="right", style="dim", width=10)

        for day_data in best_days[:5]:
            days_table.add_row(
                day_data["day"],
                f"{day_data['avg_engagement']:.1f}",
                str(day_data["post_count"])
            )

        self.console.print(Panel(
            times_table,
            title="[bold]Optimal Posting Times[/bold]",
            border_style="cyan"
        ))

        self.console.print("\n")

        self.console.print(Panel(
            days_table,
            title="[bold]Optimal Posting Days[/bold]",
            border_style="cyan"
        ))

    def _display_content_performance(self, data: Dict):
        """Display content performance breakdown"""
        if data.get("status") != "success":
            self.console.print("[yellow]Insufficient data for content analysis[/yellow]")
            return

        top_performers = data.get("top_performers", {})

        # Top performers summary
        summary_table = Table(box=box.ROUNDED, show_header=True)
        summary_table.add_column("Category", style="cyan", width=20)
        summary_table.add_column("Best Performer", style="white", width=20)
        summary_table.add_column("Avg Engagement", justify="right", style="green", width=15)

        best_tone = top_performers.get("best_tone")
        if best_tone:
            summary_table.add_row(
                "Tone",
                best_tone["tone"],
                f"{best_tone['stats']['avg_engagement']:.1f}"
            )

        best_length = top_performers.get("best_length")
        if best_length:
            summary_table.add_row(
                "Length",
                best_length["length"],
                f"{best_length['stats']['avg_engagement']:.1f}"
            )

        self.console.print(Panel(
            summary_table,
            title="[bold]Top Performing Content Attributes[/bold]",
            border_style="cyan"
        ))

        # Top topics
        top_topics = top_performers.get("top_topics", [])
        if top_topics:
            self.console.print("\n")
            topics_table = Table(box=box.ROUNDED, show_header=True)
            topics_table.add_column("Rank", justify="center", style="dim", width=6)
            topics_table.add_column("Topic", style="white", width=40)
            topics_table.add_column("Avg Engagement", justify="right", style="green", width=15)
            topics_table.add_column("Posts", justify="right", style="dim", width=8)

            for i, topic_data in enumerate(top_topics[:5], 1):
                topics_table.add_row(
                    f"#{i}",
                    topic_data["topic"][:40],
                    f"{topic_data['stats']['avg_engagement']:.1f}",
                    str(topic_data['stats']['post_count'])
                )

            self.console.print(Panel(
                topics_table,
                title="[bold]Top Performing Topics[/bold]",
                border_style="cyan"
            ))

        # Performance by tone
        by_tone = data.get("by_tone", {})
        if by_tone:
            self.console.print("\n")
            tone_table = Table(box=box.ROUNDED, show_header=True)
            tone_table.add_column("Tone", style="cyan", width=20)
            tone_table.add_column("Avg Views", justify="right", style="blue", width=12)
            tone_table.add_column("Avg Engagement", justify="right", style="green", width=15)
            tone_table.add_column("Engagement Rate", justify="right", style="yellow", width=15)
            tone_table.add_column("Posts", justify="right", style="dim", width=8)

            sorted_tones = sorted(by_tone.items(), key=lambda x: x[1]["avg_engagement"], reverse=True)
            for tone, stats in sorted_tones:
                tone_table.add_row(
                    tone,
                    f"{stats['avg_views']:.0f}",
                    f"{stats['avg_engagement']:.1f}",
                    f"{stats['engagement_rate']:.1f}%",
                    str(stats['post_count'])
                )

            self.console.print(Panel(
                tone_table,
                title="[bold]Performance by Tone[/bold]",
                border_style="cyan"
            ))

        # Performance by length
        by_length = data.get("by_length", {})
        if by_length:
            self.console.print("\n")
            length_table = Table(box=box.ROUNDED, show_header=True)
            length_table.add_column("Length", style="cyan", width=20)
            length_table.add_column("Avg Views", justify="right", style="blue", width=12)
            length_table.add_column("Avg Engagement", justify="right", style="green", width=15)
            length_table.add_column("Engagement Rate", justify="right", style="yellow", width=15)
            length_table.add_column("Posts", justify="right", style="dim", width=8)

            sorted_lengths = sorted(by_length.items(), key=lambda x: x[1]["avg_engagement"], reverse=True)
            for length, stats in sorted_lengths:
                length_table.add_row(
                    length,
                    f"{stats['avg_views']:.0f}",
                    f"{stats['avg_engagement']:.1f}",
                    f"{stats['engagement_rate']:.1f}%",
                    str(stats['post_count'])
                )

            self.console.print(Panel(
                length_table,
                title="[bold]Performance by Length[/bold]",
                border_style="cyan"
            ))

    def _display_performance_trends(self, data: Dict):
        """Display performance trends over time"""
        if data.get("status") != "success":
            self.console.print("[yellow]Insufficient data for trend analysis[/yellow]")
            return

        trends = data.get("weekly_trends", [])
        overall_trend = data.get("overall_trend", "unknown")

        # Trend direction indicator
        trend_colors = {
            "improving": "green",
            "declining": "red",
            "stable": "yellow",
            "insufficient_data": "dim"
        }
        trend_symbols = {
            "improving": "↗",
            "declining": "↘",
            "stable": "→",
            "insufficient_data": "-"
        }

        trend_color = trend_colors.get(overall_trend, "white")
        trend_symbol = trend_symbols.get(overall_trend, "-")

        header_text = f"[bold]Performance Trends[/bold] [{trend_color}]{trend_symbol} {overall_trend.upper()}[/{trend_color}]"

        # Weekly trends table
        trends_table = Table(box=box.ROUNDED, show_header=True)
        trends_table.add_column("Week Starting", style="cyan", width=15)
        trends_table.add_column("Posts", justify="right", style="dim", width=8)
        trends_table.add_column("Avg Views", justify="right", style="blue", width=12)
        trends_table.add_column("Avg Engagement", justify="right", style="green", width=15)
        trends_table.add_column("Change", justify="right", style="yellow", width=10)

        for trend in trends[-8:]:  # Show last 8 weeks
            change_str = ""
            if "engagement_change_pct" in trend:
                change_pct = trend["engagement_change_pct"]
                if change_pct > 0:
                    change_str = f"[green]+{change_pct:.1f}%[/green]"
                elif change_pct < 0:
                    change_str = f"[red]{change_pct:.1f}%[/red]"
                else:
                    change_str = "[dim]0.0%[/dim]"
            else:
                change_str = "[dim]-[/dim]"

            trends_table.add_row(
                trend["week_starting"],
                str(trend["posts_published"]),
                f"{trend['avg_views_per_post']:.0f}",
                f"{trend['avg_engagement_per_post']:.1f}",
                change_str
            )

        self.console.print(Panel(
            trends_table,
            title=header_text,
            border_style="cyan"
        ))

    def _display_insights(self, insights: List[str]):
        """Display AI-generated insights"""
        insights_text = Text()

        for i, insight in enumerate(insights, 1):
            insights_text.append(f"{i}. ", style="bold cyan")
            insights_text.append(f"{insight}\n\n", style="white")

        self.console.print(Panel(
            insights_text,
            title="[bold]AI-Powered Insights & Recommendations[/bold]",
            border_style="magenta",
            padding=(1, 2)
        ))

    def display_quick_summary(self, dashboard_data: Dict):
        """Display a quick summary of key metrics

        Args:
            dashboard_data: Complete dashboard data
        """
        self.console.print("\n[bold cyan]Quick Summary[/bold cyan]")
        self.console.print("=" * 80, style="cyan")

        # Engagement rate
        engagement_data = dashboard_data.get("engagement_rates", {})
        if engagement_data.get("status") == "success":
            rates = engagement_data.get("engagement_rates", {})
            overall = rates.get("overall_rate", 0)
            status = engagement_data.get("benchmarks", {}).get("your_status", "unknown")

            self.console.print(f"\nEngagement Rate: [bold]{overall}%[/bold] ({status})")

        # Best posting time
        times_data = dashboard_data.get("optimal_times", {})
        if times_data.get("status") == "success":
            best_hours = times_data.get("best_hours", [])
            best_days = times_data.get("best_days", [])

            if best_hours:
                self.console.print(f"Best Time to Post: [bold cyan]{best_hours[0]['hour']}[/bold cyan]")
            if best_days:
                self.console.print(f"Best Day to Post: [bold cyan]{best_days[0]['day']}[/bold cyan]")

        # Trend
        trends_data = dashboard_data.get("performance_trends", {})
        if trends_data.get("status") == "success":
            trend = trends_data.get("overall_trend", "unknown")
            trend_colors = {
                "improving": "green",
                "declining": "red",
                "stable": "yellow"
            }
            color = trend_colors.get(trend, "white")
            self.console.print(f"Overall Trend: [{color}]{trend.upper()}[/{color}]")

        # Top content
        content_data = dashboard_data.get("content_performance", {})
        if content_data.get("status") == "success":
            top = content_data.get("top_performers", {})
            best_tone = top.get("best_tone")
            best_length = top.get("best_length")

            if best_tone:
                self.console.print(f"Best Performing Tone: [bold]{best_tone['tone']}[/bold]")
            if best_length:
                self.console.print(f"Best Performing Length: [bold]{best_length['length']}[/bold]")

        self.console.print("\n")

    def _display_comment_activity(self, data: Dict):
        """Display comment activity and engagement tracking"""
        if data.get("status") == "no_data":
            self.console.print("[yellow]No comment activity to display[/yellow]")
            return

        if data.get("status") != "success":
            return

        # Overview stats
        overview_table = Table(box=box.ROUNDED, show_header=False, padding=(0, 2))
        overview_table.add_column(style="cyan", width=30)
        overview_table.add_column(style="white", width=15)

        overview_table.add_row("Total Comments Generated", str(data.get("total_comments", 0)))
        overview_table.add_row("Comments Published", f"[bold green]{data.get('published_comments', 0)}[/bold green]")
        overview_table.add_row("Publish Rate", f"[bold]{data.get('publish_rate', 0)}%[/bold]")
        overview_table.add_row("", "")
        overview_table.add_row(f"Recent ({data.get('analysis_period_days', 30)} days)", f"{data.get('recent_comments', 0)} generated")
        overview_table.add_row("Recent Published", f"{data.get('recent_published', 0)} posted")
        overview_table.add_row("Avg Daily Comments", f"{data.get('avg_daily_comments', 0)}")

        self.console.print(Panel(
            overview_table,
            title="[bold]Comment Activity & Engagement[/bold]",
            border_style="cyan"
        ))

        # Comment tone breakdown
        by_tone = data.get("by_tone", {})
        if by_tone:
            self.console.print("\n")
            tone_table = Table(box=box.ROUNDED, show_header=True)
            tone_table.add_column("Tone", style="cyan", width=20)
            tone_table.add_column("Count", justify="right", style="green", width=10)

            sorted_tones = sorted(by_tone.items(), key=lambda x: x[1], reverse=True)
            for tone, count in sorted_tones:
                tone_table.add_row(tone.capitalize(), str(count))

            self.console.print(Panel(
                tone_table,
                title="[bold]Comments by Tone[/bold]",
                border_style="cyan"
            ))

        # Top authors we engage with
        top_authors = data.get("top_authors_engaged", [])
        if top_authors:
            self.console.print("\n")
            authors_table = Table(box=box.ROUNDED, show_header=True)
            authors_table.add_column("Rank", justify="center", style="dim", width=6)
            authors_table.add_column("Author", style="white", width=40)
            authors_table.add_column("Comments", justify="right", style="green", width=10)

            for i, author_data in enumerate(top_authors[:10], 1):
                authors_table.add_row(
                    f"#{i}",
                    author_data["author"][:40],
                    str(author_data["comment_count"])
                )

            self.console.print(Panel(
                authors_table,
                title="[bold]Most Engaged Authors[/bold]",
                border_style="cyan"
            ))
