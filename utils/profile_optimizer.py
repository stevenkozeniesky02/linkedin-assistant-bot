"""
Profile Optimization System

Analyzes and optimizes LinkedIn profile sections for maximum visibility and impact.
"""

import logging
import re
from typing import Dict, List, Optional
from collections import Counter

logger = logging.getLogger(__name__)


class ProfileOptimizer:
    """
    Analyze and optimize LinkedIn profile sections for SEO and engagement.
    """

    def __init__(self, ai_client=None, config: dict = None):
        self.ai_client = ai_client
        self.config = config or {}

        # Industry-specific keywords
        self.industry_keywords = {
            'Technology': [
                'software', 'development', 'engineering', 'programming', 'cloud',
                'AI', 'machine learning', 'data', 'agile', 'DevOps', 'API',
                'microservices', 'architecture', 'scalable', 'innovation'
            ],
            'Artificial Intelligence': [
                'AI', 'machine learning', 'deep learning', 'neural networks', 'NLP',
                'computer vision', 'data science', 'algorithms', 'models', 'training',
                'inference', 'transformers', 'PyTorch', 'TensorFlow'
            ],
            'Software Development': [
                'software engineer', 'full stack', 'backend', 'frontend', 'API',
                'database', 'cloud', 'microservices', 'CI/CD', 'testing',
                'Git', 'Python', 'JavaScript', 'React', 'Node.js'
            ],
            'Data Science': [
                'data science', 'analytics', 'machine learning', 'statistics',
                'Python', 'R', 'SQL', 'visualization', 'modeling', 'insights',
                'big data', 'predictive', 'algorithms', 'data engineering'
            ],
            'Career Growth': [
                'leadership', 'management', 'strategy', 'growth', 'development',
                'mentoring', 'communication', 'team building', 'innovation',
                'results-driven', 'problem solving', 'collaboration'
            ]
        }

        # Profile section weight for scoring
        self.section_weights = {
            'headline': 25,
            'summary': 30,
            'experience': 25,
            'skills': 15,
            'overall': 5
        }

    def analyze_profile(self, profile_data: Dict) -> Dict:
        """
        Comprehensive profile analysis with scoring and recommendations.

        Args:
            profile_data: Dictionary with profile sections:
                - headline: str
                - summary: str
                - experience: List[Dict] (title, company, description)
                - skills: List[str]
                - industry: str (optional)

        Returns:
            Dictionary with analysis results and recommendations
        """
        logger.info("Analyzing profile for optimization opportunities")

        industry = profile_data.get('industry', 'Technology')

        # Analyze each section
        headline_analysis = self._analyze_headline(
            profile_data.get('headline', ''),
            industry
        )

        summary_analysis = self._analyze_summary(
            profile_data.get('summary', ''),
            industry
        )

        experience_analysis = self._analyze_experience(
            profile_data.get('experience', []),
            industry
        )

        skills_analysis = self._analyze_skills(
            profile_data.get('skills', []),
            industry
        )

        # Calculate overall score
        overall_score = self._calculate_overall_score(
            headline_analysis,
            summary_analysis,
            experience_analysis,
            skills_analysis
        )

        # Generate strategic recommendations
        recommendations = self._generate_recommendations(
            headline_analysis,
            summary_analysis,
            experience_analysis,
            skills_analysis,
            overall_score
        )

        return {
            'overall_score': overall_score,
            'headline': headline_analysis,
            'summary': summary_analysis,
            'experience': experience_analysis,
            'skills': skills_analysis,
            'recommendations': recommendations,
            'industry': industry
        }

    def _analyze_headline(self, headline: str, industry: str) -> Dict:
        """Analyze profile headline for optimization."""
        if not headline:
            return {
                'score': 0,
                'length': 0,
                'keyword_count': 0,
                'keywords_found': [],
                'issues': ['Missing headline'],
                'suggestions': ['Add a compelling headline that includes your role and key skills']
            }

        length = len(headline)
        keywords = self.industry_keywords.get(industry, self.industry_keywords['Technology'])

        # Find matching keywords
        headline_lower = headline.lower()
        keywords_found = [kw for kw in keywords if kw.lower() in headline_lower]

        # Score calculation
        score = 0
        issues = []
        suggestions = []

        # Length scoring (optimal 40-120 characters)
        if length < 40:
            issues.append(f'Headline too short ({length} chars)')
            suggestions.append('Expand headline to 40-120 characters for better visibility')
            score += (length / 40) * 30
        elif length > 120:
            issues.append(f'Headline too long ({length} chars)')
            suggestions.append('Shorten headline to under 120 characters')
            score += 30
        else:
            score += 30

        # Keyword scoring
        keyword_score = min(50, len(keywords_found) * 10)
        score += keyword_score

        if len(keywords_found) < 2:
            issues.append('Few industry keywords')
            suggestions.append(f'Add more relevant keywords: {", ".join(keywords[:5])}')

        # Value proposition check
        value_indicators = ['help', 'build', 'create', 'deliver', 'drive', 'lead', 'expert']
        has_value = any(word in headline_lower for word in value_indicators)

        if has_value:
            score += 20
        else:
            issues.append('Missing value proposition')
            suggestions.append('Include what you do or the value you provide')

        return {
            'score': min(100, score),
            'length': length,
            'keyword_count': len(keywords_found),
            'keywords_found': keywords_found,
            'issues': issues,
            'suggestions': suggestions,
            'text': headline
        }

    def _analyze_summary(self, summary: str, industry: str) -> Dict:
        """Analyze profile summary/about section."""
        if not summary:
            return {
                'score': 0,
                'length': 0,
                'word_count': 0,
                'keyword_count': 0,
                'keywords_found': [],
                'issues': ['Missing summary'],
                'suggestions': ['Add a summary that highlights your expertise and achievements']
            }

        length = len(summary)
        words = summary.split()
        word_count = len(words)
        keywords = self.industry_keywords.get(industry, self.industry_keywords['Technology'])

        # Find matching keywords
        summary_lower = summary.lower()
        keywords_found = [kw for kw in keywords if kw.lower() in summary_lower]

        score = 0
        issues = []
        suggestions = []

        # Length scoring (optimal 200-2000 characters)
        if length < 200:
            issues.append(f'Summary too short ({length} chars)')
            suggestions.append('Expand summary to at least 200 characters')
            score += (length / 200) * 25
        elif length > 2000:
            issues.append(f'Summary too long ({length} chars)')
            suggestions.append('Consider shortening to under 2000 characters')
            score += 25
        else:
            score += 25

        # Keyword diversity
        keyword_score = min(30, len(keywords_found) * 3)
        score += keyword_score

        if len(keywords_found) < 5:
            issues.append('Limited keyword coverage')
            suggestions.append(f'Include more industry terms: {", ".join(keywords[:8])}')

        # Structure scoring
        paragraphs = summary.split('\n\n')
        if len(paragraphs) >= 2:
            score += 15
        else:
            issues.append('Poor formatting')
            suggestions.append('Break summary into 2-3 paragraphs for readability')

        # Call to action check
        cta_indicators = ['connect', 'reach out', 'contact', 'email', 'let\'s', 'collaborate']
        has_cta = any(word in summary_lower for word in cta_indicators)

        if has_cta:
            score += 15
        else:
            suggestions.append('Add a call-to-action at the end (e.g., "Let\'s connect!")')

        # Achievement indicators
        achievement_words = ['increased', 'reduced', 'improved', 'built', 'led', 'achieved', 'delivered']
        achievement_count = sum(1 for word in achievement_words if word in summary_lower)

        if achievement_count >= 2:
            score += 15
        else:
            suggestions.append('Include specific achievements or results')

        return {
            'score': min(100, score),
            'length': length,
            'word_count': word_count,
            'paragraph_count': len(paragraphs),
            'keyword_count': len(keywords_found),
            'keywords_found': keywords_found,
            'achievement_indicators': achievement_count,
            'has_cta': has_cta,
            'issues': issues,
            'suggestions': suggestions
        }

    def _analyze_experience(self, experience: List[Dict], industry: str) -> Dict:
        """Analyze experience section."""
        if not experience:
            return {
                'score': 0,
                'entry_count': 0,
                'issues': ['No experience entries'],
                'suggestions': ['Add at least 2-3 relevant work experiences']
            }

        keywords = self.industry_keywords.get(industry, self.industry_keywords['Technology'])
        score = 0
        issues = []
        suggestions = []

        total_keyword_count = 0
        entries_with_achievements = 0

        for entry in experience:
            description = entry.get('description', '').lower()

            # Check for keywords
            keywords_in_entry = [kw for kw in keywords if kw.lower() in description]
            total_keyword_count += len(keywords_in_entry)

            # Check for achievement indicators
            achievement_words = ['increased', 'reduced', 'improved', 'built', 'led', 'achieved', 'delivered', 'saved']
            if any(word in description for word in achievement_words):
                entries_with_achievements += 1

        # Entry count scoring
        if len(experience) >= 3:
            score += 30
        else:
            issues.append(f'Only {len(experience)} experience entries')
            suggestions.append('Add more relevant work experience entries')
            score += len(experience) * 10

        # Keyword scoring
        avg_keywords = total_keyword_count / max(len(experience), 1)
        keyword_score = min(40, avg_keywords * 8)
        score += keyword_score

        if avg_keywords < 2:
            suggestions.append('Add more industry-specific keywords to experience descriptions')

        # Achievement scoring
        achievement_ratio = entries_with_achievements / max(len(experience), 1)
        achievement_score = achievement_ratio * 30
        score += achievement_score

        if achievement_ratio < 0.5:
            issues.append('Few measurable achievements')
            suggestions.append('Add quantifiable achievements to each experience (e.g., "Increased efficiency by 40%")')

        return {
            'score': min(100, score),
            'entry_count': len(experience),
            'total_keywords': total_keyword_count,
            'avg_keywords_per_entry': round(avg_keywords, 1),
            'entries_with_achievements': entries_with_achievements,
            'achievement_ratio': round(achievement_ratio, 2),
            'issues': issues,
            'suggestions': suggestions
        }

    def _analyze_skills(self, skills: List[str], industry: str) -> Dict:
        """Analyze skills section."""
        if not skills:
            return {
                'score': 0,
                'skill_count': 0,
                'issues': ['No skills listed'],
                'suggestions': ['Add at least 10-15 relevant skills']
            }

        recommended_keywords = self.industry_keywords.get(industry, self.industry_keywords['Technology'])
        skills_lower = [s.lower() for s in skills]

        # Find matching keywords
        matching_skills = [kw for kw in recommended_keywords if kw.lower() in ' '.join(skills_lower)]

        score = 0
        issues = []
        suggestions = []

        # Skill count scoring (optimal 10-50)
        if len(skills) < 10:
            issues.append(f'Only {len(skills)} skills listed')
            suggestions.append('Add more skills (aim for 10-15 core skills)')
            score += len(skills) * 5
        elif len(skills) > 50:
            issues.append(f'Too many skills ({len(skills)})')
            suggestions.append('Focus on your top 30-40 most relevant skills')
            score += 50
        else:
            score += 50

        # Keyword match scoring
        keyword_score = min(50, len(matching_skills) * 5)
        score += keyword_score

        if len(matching_skills) < 5:
            issues.append('Few industry-relevant skills')
            suggestions.append(f'Add these skills: {", ".join(recommended_keywords[:10])}')

        return {
            'score': min(100, score),
            'skill_count': len(skills),
            'matching_skills': len(matching_skills),
            'matched_keywords': matching_skills,
            'issues': issues,
            'suggestions': suggestions
        }

    def _calculate_overall_score(self, headline, summary, experience, skills) -> int:
        """Calculate weighted overall profile score."""
        weighted_score = (
            (headline['score'] * self.section_weights['headline'] / 100) +
            (summary['score'] * self.section_weights['summary'] / 100) +
            (experience['score'] * self.section_weights['experience'] / 100) +
            (skills['score'] * self.section_weights['skills'] / 100)
        )

        return min(100, int(weighted_score))

    def _generate_recommendations(self, headline, summary, experience, skills, overall_score) -> List[str]:
        """Generate prioritized recommendations based on analysis."""
        recommendations = []

        # Priority 1: Critical issues (score < 30)
        if headline['score'] < 30:
            recommendations.append('🔴 CRITICAL: Improve your headline - it\'s your first impression')
        if summary['score'] < 30:
            recommendations.append('🔴 CRITICAL: Add or significantly improve your summary section')

        # Priority 2: Important improvements (score < 60)
        if headline['score'] < 60:
            recommendations.extend([f'• {s}' for s in headline['suggestions'][:2]])
        if summary['score'] < 60:
            recommendations.extend([f'• {s}' for s in summary['suggestions'][:2]])
        if experience['score'] < 60:
            recommendations.extend([f'• {s}' for s in experience['suggestions'][:2]])
        if skills['score'] < 60:
            recommendations.extend([f'• {s}' for s in skills['suggestions'][:1]])

        # Priority 3: Optimizations (score < 80)
        if overall_score >= 60 and overall_score < 80:
            recommendations.append('🟡 Good progress! Focus on adding industry keywords and quantifiable achievements')

        # Success message
        if overall_score >= 80:
            recommendations.insert(0, '🟢 Excellent! Your profile is well-optimized. Keep it updated!')

        # Limit to top 8 recommendations
        return recommendations[:8] if recommendations else ['Your profile looks good! Keep it updated.']

    def generate_optimized_headline(self, current_headline: str, role: str, industry: str, skills: List[str]) -> str:
        """Generate an optimized headline using AI."""
        if not self.ai_client:
            logger.warning("No AI client available for headline generation")
            return current_headline

        try:
            prompt = f"""Generate an optimized LinkedIn headline for a professional in the {industry} industry.

Role: {role}
Current headline: {current_headline if current_headline else "None"}
Key skills: {", ".join(skills[:5])}

Requirements:
- 40-120 characters
- Include role and key value proposition
- Use relevant industry keywords
- Make it engaging and searchable
- Show what value you bring

Return only the optimized headline text, no explanation."""

            optimized = self.ai_client.generate_text(prompt)
            return optimized.strip().strip('"').strip("'")

        except Exception as e:
            logger.error(f"Error generating headline: {e}")
            return current_headline

    def generate_optimized_summary(self, current_summary: str, role: str, industry: str,
                                  achievements: List[str], skills: List[str]) -> str:
        """Generate an optimized summary using AI."""
        if not self.ai_client:
            logger.warning("No AI client available for summary generation")
            return current_summary

        try:
            prompt = f"""Generate an optimized LinkedIn summary/about section for a {role} in {industry}.

Current summary: {current_summary if current_summary else "None"}
Key achievements: {", ".join(achievements[:3])}
Top skills: {", ".join(skills[:8])}

Requirements:
- 200-400 words
- Include relevant industry keywords naturally
- Highlight key achievements with numbers/results
- Show personality and passion
- Include a call-to-action
- Format in 2-3 short paragraphs

Return only the optimized summary text."""

            optimized = self.ai_client.generate_text(prompt)
            return optimized.strip()

        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return current_summary

    def get_skill_recommendations(self, current_skills: List[str], industry: str,
                                 role: str = None, max_suggestions: int = 10) -> Dict:
        """
        Recommend skills to add based on industry and current skills.

        Args:
            current_skills: List of current skills
            industry: Industry/field
            role: Optional role/title for more targeted recommendations
            max_suggestions: Maximum number of skills to suggest

        Returns:
            Dictionary with recommended skills categorized by priority
        """
        logger.info(f"Generating skill recommendations for {industry}")

        # Get industry keywords as base recommendations
        recommended_keywords = self.industry_keywords.get(industry, self.industry_keywords['Technology'])

        # Normalize current skills for comparison
        current_skills_lower = [s.lower() for s in current_skills]

        # Find missing industry-relevant skills
        missing_skills = []
        for keyword in recommended_keywords:
            # Check if keyword is not already in skills
            if keyword.lower() not in ' '.join(current_skills_lower):
                missing_skills.append(keyword)

        # Categorize recommendations
        high_priority = []
        medium_priority = []
        nice_to_have = []

        # High priority: Core industry skills (first third)
        core_count = len(recommended_keywords) // 3
        core_skills = recommended_keywords[:core_count]

        for skill in missing_skills:
            if skill in core_skills:
                high_priority.append(skill)
            elif len(high_priority) + len(medium_priority) < core_count * 2:
                medium_priority.append(skill)
            else:
                nice_to_have.append(skill)

        # Use AI to generate additional personalized recommendations if available
        ai_recommendations = []
        if self.ai_client and role:
            try:
                prompt = f"""Generate a comma-separated list of {max_suggestions} relevant skills for a {role} in {industry}.

Current skills they already have: {", ".join(current_skills[:15])}

Focus on:
- In-demand, marketable skills
- Both technical and soft skills
- Skills that complement what they already have

Return ONLY the skill names separated by commas, nothing else. No numbering, no explanations, no extra text.

Example: Docker, Kubernetes, TypeScript, CI/CD, System Design"""

                ai_response = self.ai_client.generate_text(prompt).strip()

                # Split by common separators and clean up
                if ',' in ai_response:
                    ai_skills = [s.strip() for s in ai_response.split(',')]
                elif '\n' in ai_response:
                    # Handle numbered lists
                    ai_skills = []
                    for line in ai_response.split('\n'):
                        # Remove numbering and bullet points
                        cleaned = re.sub(r'^\d+[\.)]\s*', '', line.strip())
                        cleaned = re.sub(r'^[•\-*]\s*', '', cleaned)
                        if cleaned:
                            ai_skills.append(cleaned)
                else:
                    ai_skills = [ai_response]

                # Filter out skills already in current skills and limit
                ai_recommendations = []
                for skill in ai_skills:
                    skill_clean = skill.strip().strip('"').strip("'")
                    if (skill_clean and
                        skill_clean.lower() not in ' '.join(current_skills_lower) and
                        len(skill_clean) < 50):  # Avoid long explanatory text
                        ai_recommendations.append(skill_clean)
                    if len(ai_recommendations) >= max_suggestions:
                        break

            except Exception as e:
                logger.error(f"Error getting AI skill recommendations: {e}")

        # Combine and deduplicate recommendations
        all_recommendations = {
            'high_priority': high_priority[:5],
            'medium_priority': medium_priority[:5],
            'nice_to_have': nice_to_have[:5],
            'ai_suggested': ai_recommendations,
            'total_current': len(current_skills),
            'missing_industry_keywords': len(missing_skills)
        }

        return all_recommendations
