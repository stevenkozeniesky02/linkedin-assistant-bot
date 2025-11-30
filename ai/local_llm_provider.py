"""Local LLM (Ollama) AI Provider Implementation"""

import requests
from typing import Dict, List, Optional

from .base import AIProvider


class LocalLLMProvider(AIProvider):
    """Local LLM provider for content generation (supports Ollama, LM Studio, etc.)"""

    def __init__(self, config: dict):
        super().__init__(config)

        # Get local LLM configuration
        local_config = config.get('local_llm', {})
        self.base_url = local_config.get('base_url', 'http://localhost:11434')
        self.model = local_config.get('model', 'llama2')
        self.temperature = local_config.get('temperature', 0.7)

        # Ensure base_url doesn't end with slash
        self.base_url = self.base_url.rstrip('/')

        # Test connection
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code != 200:
                print(f"Warning: Local LLM server at {self.base_url} returned status {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Warning: Could not connect to local LLM at {self.base_url}")
            print(f"Make sure Ollama (or your local LLM server) is running.")
            print(f"Error: {e}")

    def _generate(self, prompt: str, system_prompt: str = "") -> str:
        """Internal method to generate text using Ollama API"""

        url = f"{self.base_url}/api/generate"

        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system_prompt,
            "stream": False,
            "options": {
                "temperature": self.temperature
            }
        }

        try:
            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()
            return result.get('response', '')
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error calling local LLM: {e}")

    def generate_post(
        self,
        topic: str,
        tone: str = "professional",
        length: str = "medium",
        include_emojis: bool = True,
        include_hashtags: bool = True,
        max_hashtags: int = 5
    ) -> Dict[str, any]:
        """Generate a LinkedIn post using local LLM"""

        # Define length guidelines
        length_guidelines = {
            "short": "100-150 words, concise and punchy",
            "medium": "200-300 words, balanced depth and readability",
            "long": "400-500 words, in-depth exploration"
        }

        # Build the prompt
        prompt = f"""Generate a professional LinkedIn post about: {topic}

Requirements:
- Tone: {tone}
- Length: {length_guidelines.get(length, length_guidelines['medium'])}
- Include emojis: {'Yes' if include_emojis else 'No'}
- Include hashtags: {'Yes, up to ' + str(max_hashtags) if include_hashtags else 'No'}

The post should:
1. Start with a strong hook to grab attention
2. Provide valuable insights or information
3. Include a call-to-action or thought-provoking question
4. Be formatted for maximum readability (short paragraphs, line breaks)
5. Sound authentic and human, not overly promotional

Return the response in this format:
POST:
[Post content here]

HASHTAGS:
[Hashtags here, separated by spaces]
"""

        system_prompt = "You are an expert LinkedIn content strategist who creates engaging, professional posts that drive engagement."

        # Make API call
        content = self._generate(prompt, system_prompt)

        # Split into post and hashtags
        parts = content.split("HASHTAGS:")
        post_content = parts[0].replace("POST:", "").strip()
        hashtags = parts[1].strip() if len(parts) > 1 else ""

        return {
            "content": post_content,
            "hashtags": hashtags
        }

    def generate_comment(
        self,
        post_content: str,
        tone: str = "supportive",
        max_length: int = 200,
        user_context: Optional[Dict] = None
    ) -> str:
        """Generate a comment for a LinkedIn post"""

        # Build user context string
        context_str = ""
        if user_context:
            title = user_context.get('title', '')
            industry = user_context.get('industry', '')
            background = user_context.get('background', '')
            interests = user_context.get('interests', [])

            if title or industry or background:
                context_str = "\n\nYour profile:\n"
                if title:
                    context_str += f"- Title: {title}\n"
                if industry:
                    context_str += f"- Industry: {industry}\n"
                if background:
                    context_str += f"- Background: {background}\n"
                if interests:
                    context_str += f"- Interests: {', '.join(interests)}\n"

        prompt = f"""POST CONTENT:
{post_content}{context_str}

Write a {tone} comment (maximum {max_length} characters). Requirements:
- NO EMOJIS - write naturally like a real person
- Be conversational and authentic, not overly enthusiastic
- Comment from YOUR perspective based on your profile above
- DO NOT make up experiences or roles you don't have
- Avoid generic praise like "Great post!" or "Love this!"
- Provide specific insights, observations, or ask thoughtful questions
- Keep it concise - 2-3 sentences maximum
- Sound human, not like AI-generated content
- Avoid phrases like "I'm intrigued by", "fascinating", "I'd love to hear"
- DO NOT include any preamble like "Sure!" or "Here is a comment:"
- DO NOT wrap your response in quotation marks

CRITICAL: Return ONLY the raw comment text itself. No preamble, no quotes, no labels, no extra text.
"""

        system_prompt = "You are writing a LinkedIn comment. Return ONLY the comment text itself with absolutely no preamble, introduction, or explanation. Just the comment, nothing else."

        generated = self._generate(prompt, system_prompt).strip()

        # Strip common AI preambles
        preambles = [
            "Sure thing! Here is a thoughtful comment for the LinkedIn post:",
            "Sure! Here is a thoughtful comment:",
            "Here is a thoughtful comment:",
            "Sure thing!",
            "Here's a comment:",
            "Comment:",
        ]

        for preamble in preambles:
            if generated.startswith(preamble):
                generated = generated[len(preamble):].strip()
                break

        # Strip any surrounding quotes that the AI might have added
        if generated.startswith('"') and generated.endswith('"'):
            generated = generated[1:-1]
        if generated.startswith("'") and generated.endswith("'"):
            generated = generated[1:-1]

        return generated

    def optimize_content(
        self,
        content: str,
        performance_data: Optional[Dict] = None
    ) -> str:
        """Optimize content based on performance data"""

        performance_context = ""
        if performance_data:
            performance_context = f"""
Previous performance data:
- Average views: {performance_data.get('avg_views', 'N/A')}
- Average reactions: {performance_data.get('avg_reactions', 'N/A')}
- Average comments: {performance_data.get('avg_comments', 'N/A')}
- Top performing topics: {', '.join(performance_data.get('top_topics', []))}
"""

        prompt = f"""Optimize this LinkedIn post for better engagement:

Original post:
"{content}"

{performance_context}

Optimization guidelines:
1. Strengthen the hook to grab attention in first 2 lines
2. Improve readability with better formatting
3. Add strategic line breaks and white space
4. Make the call-to-action more compelling
5. Ensure it sounds authentic and conversational
6. Optimize for LinkedIn's algorithm (encourage comments/shares)

Return only the optimized post content.
"""

        system_prompt = "You are a LinkedIn growth expert who optimizes content for maximum engagement."

        return self._generate(prompt, system_prompt).strip()

    def analyze_post(
        self,
        post_content: str
    ) -> Dict[str, any]:
        """Analyze a post for engagement potential"""

        prompt = f"""Analyze this LinkedIn post and predict its engagement potential:

"{post_content}"

Provide analysis in this format:
ENGAGEMENT_SCORE: [1-10]
STRENGTHS: [Key strengths]
WEAKNESSES: [Areas for improvement]
SUGGESTIONS: [Specific actionable suggestions]
PREDICTED_PERFORMANCE: [Expected performance]
"""

        system_prompt = "You are a LinkedIn analytics expert who predicts post performance and provides actionable insights."

        content = self._generate(prompt, system_prompt)

        # Parse the response (simple parsing, could be improved)
        lines = content.split('\n')
        result = {
            "raw_analysis": content,
            "engagement_score": 7,  # Default
            "strengths": [],
            "weaknesses": [],
            "suggestions": []
        }

        # Extract engagement score
        for line in lines:
            if "ENGAGEMENT_SCORE:" in line:
                try:
                    score = int(line.split(':')[1].strip().split('-')[0])
                    result["engagement_score"] = score
                except:
                    pass

        return result

    def suggest_topics(
        self,
        industry: str,
        recent_posts: Optional[List[str]] = None
    ) -> List[str]:
        """Suggest topics for posts based on industry and trends"""

        recent_context = ""
        if recent_posts:
            recent_context = f"\n\nRecent topics covered (avoid repetition):\n- " + "\n- ".join(recent_posts)

        prompt = f"""Suggest 5 engaging LinkedIn post topics for someone in the {industry} industry.

Requirements:
- Topics should be timely and relevant
- Mix of educational, thought leadership, and personal experience angles
- Specific enough to write about, broad enough to be interesting
- Avoid repetition with recent posts{recent_context}

Return as a numbered list:
1. [Topic]
2. [Topic]
...
"""

        system_prompt = "You are a LinkedIn content strategist who identifies trending topics and engagement opportunities."

        content = self._generate(prompt, system_prompt)

        # Parse numbered list
        topics = []
        for line in content.split('\n'):
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith('-')):
                # Remove numbering
                topic = line.split('.', 1)[-1].strip() if '.' in line else line.lstrip('- ').strip()
                if topic:
                    topics.append(topic)

        return topics[:5]  # Return up to 5 topics

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
        """Generate multiple posts at once with variety"""

        tone_variations = ["professional", "casual", "thought_leader", "technical"]
        length_variations = ["short", "medium", "long"]

        posts = []

        for i, topic in enumerate(topics):
            # Vary tone and length if requested
            current_tone = tone
            current_length = length

            if vary_tone:
                current_tone = tone_variations[i % len(tone_variations)]
                current_length = length_variations[i % len(length_variations)]

            # Generate the post
            result = self.generate_post(
                topic=topic,
                tone=current_tone,
                length=current_length,
                include_emojis=include_emojis,
                include_hashtags=include_hashtags,
                max_hashtags=max_hashtags
            )

            posts.append({
                "topic": topic,
                "content": result["content"],
                "hashtags": result["hashtags"],
                "tone": current_tone,
                "length": current_length
            })

        return posts

    def suggest_hashtags(
        self,
        topic: str,
        industry: str,
        count: int = 10
    ) -> List[str]:
        """Research and suggest relevant hashtags for a topic"""

        prompt = f"""Suggest {count} relevant LinkedIn hashtags for a post about: {topic}

Industry: {industry}

Requirements:
- Mix of popular and niche hashtags
- Relevant to the topic and industry
- Appropriate for LinkedIn (professional, business-focused)
- Include both broad and specific tags
- Return hashtags without the # symbol

Return as a simple list, one hashtag per line.
"""

        system_prompt = "You are a LinkedIn hashtag research expert who identifies trending and relevant hashtags."

        content = self._generate(prompt, system_prompt)

        # Parse hashtags
        hashtags = []
        for line in content.split('\n'):
            line = line.strip()
            if line:
                # Remove # symbol if present, numbering, and dashes
                hashtag = line.lstrip('#- ').split('.', 1)[-1].strip()
                if hashtag and hashtag not in hashtags:
                    hashtags.append(hashtag)

        return hashtags[:count]

    def generate_text(
        self,
        prompt: str,
        max_tokens: int = 500,
        temperature: float = 0.7
    ) -> str:
        """
        Generate text from a custom prompt

        Args:
            prompt: The prompt to generate text from
            max_tokens: Maximum tokens to generate (not used in Ollama, included for API compatibility)
            temperature: Sampling temperature (0-1)

        Returns:
            Generated text
        """
        # Use the internal _generate method
        return self._generate(prompt=prompt)
