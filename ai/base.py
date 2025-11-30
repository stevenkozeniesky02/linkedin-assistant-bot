"""Base AI Provider Interface"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class AIProvider(ABC):
    """Abstract base class for AI providers"""

    def __init__(self, config: dict):
        """
        Initialize the AI provider with configuration

        Args:
            config: Configuration dictionary from config.yaml
        """
        self.config = config

    @abstractmethod
    def generate_post(
        self,
        topic: str,
        tone: str = "professional",
        length: str = "medium",
        include_emojis: bool = True,
        include_hashtags: bool = True,
        max_hashtags: int = 5
    ) -> Dict[str, any]:
        """
        Generate a LinkedIn post

        Args:
            topic: The topic or subject for the post
            tone: Tone of the post (professional, casual, thought_leader, technical)
            length: Length of post (short, medium, long)
            include_emojis: Whether to include emojis
            include_hashtags: Whether to include hashtags
            max_hashtags: Maximum number of hashtags

        Returns:
            Dictionary with 'content' and 'hashtags' keys
        """
        pass

    @abstractmethod
    def generate_comment(
        self,
        post_content: str,
        tone: str = "supportive",
        max_length: int = 200,
        user_context: Optional[Dict] = None
    ) -> str:
        """
        Generate a comment for a LinkedIn post

        Args:
            post_content: The content of the post to comment on
            tone: Tone of the comment (supportive, inquisitive, analytical)
            max_length: Maximum length of the comment
            user_context: User's profile context (title, industry, background, interests)

        Returns:
            Generated comment text
        """
        pass

    @abstractmethod
    def optimize_content(
        self,
        content: str,
        performance_data: Optional[Dict] = None
    ) -> str:
        """
        Optimize content based on performance data

        Args:
            content: Original content to optimize
            performance_data: Analytics data from previous posts

        Returns:
            Optimized content
        """
        pass

    @abstractmethod
    def analyze_post(
        self,
        post_content: str
    ) -> Dict[str, any]:
        """
        Analyze a post for engagement potential

        Args:
            post_content: The post content to analyze

        Returns:
            Dictionary with analysis results (engagement_score, suggestions, etc.)
        """
        pass

    @abstractmethod
    def suggest_topics(
        self,
        industry: str,
        recent_posts: Optional[List[str]] = None
    ) -> List[str]:
        """
        Suggest topics for posts based on industry and trends

        Args:
            industry: User's industry/field
            recent_posts: List of recent post topics to avoid repetition

        Returns:
            List of suggested topics
        """
        pass

    @abstractmethod
    def generate_bulk_posts(
        self,
        topics: List[str],
        tone: str = "professional",
        length: str = "medium",
        include_emojis: bool = True,
        include_hashtags: bool = True,
        max_hashtags: int = 5,
        vary_tone: bool = True
    ) -> List[Dict[str, any]]:
        """
        Generate multiple posts at once

        Args:
            topics: List of topics to generate posts for
            tone: Base tone (will be varied if vary_tone=True)
            length: Base length (will be varied if vary_tone=True)
            include_emojis: Whether to include emojis
            include_hashtags: Whether to include hashtags
            max_hashtags: Maximum number of hashtags
            vary_tone: Whether to automatically vary tone/length for diversity

        Returns:
            List of dictionaries with post data including topic, content, hashtags
        """
        pass

    @abstractmethod
    def suggest_hashtags(
        self,
        topic: str,
        industry: str,
        count: int = 10
    ) -> List[str]:
        """
        Research and suggest relevant hashtags for a topic

        Args:
            topic: The post topic
            industry: User's industry/field
            count: Number of hashtags to suggest

        Returns:
            List of suggested hashtags (without # symbol)
        """
        pass

    @abstractmethod
    def generate_text(
        self,
        prompt: str,
        max_tokens: int = 500,
        temperature: float = 0.7
    ) -> str:
        """
        Generate text from a custom prompt (generic text generation)

        Args:
            prompt: The prompt to generate text from
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0-1)

        Returns:
            Generated text
        """
        pass
