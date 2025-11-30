"""
PDF Report Generator

Generate professional PDF reports for LinkedIn analytics including:
- Weekly/monthly performance summaries
- Network growth metrics
- Engagement analytics
- AI-generated insights
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, PageBreak, Image
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from database.session import get_session
from database.models import Post, Analytics, Connection, Activity
from sqlalchemy import func

logger = logging.getLogger(__name__)


class PDFReportGenerator:
    """Generate PDF reports for LinkedIn analytics"""

    def __init__(self):
        self.session = get_session()
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Setup custom paragraph styles"""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#0077B5'),  # LinkedIn blue
            spaceAfter=30,
            alignment=TA_CENTER
        ))

        # Subtitle style
        self.styles.add(ParagraphStyle(
            name='CustomSubtitle',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#0077B5'),
            spaceAfter=12
        ))

        # Metric style
        self.styles.add(ParagraphStyle(
            name='Metric',
            parent=self.styles['Normal'],
            fontSize=14,
            textColor=colors.HexColor('#00A0DC'),
            spaceAfter=6
        ))

    def generate_weekly_report(
        self,
        output_file: str = None,
        weeks: int = 1
    ) -> str:
        """
        Generate a weekly performance report.

        Args:
            output_file: Output PDF filename
            weeks: Number of weeks to include

        Returns:
            Path to generated PDF
        """
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"linkedin_weekly_report_{timestamp}.pdf"

        logger.info(f"Generating weekly report: {output_file}")

        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(weeks=weeks)

        # Gather data
        data = self._gather_report_data(start_date, end_date)

        # Create PDF
        doc = SimpleDocTemplate(
            output_file,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )

        story = []

        # Title
        title = Paragraph(
            f"LinkedIn Performance Report<br/>{start_date.strftime('%b %d')} - {end_date.strftime('%b %d, %Y')}",
            self.styles['CustomTitle']
        )
        story.append(title)
        story.append(Spacer(1, 0.3*inch))

        # Executive Summary
        story.append(Paragraph("Executive Summary", self.styles['CustomSubtitle']))
        summary_data = self._create_summary_table(data)
        story.append(summary_data)
        story.append(Spacer(1, 0.3*inch))

        # Content Performance
        story.append(Paragraph("Content Performance", self.styles['CustomSubtitle']))
        content_table = self._create_content_performance_table(data)
        story.append(content_table)
        story.append(Spacer(1, 0.3*inch))

        # Network Growth
        story.append(Paragraph("Network Growth", self.styles['CustomSubtitle']))
        network_table = self._create_network_growth_table(data)
        story.append(network_table)
        story.append(Spacer(1, 0.3*inch))

        # Top Performing Posts
        story.append(Paragraph("Top Performing Posts", self.styles['CustomSubtitle']))
        top_posts_table = self._create_top_posts_table(data)
        story.append(top_posts_table)

        # Build PDF
        doc.build(story)

        logger.info(f"PDF report generated: {output_file}")
        return output_file

    def _gather_report_data(self, start_date: datetime, end_date: datetime) -> Dict:
        """Gather all data needed for the report"""
        # Posts published in period
        posts = self.session.query(Post).filter(
            Post.published == True,
            Post.published_at >= start_date,
            Post.published_at <= end_date
        ).all()

        # Analytics for these posts
        post_ids = [p.id for p in posts]
        analytics = self.session.query(Analytics).filter(
            Analytics.post_id.in_(post_ids)
        ).all() if post_ids else []

        # Network growth
        new_connections = self.session.query(func.count(Connection.id)).filter(
            Connection.connection_date >= start_date,
            Connection.connection_date <= end_date
        ).scalar()

        # Activity counts
        total_activities = self.session.query(func.count(Activity.id)).filter(
            Activity.performed_at >= start_date,
            Activity.performed_at <= end_date
        ).scalar()

        return {
            'posts': posts,
            'analytics': analytics,
            'new_connections': new_connections or 0,
            'total_activities': total_activities or 0,
            'start_date': start_date,
            'end_date': end_date
        }

    def _create_summary_table(self, data: Dict) -> Table:
        """Create executive summary table"""
        posts = data['posts']
        analytics = data['analytics']

        total_views = sum(a.views for a in analytics)
        total_likes = sum(a.likes for a in analytics)
        total_comments = sum(a.comments_count for a in analytics)
        total_shares = sum(a.shares for a in analytics)

        avg_engagement = (
            sum(a.engagement_rate for a in analytics) / len(analytics)
            if analytics else 0
        )

        summary_data = [
            ['Metric', 'Value'],
            ['Posts Published', str(len(posts))],
            ['Total Views', f'{total_views:,}'],
            ['Total Likes', f'{total_likes:,}'],
            ['Total Comments', f'{total_comments:,}'],
            ['Total Shares', f'{total_shares:,}'],
            ['Avg Engagement Rate', f'{avg_engagement:.2f}%'],
            ['New Connections', str(data['new_connections'])],
            ['Total Activities', str(data['total_activities'])],
        ]

        table = Table(summary_data, colWidths=[3*inch, 2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0077B5')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ]))

        return table

    def _create_content_performance_table(self, data: Dict) -> Table:
        """Create content performance breakdown table"""
        posts = data['posts']

        # Count by tone
        tone_counts = {}
        for post in posts:
            tone = post.tone or 'Unknown'
            tone_counts[tone] = tone_counts.get(tone, 0) + 1

        # Count by length
        length_counts = {}
        for post in posts:
            length = post.length or 'Unknown'
            length_counts[length] = length_counts.get(length, 0) + 1

        content_data = [
            ['Content Type', 'Count'],
            ['', ''],  # Separator
            ['By Tone:', ''],
        ]

        for tone, count in tone_counts.items():
            content_data.append([f'  {tone.title()}', str(count)])

        content_data.extend([
            ['', ''],  # Separator
            ['By Length:', ''],
        ])

        for length, count in length_counts.items():
            content_data.append([f'  {length.title()}', str(count)])

        table = Table(content_data, colWidths=[3*inch, 2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0077B5')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 2), (0, 2), 'Helvetica-Bold'),
            ('FONTNAME', (0, len(tone_counts)+4), (0, len(tone_counts)+4), 'Helvetica-Bold'),
        ]))

        return table

    def _create_network_growth_table(self, data: Dict) -> Table:
        """Create network growth metrics table"""
        # Get connection stats
        total_connections = self.session.query(func.count(Connection.id)).filter(
            Connection.is_active == True
        ).scalar()

        avg_quality = self.session.query(func.avg(Connection.quality_score)).scalar()

        network_data = [
            ['Metric', 'Value'],
            ['Total Active Connections', str(total_connections or 0)],
            ['New Connections (Period)', str(data['new_connections'])],
            ['Average Quality Score', f'{avg_quality:.2f}/10' if avg_quality else 'N/A'],
        ]

        table = Table(network_data, colWidths=[3*inch, 2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0077B5')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ]))

        return table

    def _create_top_posts_table(self, data: Dict) -> Table:
        """Create top performing posts table"""
        analytics = data['analytics']

        # Sort by views
        sorted_analytics = sorted(analytics, key=lambda a: a.views, reverse=True)[:5]

        top_posts_data = [
            ['Post ID', 'Views', 'Likes', 'Comments', 'Engagement %']
        ]

        for a in sorted_analytics:
            top_posts_data.append([
                str(a.post_id),
                f'{a.views:,}',
                str(a.likes),
                str(a.comments_count),
                f'{a.engagement_rate:.2f}%'
            ])

        table = Table(top_posts_data, colWidths=[1*inch, 1.2*inch, 1*inch, 1.2*inch, 1.2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0077B5')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))

        return table
