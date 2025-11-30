# 🤖 LinkedIn Assistant Bot

> **AI-powered LinkedIn automation** for intelligent content generation, strategic engagement, and autonomous profile growth

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

---

## ✨ Features

### 🎯 Core Capabilities
- **Multi-Provider AI Generation** - Choose from OpenAI (GPT-4), Anthropic (Claude), Google (Gemini), or Local LLMs (Ollama)
- **One-Command Setup** - Interactive initialization wizard (`python main.py init`)
- **Bulk Content Creation** - Generate multiple posts at once with varied tones and styles
- **Smart Scheduling** - Schedule posts for optimal times
- **Intelligent Analytics** - Track performance and optimize strategy

### 🚀 Autonomous Agent
- **AI-Powered Post Selection** - Intelligently ranks feed posts by engagement potential
- **Automatic Engagement** - Comments on relevant posts with human-like, personalized responses
- **Configurable Strategies** - Conservative, balanced, or aggressive engagement modes
- **Smart Content Filtering** - Automatically skips promotional and low-quality posts
- **Human-Like Behavior** - Random delays, varied activity patterns

### 💬 Intelligent Engagement
- **Natural Comments** - AI generates authentic, conversational comments (no emojis, no AI-speak)
- **User Profile Context** - Comments reflect YOUR actual expertise and background
- **Interactive Mode** - Regenerate comments or switch posts without restarting
- **Quality Filtering** - Skips corporate brands, promotional content, duplicates

### 📊 Analytics & Insights
- **Performance Tracking** - Monitor views, reactions, comments, shares
- **Topic Analysis** - Identify which topics resonate with your audience
- **Tone & Length Optimization** - Discover what style works best for you
- **Historical Trends** - Track growth and engagement over time

### 🛡️ Safety & Ethics
- **Human-in-the-Loop** - Always asks for approval before posting
- **Rate Limiting** - Configurable limits to avoid spam detection
- **Session Persistence** - Saves LinkedIn session to avoid constant re-login
- **Transparent** - All AI-generated content is clearly marked

---

## 🚦 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/linkedin-assistant-bot.git
cd linkedin-assistant-bot

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run interactive setup wizard
python main.py init
```

The setup wizard will ask you for:
- Your LinkedIn profile information (name, title, industry, expertise)
- AI provider preference (OpenAI, Anthropic, Gemini, or Local LLM)
- Engagement strategy (conservative, balanced, or aggressive)

### Set Your API Key (if using cloud AI)

```bash
# For OpenAI
export OPENAI_API_KEY='your-key-here'

# For Anthropic
export ANTHROPIC_API_KEY='your-key-here'

# For Google Gemini
export GOOGLE_API_KEY='your-key-here'
```

Or add to `.env` file:
```
OPENAI_API_KEY=your-key-here
ANTHROPIC_API_KEY=your-key-here
GOOGLE_API_KEY=your-key-here
```

### For Local LLM (Free!)

```bash
# Install Ollama
# Visit: https://ollama.ai

# Pull a model
ollama pull llama2

# The bot will automatically connect to http://localhost:11434
```

---

## 📖 Usage

### Generate a Post

```bash
python main.py generate-post --topic "The future of AI in software development"
```

**Options:**
- `--tone` - professional, casual, thought_leader, technical
- `--length` - short, medium, long

### Engage with Feed

```bash
python main.py engage
```

**Interactive workflow:**
1. Displays relevant posts from your feed
2. Select a post to engage with
3. AI generates a personalized comment
4. Preview and choose: (p)ost, (r)egenerate, (d)ifferent post, (e)xit

### Run Autonomous Agent

```bash
python main.py autonomous
```

**What it does:**
- Checks for scheduled posts and publishes them
- Analyzes feed posts with AI scoring
- Engages with top-ranked posts automatically
- Runs continuously on a configurable schedule

**Options:**
- `--check-interval 300` - Check every 5 minutes
- `--strategy aggressive` - Use aggressive engagement strategy

### Schedule Posts

```bash
# View scheduled posts
python main.py view-scheduled

# Schedule a post
python main.py schedule --post-id 5 --date "2024-01-20 10:00"

# Cancel a scheduled post
python main.py cancel-schedule --post-id 5
```

### Bulk Generation

```bash
python main.py bulk-generate --count 10 --industry "Technology"
```

Generates multiple posts with varied tones and lengths for content planning.

### Analytics

```bash
# View statistics
python main.py stats

# Analyze performance
python main.py analyze-performance

# Optimize based on past performance
python main.py optimize-post --topic "Cloud computing trends"
```

### Research Hashtags

```bash
python main.py hashtag-research --topic "machine learning" --industry "Technology"
```

### Suggest Topics

```bash
python main.py suggest-topics
```

AI suggests trending topics based on your industry and past performance.

---

## ⚙️ Configuration

The `config.yaml` file controls all settings. Key sections:

### AI Provider
```yaml
ai_provider: local  # openai, anthropic, gemini, or local

local_llm:
  base_url: http://localhost:11434
  model: llama2
  temperature: 0.7
```

### User Profile (for authentic comments)
```yaml
user_profile:
  name: "Your Name"
  title: "Data Analyst"  # Your actual job title
  industry: "Technology"
  background: "Experienced in Python, automation, and AI/ML systems"
  interests: ["artificial intelligence", "automation", "software development"]
```

### Autonomous Agent
```yaml
autonomous_agent:
  enable_engagement: true
  auto_post_scheduled: true
  check_interval: 300  # seconds
  engagement_strategy: balanced  # conservative, balanced, aggressive
  max_engagements_per_cycle: 3
  reply_to_comments: true
```

### Engagement Filters
```yaml
engagement:
  comment_tone: supportive  # supportive, inquisitive, analytical
  skip_promotional: true
  skip_corporate_brands:
    - Wells Fargo
    - Bank of America
    - Chase
  engage_with:
    - connections
    - industry_leaders
    - trending_posts
```

### Safety Limits
```yaml
safety:
  require_approval: true
  max_posts_per_day: 3
  max_actions_per_hour: 5
  prevent_duplicate_content: true
  avoid_topics:
    - politics
    - religion
    - controversial
```

---

## 🏗️ Architecture

```
linkedin-assistant-bot/
├── ai/                      # AI provider integrations
│   ├── base.py             # Abstract base class
│   ├── openai_provider.py  # OpenAI GPT-4
│   ├── anthropic_provider.py  # Anthropic Claude
│   ├── gemini_provider.py  # Google Gemini
│   └── local_llm_provider.py  # Ollama/LM Studio
│
├── linkedin/               # LinkedIn automation
│   ├── client.py          # Browser automation
│   ├── post_manager.py    # Post creation/management
│   └── engagement_manager.py  # Comments, likes, etc.
│
├── database/              # Data persistence
│   ├── models.py         # SQLAlchemy models
│   └── database.py       # Database operations
│
├── utils/                # Utilities
│   └── scheduler.py      # Post scheduling
│
├── autonomous_agent.py   # Autonomous agent
├── main.py              # CLI entry point
├── config.yaml          # Configuration
└── requirements.txt     # Dependencies
```

---

## 🎨 Examples

### Example Generated Post

```
The debate around AI-generated code quality is fascinating.

After working with GitHub Copilot and ChatGPT for the past year, I've noticed that while these tools can save significant time, they require a robust verification process. The key isn't to blindly trust AI output, but to adapt our workflows to leverage its strengths while accounting for its limitations.

What verification strategies are you using for AI-generated code in your team?

#SoftwareDevelopment #AI #CodeQuality #TechLeadership
```

### Example AI-Generated Comment

```
As someone who's worked with AI-generated code, I've noticed that while it can save time and resources, it's crucial to have a solid verification process in place to ensure accuracy and reliability. It's not enough to just rely on the AI assistant - we need to adapt our workflows to account for its limitations and strengths.
```

**Note:** Comments are generated based on YOUR profile (title, industry, expertise), so they sound authentic and relevant to your experience.

---

## 📊 Database Schema

Posts, comments, and analytics are stored in SQLite:

```python
Post:
  - id, content, hashtags, topic, tone, length
  - ai_provider, ai_model
  - published, published_at
  - is_scheduled, scheduled_time
  - created_at, updated_at

Comment:
  - id, content, tone
  - target_post_author, target_post_url, target_post_excerpt
  - ai_provider
  - published, published_at
  - created_at

Analytics:
  - id, post_id
  - views, reactions, comments, shares
  - profile_views
  - last_updated, created_at
```

---

## 🛣️ Roadmap

See [ROADMAP.md](ROADMAP.md) for detailed feature plans.

**Upcoming Features:**
- Advanced analytics dashboard
- A/B testing framework
- Targeted engagement campaigns (hashtag/company/influencer)
- Content recycling (auto-repost top performers)
- Lead generation and tracking
- Connection management automation
- Direct messaging automation
- Multi-account support

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

See [ROADMAP.md](ROADMAP.md) to pick a feature to implement.

---

## ⚠️ Disclaimer

**This tool is for personal use to enhance LinkedIn engagement.**

- ✅ Always review AI-generated content before posting
- ✅ Use responsibly and ethically
- ✅ Comply with LinkedIn's Terms of Service
- ✅ Respect rate limits and avoid spam behavior
- ⚠️ The autonomous agent should be supervised
- ⚠️ Not responsible for account restrictions from misuse

**This is a productivity tool, not a spam tool.** Use it to enhance genuine professional engagement, not to game the system.

---

## 📄 License

MIT License - See [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Built with [Selenium](https://selenium.dev) for LinkedIn automation
- Powered by [OpenAI](https://openai.com), [Anthropic](https://anthropic.com), [Google](https://ai.google.dev/), and [Ollama](https://ollama.ai)
- CLI interface with [Click](https://click.palletsprojects.com/) and [Rich](https://rich.readthedocs.io/)
- Database management with [SQLAlchemy](https://www.sqlalchemy.org/)

---

## 📞 Support

- **Issues:** [GitHub Issues](https://github.com/yourusername/linkedin-assistant-bot/issues)
- **Discussions:** [GitHub Discussions](https://github.com/yourusername/linkedin-assistant-bot/discussions)

---

**Made with ❤️ for the LinkedIn community**
