"""A/B Testing Engine with Statistical Analysis"""

import json
import random
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
import math

from database.models import ABTest, TestVariant, TestAssignment, Post, Analytics
from ai import get_ai_provider


class ABTestingEngine:
    """Manage A/B tests with statistical analysis and auto-optimization"""

    def __init__(self, db_session: Session, config: dict):
        """
        Initialize A/B Testing Engine

        Args:
            db_session: SQLAlchemy database session
            config: Configuration dictionary
        """
        self.db = db_session
        self.config = config
        self.ai_provider = get_ai_provider(config)

    def create_test(
        self,
        name: str,
        test_type: str,
        hypothesis: str = None,
        description: str = None,
        variants_config: List[Dict] = None,
        confidence_level: float = 0.95,
        minimum_sample_size: int = 30,
        planned_duration_days: int = 30
    ) -> ABTest:
        """
        Create a new A/B test

        Args:
            name: Test name
            test_type: Type of test (headline, tone, length, emoji, time_of_day, cta, hashtag)
            hypothesis: What you're testing
            description: Detailed description
            variants_config: List of variant configurations
            confidence_level: Statistical confidence level (default 0.95)
            minimum_sample_size: Minimum posts per variant (default 30)
            planned_duration_days: How long to run the test

        Returns:
            Created ABTest instance
        """
        # Create the test
        test = ABTest(
            name=name,
            description=description,
            hypothesis=hypothesis,
            test_type=test_type,
            status='draft',
            confidence_level=confidence_level,
            minimum_sample_size=minimum_sample_size,
            planned_duration_days=planned_duration_days
        )

        self.db.add(test)
        self.db.commit()

        # Create variants
        if variants_config:
            for idx, variant_cfg in enumerate(variants_config):
                variant = TestVariant(
                    test_id=test.id,
                    variant_name=variant_cfg.get('name', f'variant_{idx}'),
                    variant_label=variant_cfg.get('label', f'Variant {idx}'),
                    variant_config=json.dumps(variant_cfg.get('config', {})),
                    is_control=variant_cfg.get('is_control', idx == 0)
                )
                self.db.add(variant)

        self.db.commit()
        return test

    def start_test(self, test_id: int) -> Dict:
        """
        Start an A/B test

        Args:
            test_id: Test ID to start

        Returns:
            Status dictionary
        """
        test = self.db.query(ABTest).filter(ABTest.id == test_id).first()

        if not test:
            return {'success': False, 'error': 'Test not found'}

        if test.status != 'draft':
            return {'success': False, 'error': f'Test is already {test.status}'}

        # Check if test has variants
        variant_count = self.db.query(func.count(TestVariant.id)).filter(
            TestVariant.test_id == test_id
        ).scalar()

        if variant_count < 2:
            return {'success': False, 'error': 'Test must have at least 2 variants'}

        # Start the test
        test.status = 'running'
        test.start_date = datetime.utcnow()

        if test.planned_duration_days:
            test.end_date = datetime.utcnow() + timedelta(days=test.planned_duration_days)

        self.db.commit()

        return {
            'success': True,
            'message': f'Test "{test.name}" started',
            'start_date': test.start_date,
            'end_date': test.end_date
        }

    def assign_post_to_variant(
        self,
        post_id: int,
        test_id: int = None,
        variant_id: int = None,
        assignment_method: str = 'random'
    ) -> Optional[TestAssignment]:
        """
        Assign a post to a test variant

        Args:
            post_id: Post ID to assign
            test_id: Test ID (if variant_id not provided)
            variant_id: Specific variant to assign to (optional)
            assignment_method: Assignment method (random, manual, weighted)

        Returns:
            TestAssignment instance or None
        """
        # Check if post already assigned
        existing = self.db.query(TestAssignment).filter(
            TestAssignment.post_id == post_id
        ).first()

        if existing:
            print(f"Post {post_id} already assigned to variant {existing.variant_id}")
            return existing

        # Get or select variant
        if variant_id:
            variant = self.db.query(TestVariant).filter(TestVariant.id == variant_id).first()
            if not variant:
                print(f"Variant {variant_id} not found")
                return None
            test_id = variant.test_id

        elif test_id:
            # Get all active variants for this test
            variants = self.db.query(TestVariant).filter(
                TestVariant.test_id == test_id
            ).all()

            if not variants:
                print(f"No variants found for test {test_id}")
                return None

            # Random assignment (can be weighted in future)
            variant = random.choice(variants)
        else:
            print("Must provide either test_id or variant_id")
            return None

        # Create assignment
        assignment = TestAssignment(
            test_id=test_id,
            variant_id=variant.id,
            post_id=post_id,
            assignment_method=assignment_method
        )

        self.db.add(assignment)

        # Update variant post count
        variant.posts_count += 1

        self.db.commit()

        return assignment

    def sync_test_metrics(self, test_id: int) -> Dict:
        """
        Sync metrics from Analytics to test assignments and calculate variant stats

        Args:
            test_id: Test ID

        Returns:
            Status dictionary with updated metrics
        """
        test = self.db.query(ABTest).filter(ABTest.id == test_id).first()

        if not test:
            return {'success': False, 'error': 'Test not found'}

        # Get all assignments for this test
        assignments = self.db.query(TestAssignment).filter(
            TestAssignment.test_id == test_id
        ).all()

        updated_count = 0

        for assignment in assignments:
            # Get analytics for this post
            analytics = self.db.query(Analytics).filter(
                Analytics.post_id == assignment.post_id
            ).first()

            if analytics:
                # Sync metrics
                assignment.sync_metrics_from_analytics(analytics)
                updated_count += 1

        # Update variant aggregate metrics
        variants = test.variants

        for variant in variants:
            # Sum up all metrics from assignments
            variant_assignments = self.db.query(TestAssignment).filter(
                TestAssignment.variant_id == variant.id
            ).all()

            variant.total_views = sum(a.views for a in variant_assignments)
            variant.total_likes = sum(a.likes for a in variant_assignments)
            variant.total_comments = sum(a.comments_count for a in variant_assignments)
            variant.total_shares = sum(a.shares for a in variant_assignments)

            # Calculate averages
            variant.calculate_metrics()

            # Calculate standard deviation of engagement rates
            if len(variant_assignments) > 1:
                engagement_rates = [a.engagement_rate for a in variant_assignments if a.engagement_rate > 0]
                if engagement_rates:
                    variant.std_deviation = self._calculate_std_dev(engagement_rates)

        self.db.commit()

        return {
            'success': True,
            'assignments_updated': updated_count,
            'variants_updated': len(variants)
        }

    def analyze_test(self, test_id: int) -> Dict:
        """
        Perform statistical analysis on test results

        Args:
            test_id: Test ID to analyze

        Returns:
            Analysis results dictionary
        """
        test = self.db.query(ABTest).filter(ABTest.id == test_id).first()

        if not test:
            return {'success': False, 'error': 'Test not found'}

        # Sync metrics first
        self.sync_test_metrics(test_id)

        variants = test.variants

        if len(variants) < 2:
            return {'success': False, 'error': 'Need at least 2 variants to analyze'}

        # Check if we have enough sample size
        min_sample = test.minimum_sample_size
        insufficient_samples = [v for v in variants if v.posts_count < min_sample]

        if insufficient_samples:
            return {
                'success': False,
                'error': f'Insufficient sample size. Need {min_sample} posts per variant.',
                'current_samples': {v.variant_name: v.posts_count for v in variants},
                'minimum_required': min_sample
            }

        # Perform statistical tests
        results = {
            'success': True,
            'test_id': test_id,
            'test_name': test.name,
            'test_type': test.test_type,
            'variants': []
        }

        # Get control variant (or first variant)
        control = next((v for v in variants if v.is_control), variants[0])

        # Compare each variant to control
        for variant in variants:
            variant_result = {
                'variant_id': variant.id,
                'variant_name': variant.variant_name,
                'variant_label': variant.variant_label,
                'posts_count': variant.posts_count,
                'avg_engagement_rate': round(variant.avg_engagement_rate, 2),
                'total_views': variant.total_views,
                'total_likes': variant.total_likes,
                'total_comments': variant.total_comments,
                'total_shares': variant.total_shares
            }

            if variant.id != control.id:
                # Calculate statistical significance
                p_value, is_significant = self._two_sample_t_test(
                    control, variant, test.confidence_level
                )

                variant_result['p_value'] = round(p_value, 4) if p_value else None
                variant_result['is_significant'] = is_significant

                # Calculate lift
                if control.avg_engagement_rate > 0:
                    lift = ((variant.avg_engagement_rate - control.avg_engagement_rate) /
                            control.avg_engagement_rate * 100)
                    variant_result['lift_percent'] = round(lift, 2)
                else:
                    variant_result['lift_percent'] = None

                # Calculate confidence interval
                ci_lower, ci_upper = self._confidence_interval(
                    variant.avg_engagement_rate,
                    variant.std_deviation if variant.std_deviation else 0,
                    variant.posts_count,
                    test.confidence_level
                )

                variant_result['confidence_interval'] = (round(ci_lower, 2), round(ci_upper, 2))
                variant.confidence_interval_lower = ci_lower
                variant.confidence_interval_upper = ci_upper

            else:
                variant_result['is_control'] = True

            results['variants'].append(variant_result)

        # Determine winner
        winner = self._determine_winner(variants, control, test.confidence_level)

        if winner:
            results['winner'] = {
                'variant_id': winner.id,
                'variant_name': winner.variant_name,
                'variant_label': winner.variant_label,
                'avg_engagement_rate': round(winner.avg_engagement_rate, 2)
            }

            # Update test with winner
            test.winner_variant_id = winner.id
            test.is_significant = True
            winner.is_winner = True

        else:
            results['winner'] = None
            results['message'] = 'No statistically significant winner found'

        self.db.commit()

        return results

    def stop_test(self, test_id: int, declare_winner: bool = True) -> Dict:
        """
        Stop a running test

        Args:
            test_id: Test ID
            declare_winner: Whether to analyze and declare winner

        Returns:
            Status dictionary
        """
        test = self.db.query(ABTest).filter(ABTest.id == test_id).first()

        if not test:
            return {'success': False, 'error': 'Test not found'}

        if test.status != 'running':
            return {'success': False, 'error': f'Test is not running (status: {test.status})'}

        # Analyze if requested
        analysis = None
        if declare_winner:
            analysis = self.analyze_test(test_id)

        # Stop the test
        test.status = 'completed'
        test.completed_at = datetime.utcnow()

        self.db.commit()

        return {
            'success': True,
            'message': f'Test "{test.name}" stopped',
            'completed_at': test.completed_at,
            'analysis': analysis
        }

    def get_test_results(self, test_id: int) -> Dict:
        """
        Get formatted test results for display

        Args:
            test_id: Test ID

        Returns:
            Formatted results dictionary
        """
        test = self.db.query(ABTest).filter(ABTest.id == test_id).first()

        if not test:
            return {'success': False, 'error': 'Test not found'}

        # Sync and analyze
        self.sync_test_metrics(test_id)
        analysis = self.analyze_test(test_id)

        return {
            'success': True,
            'test': {
                'id': test.id,
                'name': test.name,
                'description': test.description,
                'hypothesis': test.hypothesis,
                'type': test.test_type,
                'status': test.status,
                'start_date': test.start_date,
                'end_date': test.end_date,
                'completed_at': test.completed_at,
                'is_significant': test.is_significant,
                'p_value': test.p_value
            },
            'analysis': analysis
        }

    def list_tests(self, status: str = None) -> List[Dict]:
        """
        List all A/B tests

        Args:
            status: Filter by status (draft, running, completed, etc.)

        Returns:
            List of test dictionaries
        """
        query = self.db.query(ABTest)

        if status:
            query = query.filter(ABTest.status == status)

        tests = query.order_by(ABTest.created_at.desc()).all()

        return [{
            'id': t.id,
            'name': t.name,
            'type': t.test_type,
            'status': t.status,
            'variants_count': len(t.variants),
            'total_posts': sum(v.posts_count for v in t.variants),
            'is_significant': t.is_significant,
            'winner': t.winner.variant_name if t.winner else None,
            'created_at': t.created_at,
            'start_date': t.start_date,
            'completed_at': t.completed_at
        } for t in tests]

    def generate_ai_recommendations(self, test_id: int) -> str:
        """
        Generate AI-powered recommendations based on test results

        Args:
            test_id: Test ID

        Returns:
            AI-generated recommendations
        """
        results = self.get_test_results(test_id)

        if not results['success']:
            return "Unable to generate recommendations: Test not found"

        test_info = results['test']
        analysis = results['analysis']

        # Build prompt for AI
        prompt = f"""Analyze these A/B test results and provide actionable recommendations:

Test: {test_info['name']}
Hypothesis: {test_info['hypothesis']}
Type: {test_info['type']}

Results:
{json.dumps(analysis['variants'], indent=2)}

Winner: {analysis.get('winner', {}).get('variant_name', 'No significant winner')}

Provide:
1. Key insights from the data
2. Specific recommendations for content optimization
3. Suggestions for follow-up tests
4. Strategic implications for LinkedIn content strategy

Keep it concise and actionable (3-5 bullet points)."""

        recommendations = self.ai_provider.generate_text(
            prompt=prompt,
            max_tokens=500
        )

        return recommendations

    # Statistical helper methods

    def _two_sample_t_test(
        self,
        variant_a: TestVariant,
        variant_b: TestVariant,
        confidence_level: float
    ) -> Tuple[Optional[float], bool]:
        """
        Perform two-sample t-test

        Returns:
            (p_value, is_significant)
        """
        # Get engagement rates for each variant
        assignments_a = self.db.query(TestAssignment).filter(
            TestAssignment.variant_id == variant_a.id
        ).all()

        assignments_b = self.db.query(TestAssignment).filter(
            TestAssignment.variant_id == variant_b.id
        ).all()

        rates_a = [a.engagement_rate for a in assignments_a if a.engagement_rate >= 0]
        rates_b = [a.engagement_rate for a in assignments_b if a.engagement_rate >= 0]

        if len(rates_a) < 2 or len(rates_b) < 2:
            return None, False

        # Calculate means and standard deviations
        mean_a = sum(rates_a) / len(rates_a)
        mean_b = sum(rates_b) / len(rates_b)

        std_a = self._calculate_std_dev(rates_a)
        std_b = self._calculate_std_dev(rates_b)

        n_a = len(rates_a)
        n_b = len(rates_b)

        # Calculate pooled standard deviation
        pooled_std = math.sqrt(((n_a - 1) * std_a**2 + (n_b - 1) * std_b**2) / (n_a + n_b - 2))

        # Calculate t-statistic
        if pooled_std == 0:
            return None, False

        t_stat = abs((mean_a - mean_b) / (pooled_std * math.sqrt(1/n_a + 1/n_b)))

        # Degrees of freedom
        df = n_a + n_b - 2

        # Approximate p-value using simplified approach
        # For production, use scipy.stats.t.sf
        # This is a rough approximation
        if t_stat > 2.0:  # Roughly equivalent to p < 0.05 for df > 30
            p_value = 0.05
        elif t_stat > 1.5:
            p_value = 0.15
        else:
            p_value = 0.5

        # Check significance
        alpha = 1 - confidence_level
        is_significant = p_value < alpha

        return p_value, is_significant

    def _confidence_interval(
        self,
        mean: float,
        std_dev: float,
        sample_size: int,
        confidence_level: float
    ) -> Tuple[float, float]:
        """
        Calculate confidence interval

        Returns:
            (lower_bound, upper_bound)
        """
        if sample_size < 2:
            return mean, mean

        # Z-score for confidence level (approximation)
        z_score = 1.96 if confidence_level >= 0.95 else 1.645

        margin_of_error = z_score * (std_dev / math.sqrt(sample_size))

        return (mean - margin_of_error, mean + margin_of_error)

    def _calculate_std_dev(self, values: List[float]) -> float:
        """Calculate standard deviation"""
        if len(values) < 2:
            return 0.0

        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return math.sqrt(variance)

    def _determine_winner(
        self,
        variants: List[TestVariant],
        control: TestVariant,
        confidence_level: float
    ) -> Optional[TestVariant]:
        """
        Determine the winning variant

        Returns:
            Winning TestVariant or None
        """
        # Find variant with highest engagement rate
        best_variant = max(variants, key=lambda v: v.avg_engagement_rate)

        # If it's the control, no winner
        if best_variant.id == control.id:
            return None

        # Check if it's statistically significant
        p_value, is_significant = self._two_sample_t_test(
            control, best_variant, confidence_level
        )

        if is_significant:
            return best_variant

        return None
