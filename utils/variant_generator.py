"""Variant Generator for A/B Testing"""

import re
from typing import List, Dict
from ai import get_ai_provider


class VariantGenerator:
    """Generate content variants for A/B testing"""

    def __init__(self, config: dict):
        """
        Initialize Variant Generator

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.ai_provider = get_ai_provider(config)

    def generate_variants(
        self,
        test_type: str,
        base_topic: str,
        variant_count: int = 3,
        **kwargs
    ) -> List[Dict]:
        """
        Generate content variants based on test type

        Args:
            test_type: Type of test (tone, length, emoji, headline, cta, hashtag)
            base_topic: Base topic for content generation
            variant_count: Number of variants to generate
            **kwargs: Additional parameters (industry, current_post, etc.)

        Returns:
            List of variant configurations
        """
        generators = {
            'tone': self._generate_tone_variants,
            'length': self._generate_length_variants,
            'emoji': self._generate_emoji_variants,
            'headline': self._generate_headline_variants,
            'cta': self._generate_cta_variants,
            'hashtag': self._generate_hashtag_variants
        }

        generator = generators.get(test_type)

        if not generator:
            raise ValueError(f"Unknown test type: {test_type}")

        return generator(base_topic, variant_count, **kwargs)

    def _generate_tone_variants(
        self,
        topic: str,
        variant_count: int,
        **kwargs
    ) -> List[Dict]:
        """Generate variants with different tones"""
        tones = ['professional', 'casual', 'thought_leader', 'analytical', 'storytelling']
        selected_tones = tones[:variant_count]

        variants = []

        for idx, tone in enumerate(selected_tones):
            config = {
                'tone': tone,
                'length': kwargs.get('length', 'medium'),
                'use_emojis': kwargs.get('use_emojis', False)
            }

            variants.append({
                'name': f'variant_{tone}',
                'label': f'{tone.replace("_", " ").title()} Tone',
                'config': config,
                'is_control': idx == 0
            })

        return variants

    def _generate_length_variants(
        self,
        topic: str,
        variant_count: int,
        **kwargs
    ) -> List[Dict]:
        """Generate variants with different lengths"""
        lengths = ['short', 'medium', 'long']
        selected_lengths = lengths[:variant_count]

        variants = []

        for idx, length in enumerate(selected_lengths):
            config = {
                'tone': kwargs.get('tone', 'professional'),
                'length': length,
                'use_emojis': kwargs.get('use_emojis', False)
            }

            length_labels = {
                'short': 'Short (1-2 paragraphs)',
                'medium': 'Medium (3-4 paragraphs)',
                'long': 'Long (5+ paragraphs)'
            }

            variants.append({
                'name': f'variant_{length}',
                'label': length_labels[length],
                'config': config,
                'is_control': idx == 0
            })

        return variants

    def _generate_emoji_variants(
        self,
        topic: str,
        variant_count: int,
        **kwargs
    ) -> List[Dict]:
        """Generate variants with/without emojis"""
        emoji_settings = [
            {'use_emojis': False, 'name': 'no_emoji', 'label': 'No Emojis'},
            {'use_emojis': True, 'name': 'with_emoji', 'label': 'With Emojis'},
            {'use_emojis': 'moderate', 'name': 'moderate_emoji', 'label': 'Moderate Emojis (1-2)'}
        ]

        variants = []

        for idx, emoji_cfg in enumerate(emoji_settings[:variant_count]):
            config = {
                'tone': kwargs.get('tone', 'professional'),
                'length': kwargs.get('length', 'medium'),
                'use_emojis': emoji_cfg['use_emojis']
            }

            variants.append({
                'name': emoji_cfg['name'],
                'label': emoji_cfg['label'],
                'config': config,
                'is_control': idx == 0
            })

        return variants

    def _generate_headline_variants(
        self,
        topic: str,
        variant_count: int,
        **kwargs
    ) -> List[Dict]:
        """Generate variants with different headline styles"""
        current_post = kwargs.get('current_post', '')

        prompt = f"""Generate {variant_count} different headline variations for a LinkedIn post about: {topic}

Create headlines with different approaches:
1. Question-based (engage curiosity)
2. Statement-based (bold claim)
3. Story-based (personal experience)
4. Data-based (statistics/numbers)
5. Contrarian (challenge common belief)

Return ONLY the headlines, one per line, without numbering."""

        headlines_text = self.ai_provider.generate_text(
            prompt=prompt,
            max_tokens=300
        )

        # Parse headlines
        headlines = [h.strip() for h in headlines_text.split('\n') if h.strip()][:variant_count]

        variants = []

        for idx, headline in enumerate(headlines):
            config = {
                'headline_style': self._classify_headline_style(headline),
                'headline': headline,
                'tone': kwargs.get('tone', 'professional'),
                'length': kwargs.get('length', 'medium')
            }

            variants.append({
                'name': f'headline_variant_{idx+1}',
                'label': f'Headline: {headline[:40]}...',
                'config': config,
                'is_control': idx == 0
            })

        return variants

    def _generate_cta_variants(
        self,
        topic: str,
        variant_count: int,
        **kwargs
    ) -> List[Dict]:
        """Generate variants with different calls-to-action"""
        cta_styles = [
            {'type': 'question', 'example': 'What are your thoughts?'},
            {'type': 'engagement', 'example': 'Share your experience in the comments'},
            {'type': 'action', 'example': 'Try this approach in your next project'},
            {'type': 'discussion', 'example': "Let's discuss this in the comments"},
            {'type': 'none', 'example': 'No CTA'}
        ]

        variants = []

        for idx, cta in enumerate(cta_styles[:variant_count]):
            # Generate specific CTA for this topic
            if cta['type'] != 'none':
                prompt = f"""Generate a {cta['type']}-based call-to-action for a LinkedIn post about: {topic}

Style: {cta['type']}
Example: {cta['example']}

Return ONLY the CTA text (one sentence, no extra explanation)."""

                cta_text = self.ai_provider.generate_text(
                    prompt=prompt,
                    max_tokens=50
                ).strip()
            else:
                cta_text = None

            config = {
                'cta_type': cta['type'],
                'cta_text': cta_text,
                'tone': kwargs.get('tone', 'professional'),
                'length': kwargs.get('length', 'medium')
            }

            variants.append({
                'name': f'cta_{cta["type"]}',
                'label': f'CTA: {cta["type"].title()}',
                'config': config,
                'is_control': idx == 0
            })

        return variants

    def _generate_hashtag_variants(
        self,
        topic: str,
        variant_count: int,
        **kwargs
    ) -> List[Dict]:
        """Generate variants with different hashtag strategies"""
        hashtag_strategies = [
            {'name': 'minimal', 'count': '1-2', 'strategy': 'Only highly relevant hashtags'},
            {'name': 'moderate', 'count': '3-5', 'strategy': 'Mix of specific and broad hashtags'},
            {'name': 'extensive', 'count': '7-10', 'strategy': 'Comprehensive hashtag coverage'},
            {'name': 'none', 'count': '0', 'strategy': 'No hashtags'}
        ]

        variants = []

        for idx, strategy in enumerate(hashtag_strategies[:variant_count]):
            if strategy['name'] != 'none':
                # Generate hashtags for this strategy
                prompt = f"""Generate {strategy['count']} relevant hashtags for a LinkedIn post about: {topic}

Strategy: {strategy['strategy']}
Industry: {kwargs.get('industry', 'Technology')}

Return ONLY the hashtags, space-separated, with # symbols."""

                hashtags = self.ai_provider.generate_text(
                    prompt=prompt,
                    max_tokens=100
                ).strip()
            else:
                hashtags = ''

            config = {
                'hashtag_strategy': strategy['name'],
                'hashtag_count': strategy['count'],
                'hashtags': hashtags,
                'tone': kwargs.get('tone', 'professional'),
                'length': kwargs.get('length', 'medium')
            }

            variants.append({
                'name': f'hashtag_{strategy["name"]}',
                'label': f'Hashtags: {strategy["count"]}',
                'config': config,
                'is_control': idx == 0
            })

        return variants

    def generate_post_from_variant(
        self,
        topic: str,
        variant_config: Dict,
        **kwargs
    ) -> str:
        """
        Generate full post content based on variant configuration

        Args:
            topic: Post topic
            variant_config: Variant configuration dictionary
            **kwargs: Additional parameters

        Returns:
            Generated post content
        """
        # Build generation prompt based on variant config
        tone = variant_config.get('tone', 'professional')
        length = variant_config.get('length', 'medium')
        use_emojis = variant_config.get('use_emojis', False)
        headline = variant_config.get('headline')
        cta_text = variant_config.get('cta_text')
        hashtags = variant_config.get('hashtags', '')

        # Length specifications
        length_specs = {
            'short': '1-2 short paragraphs (100-200 words)',
            'medium': '3-4 paragraphs (250-400 words)',
            'long': '5+ paragraphs (500+ words)'
        }

        # Build prompt
        prompt = f"""Generate a LinkedIn post about: {topic}

Requirements:
- Tone: {tone}
- Length: {length_specs.get(length, '3-4 paragraphs')}
- Industry: {kwargs.get('industry', 'Technology')}
"""

        if headline:
            prompt += f"- Start with this headline: {headline}\n"

        if use_emojis == True:
            prompt += "- Include relevant emojis (3-5 throughout the post)\n"
        elif use_emojis == 'moderate':
            prompt += "- Include 1-2 subtle emojis\n"
        else:
            prompt += "- NO emojis\n"

        if cta_text:
            prompt += f"- End with this call-to-action: {cta_text}\n"

        if hashtags:
            prompt += f"- Include these hashtags at the end: {hashtags}\n"
        elif 'hashtag_count' in variant_config and variant_config['hashtag_count'] == '0':
            prompt += "- NO hashtags\n"

        prompt += "\nGenerate ONLY the post content, nothing else."

        # Generate post
        post_content = self.ai_provider.generate_text(
            prompt=prompt,
            max_tokens=800
        )

        return post_content.strip()

    def _classify_headline_style(self, headline: str) -> str:
        """Classify headline style based on content"""
        headline_lower = headline.lower()

        if '?' in headline:
            return 'question'
        elif any(word in headline_lower for word in ['why', 'how', 'what', 'when', 'where']):
            return 'interrogative'
        elif any(char.isdigit() for char in headline):
            return 'data_driven'
        elif any(word in headline_lower for word in ['dont', "don't", 'never', 'stop', 'avoid']):
            return 'contrarian'
        elif any(word in headline_lower for word in ['story', 'learned', 'discovered', 'realized']):
            return 'story_based'
        else:
            return 'statement'

    def _extract_hashtags(self, content: str) -> List[str]:
        """Extract hashtags from post content"""
        return re.findall(r'#(\w+)', content)
