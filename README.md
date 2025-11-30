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

### 🚀 Autonomous Agent v2.0
- **Fully Integrated Automation** - Campaigns, safety monitoring, network growth all in one system
- **Scheduled Post Publishing** - Automatically publishes posts at optimal times
- **Campaign Execution** - Runs active engagement campaigns targeting specific hashtags/companies/influencers
- **Network Growth Automation** - Auto-accepts filtered connection requests and sends message sequences
- **SafetyMonitor Integration** - Real-time rate limiting with auto-pause on limits
- **Comprehensive Tracking** - Cycle summaries with performance across all activities
- **Human-Like Behavior** - Random delays, varied activity patterns

### 🎭 Automation Modes System

**Fully Implemented (Production Ready):**
- ✅ **Feed Engagement** - Auto-scroll feed, like posts, post AI comments with keyword filtering
- ✅ **Post Response** - Monitor your posts for comments and auto-reply with AI-generated responses
- ✅ **Connection Sync** - Automatically scrape and sync all LinkedIn connections to database

**Planned/Skeleton Implementation:**
- 🚧 **Group Networking** - Join LinkedIn groups, engage with discussions, send connection requests
- 🚧 **Connection Outreach** - Automated targeted connection requests with personalized messages
- 🚧 **Influencer Engagement** - Engage with industry leaders within first hour of posting
- 🚧 **Job Market Research** - Track companies, engage with recruiters, monitor opportunities
- 🚧 **Direct Messaging** - Automated message campaigns with personalization
- 🚧 **Content Repurposing** - Auto-repost top performers after X days with format adaptation
- 🚧 **Passive Listening** - Monitor keywords, track mentions, identify trends

**Framework Features:**
- **Smart Scheduling** - Time-window based mode rotation (morning/midday/evening)
- **Database Tracking** - Prevent duplicate actions across restarts

### 💬 Intelligent Engagement
- **Natural Comments** - AI generates authentic, conversational comments (no emojis, no AI-speak)
- **User Profile Context** - Comments reflect YOUR actual expertise and background
- **Interactive Mode** - Regenerate comments or switch posts without restarting
- **Quality Filtering** - Skips corporate brands, promotional content, duplicates

### 📊 Analytics & Content Strategy
- **Performance Tracking** - Monitor views, reactions, comments, shares
- **Topic Analysis** - Identify which topics resonate with your audience
- **Tone & Length Optimization** - Discover what style works best for you
- **Historical Trends** - Track growth and engagement over time
- **Hashtag Research** - AI-powered trending hashtag discovery based on your industry
- **Content Ideas Generator** - Get AI-generated content ideas tailored to your niche
- **Posting Schedule Optimizer** - Learn the best times and days to post
- **Best Performing Analysis** - See which content types drive the most engagement

### 🛡️ Safety & Ban Prevention
- **Activity Monitoring** - Tracks all LinkedIn actions with risk scoring
- **Rate Limiting** - Enforces hourly and daily action limits
- **Real-time Alerts** - Warns when approaching safety thresholds
- **Safety Dashboard** - Monitor current status and utilization
- **Human-in-the-Loop** - Always asks for approval before posting
- **Session Persistence** - Saves LinkedIn session to avoid constant re-login
- **Transparent** - All AI-generated content is clearly marked

### 🤝 Connection Management
- **Auto-Import Connections** - Automatically scrape and sync all LinkedIn connections
- **Quality Scoring** - Track connection quality (0-10 scale) based on engagement
- **Network Analytics** - Growth metrics, engagement breakdown, top companies
- **Target Audience Tracking** - Mark and track relevant connections in your niche
- **Engagement Monitoring** - Track messages, interactions, and post engagement
- **Health Recommendations** - AI-powered suggestions to improve network quality
- **Smart Scrolling** - Detects when all connections have been imported

### 🎯 Targeted Engagement Campaigns
- **Multi-Target Types** - Create campaigns targeting hashtags, companies, influencers, or topics
- **Smart Post Matching** - Automatically finds posts matching campaign targets in your feed
- **AI-Powered Engagement** - Generates personalized comments for matched posts
- **Campaign Analytics** - Track performance by target, engagement type, and success rate
- **Limit Management** - Per-campaign daily limits with safety integration
- **AI Recommendations** - Get suggestions to improve underperforming campaigns

### 🌱 Network Growth Automation
- **Connection Request Automation** - Send personalized requests with AI-generated messages (<200 chars)
- **Smart Auto-Accept** - Filter incoming requests by industry, title, company, mutual connections
- **Message Sequences** - Automated follow-up messages (welcome, day 3, day 7, etc.)
- **AI Personalization** - All messages customized based on connection profile
- **Sequence Templates** - Pre-built sequences (welcome, follow_up) or create custom
- **Full SafetyMonitor Integration** - Rate limiting on all connection activities

### 🎨 Profile Optimization Tools
- **Profile Audit & Scoring** - Comprehensive analysis of your LinkedIn profile with 0-100 scoring
- **AI Headline Generator** - Create optimized, keyword-rich headlines (40-120 chars)
- **AI Summary Rewriter** - Generate compelling About sections with achievements and CTAs
- **Skills Recommendations** - Get personalized skill suggestions based on your industry and role
- **Profile Comparison vs Competitors** - Competitive analysis against similar professionals with percentile ranking
- **Keyword Optimization** - Industry-specific keyword analysis for better searchability
- **Section-by-Section Analysis** - Detailed breakdowns for headline, summary, experience, and skills
- **Actionable Recommendations** - Prioritized suggestions to improve your profile score

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

# Run interactive menu (easiest way to get started!)
python linkedin.py

# OR use the full CLI
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

## 📁 Project Structure

```
linkedin-assistant-bot/
├── ai/                      # AI provider integrations
│   ├── anthropic_client.py
│   ├── gemini_client.py
│   ├── local_llm_client.py
│   └── openai_client.py
├── automation_modes/        # Automation mode implementations
│   ├── feed_engagement.py
│   ├── post_response.py
│   ├── connection_sync.py
│   ├── connection_outreach.py
│   └── ...
├── database/               # Database models and utilities
│   ├── models.py
│   └── session.py
├── docs/                   # Documentation
│   └── INTEGRATION_SUMMARY.md
├── examples/               # Example scripts and demos
│   ├── demo_feed_engagement.py
│   └── demo_network_graph.py
├── linkedin/               # LinkedIn automation core
│   ├── browser.py
│   ├── content_generator.py
│   └── engagement.py
├── scripts/                # Utility scripts
│   ├── automation_cli.py
│   ├── autonomous_agent_v2.py
│   ├── safety_connections_cli.py
│   ├── generate_network_graph.py
│   └── migrations/
├── linkedin.py            # Interactive menu CLI (beginner-friendly)
├── tests/                  # Test suite
│   └── test_integration.py
├── utils/                  # Utility modules
│   ├── analytics.py
│   ├── lead_scoring.py
│   ├── message_sequence_engine.py
│   ├── network_growth.py
│   └── safety_monitor.py
├── config.yaml            # Configuration file
├── main.py               # Main entry point
├── requirements.txt      # Python dependencies
├── LICENSE              # MIT License
└── README.md           # This file
```

---

## 📖 Usage

### Interactive Menu (Recommended for Beginners)

```bash
python linkedin.py
```

**Features:**
- Simple numbered menu interface
- First-time setup detection
- All automation modes accessible (1-9)
- Network visualization (V)
- Settings viewer (S)
- No need to memorize commands

**Menu Options:**
1. ✅ Feed Engagement - Like & comment on posts (WORKING)
2. ✅ Sync Connections - Import your connections (WORKING)
3. 🚧 Connection Outreach - Send connection requests (Planned)
4. ✅ Post Response - Reply to your post comments (WORKING)
5. 🚧 Direct Messages - Send message campaigns (Planned)
6. 🚧 Influencer Engagement - Engage with leaders (Planned)
7. 🚧 Group Networking - Join & engage in groups (Planned)
8. 🚧 Job Research - Monitor jobs & recruiters (Planned)
9. Full Automation - Run all active modes

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
# Advanced Analytics Dashboard (NEW!)
python main.py dashboard

# Quick summary view
python main.py dashboard --summary

# With AI-powered insights
python main.py dashboard --with-insights

# Analyze specific time period
python main.py dashboard --days 90

# View statistics
python main.py stats

# Analyze performance
python main.py analyze-performance

# Optimize based on past performance
python main.py optimize-post --topic "Cloud computing trends"
```

**Advanced Dashboard Features:**
- Optimal posting time analysis (best hours and days)
- Performance trends over time (weekly breakdown)
- Content performance by tone, length, and topic
- Engagement rate analysis with benchmarks
- AI-powered insights and recommendations (optional)

### Safety Monitoring

```bash
# Check current safety status
python main.py safety-status
```

**Displays:**
- Activity counts (hourly, daily, weekly)
- Rate limits and utilization percentages
- Risk score (0-1 scale)
- Active safety alerts
- Status indicator (safe, warning, limit_reached)

### Connection Management

```bash
# List all connections
python main.py connections --action list

# Add a new connection
python main.py connections --action add \
  --name "John Doe" \
  --url "https://linkedin.com/in/johndoe" \
  --title "Software Engineer" \
  --company "Tech Corp"

# View top connections by quality score
python main.py connections --action top --limit 20

# Mark connection as target audience
python main.py connections --action mark-target \
  --url "https://linkedin.com/in/johndoe"
```

### Network Analytics

```bash
# View network analytics and growth metrics
python main.py network-analytics

# Analyze specific time period
python main.py network-analytics --days 90
```

**Shows:**
- Total connections and growth rate
- Average quality score
- Engagement level breakdown
- Top companies in your network
- Network health recommendations

### Campaign Management

```bash
# Create a new campaign
python main.py campaigns --action create \
  --name "AI Thought Leaders" \
  --type hashtag \
  --targets "#AI,#MachineLearning,#DeepLearning"

# List all campaigns with stats
python main.py campaigns --action list

# View campaign analytics
python main.py campaigns --action analytics --campaign-id 1

# Get AI recommendations for improving campaign
python main.py campaigns --action recommendations --campaign-id 1

# Activate or pause a campaign
python main.py campaigns --action activate --campaign-id 1
python main.py campaigns --action pause --campaign-id 1

# Run campaigns manually (or let autonomous agent handle it)
python main.py run-campaigns
python main.py run-campaigns --campaign-id 1  # Run specific campaign
```

**Campaign Types:**
- `hashtag` - Target posts with specific hashtags
- `company` - Target posts from specific companies
- `influencer` - Target posts from specific LinkedIn profiles
- `topic` - Target posts mentioning specific topics/keywords

### Network Growth

```bash
# Send connection request with AI-generated message
python main.py connection-requests --action send \
  --profile-url "https://linkedin.com/in/johndoe" \
  --name "John Doe" \
  --title "Software Engineer" \
  --company "Tech Corp"

# List all connection requests
python main.py connection-requests --action list

# Check status of pending requests
python main.py connection-requests --action check

# Create a message sequence
python main.py message-sequences --action create \
  --name "Welcome Sequence"

# List all sequences
python main.py message-sequences --action list

# Enroll connection in sequence
python main.py message-sequences --action enroll \
  --sequence-id 1 \
  --connection-id 5

# View sequence stats
python main.py message-sequences --action stats --sequence-id 1

# Process incoming connection requests (auto-accept with filters)
python main.py process-incoming --max-requests 5

# Process due message sequences
python main.py process-sequences
```

### Automation Modes

```bash
# List all automation modes and their status
python scripts/automation_cli.py list-modes

# Run individual modes
python scripts/automation_cli.py feed-engagement --duration 15
python scripts/automation_cli.py connection-sync
python scripts/automation_cli.py post-response
python scripts/automation_cli.py group-networking
python scripts/automation_cli.py connection-outreach

# Run all active modes
python scripts/automation_cli.py run-all
```

**What Automation Modes Do:**

**✅ Fully Working Modes:**
- **Feed Engagement**: Scrolls through feed, likes/comments on relevant posts based on keywords
- **Connection Sync**: Automatically scrapes all your LinkedIn connections and syncs to database
  - Scrolls through connections page
  - Extracts name, profile URL, title, company
  - Updates existing connections or adds new ones
  - Detects when all connections have been scraped
- **Post Response**: Monitors your posts for new comments and auto-replies

**🚧 Skeleton/Planned Modes (return simulated data):**
- Group Networking, Connection Outreach, Influencer Engagement, Job Research, Direct Messaging, Content Repurposing, Passive Listening

###  Content Research & Strategy

AI-powered content research to optimize your LinkedIn strategy.

```bash
# Research trending hashtags for your industry
python scripts/content_research_cli.py hashtags --industry "Technology" --days 30

# Get hashtag recommendations for specific content
python scripts/content_research_cli.py hashtags-for-content "Just shipped a new AI feature..."

# Analyze your content performance
python scripts/content_research_cli.py analyze-performance --days 90

# Generate content ideas
python scripts/content_research_cli.py content-ideas --num 5

# Get recommended posting schedule
python scripts/content_research_cli.py posting-schedule

# View best performing hashtags
python scripts/content_research_cli.py best-hashtags --days 90
```

**What Content Research Does:**
- **Hashtag Discovery**: Finds trending hashtags based on your industry and historical performance
- **AI Hashtag Generation**: Uses AI to recommend optimal hashtags for your specific content
- **Performance Analysis**: Analyzes which content types, topics, and posting times work best
- **Content Ideas**: Generates AI-powered content ideas tailored to your industry
- **Posting Optimization**: Recommends optimal days, times, and content mix
- **Historical Tracking**: Tracks hashtag performance across all your posts
- **Group Networking**: Joins groups, engages with discussions, sends connection requests
- **Connection Outreach**: Sends targeted connection requests with AI messages
- More modes available - see `config.yaml` for full list and configuration

### Research Hashtags

```bash
python main.py hashtag-research --topic "machine learning" --industry "Technology"
```

### Suggest Topics

```bash
python main.py suggest-topics
```

AI suggests trending topics based on your industry and past performance.

### A/B Testing

```bash
# Create a new A/B test
python main.py ab-test --action create \
  --name "Tone Comparison Test" \
  --type tone \
  --topic "The future of AI in software development" \
  --variant-count 3 \
  --posts-per-variant 30

# List all A/B tests
python main.py ab-test --action list

# Start a test
python main.py ab-test --action start --test-id 1

# Generate variant posts for a test
python main.py ab-test --action generate-variants \
  --test-id 1 \
  --topic "AI trends in 2025"

# View test results
python main.py ab-test --action results --test-id 1

# Analyze test (statistical significance)
python main.py ab-test --action analyze --test-id 1

# Stop test and declare winner
python main.py ab-test --action stop --test-id 1

# Get AI recommendations
python main.py ab-test --action recommendations --test-id 1
```

**Test Types:**
- `tone` - Test different writing styles (professional, casual, thought leader, etc.)
- `length` - Compare short vs medium vs long posts
- `emoji` - With emojis vs without vs moderate
- `headline` - Different headline approaches (question, statement, data-driven, etc.)
- `cta` - Call-to-action variations (question, engagement, action, discussion, none)
- `hashtag` - Hashtag strategies (minimal, moderate, extensive, none)

**Workflow:**
1. Create test with variant count
2. Generate posts for each variant
3. Publish posts over time (manually or via scheduler)
4. System tracks performance automatically
5. Analyze results when sufficient sample size reached
6. Declare winner and apply insights to future content

**Statistical Features:**
- Minimum sample size requirements (default: 30 posts per variant)
- Confidence level testing (default: 95%)
- Two-sample t-test for significance
- P-value and lift calculations
- Confidence intervals for each variant
- Automated winner selection

### Profile Optimization

Optimize your LinkedIn profile for maximum visibility and impact.

```bash
# Analyze your profile with comprehensive scoring
python scripts/profile_optimizer_cli.py analyze --profile my_profile.json

# Generate an optimized headline
python scripts/profile_optimizer_cli.py generate-headline \
  --role "Software Engineer" \
  --industry "Technology" \
  --skills "Python,JavaScript,React,AWS"

# Generate an optimized summary/about section
python scripts/profile_optimizer_cli.py generate-summary \
  --role "Data Scientist" \
  --industry "Artificial Intelligence" \
  --achievements "Built ML models|Led team of 5|Published 3 papers" \
  --skills "Python,TensorFlow,PyTorch,SQL"

# Get personalized skill recommendations
python scripts/profile_optimizer_cli.py recommend-skills \
  --role "Software Engineer" \
  --skills "Python,JavaScript,React" \
  --num 10

# Compare your profile against competitors
python scripts/profile_optimizer_cli.py compare \
  --my-profile my_profile.json \
  --competitor-profiles competitor1.json competitor2.json competitor3.json
```

**Profile Structure (JSON):**
```json
{
  "headline": "Your current headline",
  "summary": "Your current About section text",
  "industry": "Technology",
  "experience": [
    {
      "title": "Software Engineer",
      "company": "Tech Corp",
      "description": "Built scalable systems using Python and AWS..."
    }
  ],
  "skills": ["Python", "JavaScript", "React", "AWS"]
}
```

**What Profile Optimization Does:**
- **Profile Audit**: Comprehensive 0-100 scoring across headline, summary, experience, and skills
- **Keyword Analysis**: Industry-specific keyword optimization for LinkedIn search
- **AI Generation**: Creates optimized headlines and summaries using AI
- **Skills Recommendations**: Suggests missing skills categorized by priority (high/medium/nice-to-have)
- **Competitive Analysis**: Compare your profile against competitors with percentile ranking and gap analysis
- **Skill Gap Analysis**: Identifies common, missing, and unique skills compared to competitors
- **Competitive Recommendations**: Get actionable suggestions based on competitive positioning
- **Actionable Insights**: Provides prioritized recommendations to improve your score
- **Section Breakdown**: Detailed analysis of length, keywords, achievements, and formatting

**Scoring System:**
- Headline (25%): Length, keywords, value proposition
- Summary (30%): Length, keywords, CTA, achievements, formatting
- Experience (25%): Entry count, keywords, quantifiable achievements
- Skills (15%): Skill count, industry relevance
- Overall (5%): Completeness and quality

### Network Visualization & Reporting

Visualize your LinkedIn network and generate professional PDF reports.

```bash
# Generate interactive network visualization
python scripts/reporting_cli.py network-graph --output network.html

# View network statistics
python scripts/reporting_cli.py network-stats

# Identify key connectors in your network
python scripts/reporting_cli.py key-connectors --top 15

# Generate PDF performance report
python scripts/reporting_cli.py pdf-report --weeks 4 --output monthly_report.pdf
```

**Network Visualization Features:**
- **Interactive Network Graph**: Explore your connections with an interactive HTML visualization
- **Company Clustering**: Automatically groups connections by company
- **Quality-Based Sizing**: Node sizes reflect connection quality scores
- **Engagement Color Coding**: Green (high), Orange (medium), Red (low), Purple (target audience)
- **Key Connector Analysis**: Identifies influential connections using betweenness centrality
- **Network Statistics**: Total connections, companies, engagement distribution, network density
- **Physics Simulation**: Dynamic graph layout with customizable physics

**PDF Report Features:**
- **Executive Summary**: Key metrics at a glance (posts, views, engagement, connections)
- **Content Performance**: Breakdown by tone and length
- **Network Growth**: Connection growth and quality metrics
- **Top Performing Posts**: Your best content ranked by views and engagement
- **Professional Design**: Clean, LinkedIn-branded PDF layout
- **Weekly or Monthly**: Flexible reporting periods (1-52 weeks)

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

### Autonomous Agent v2.0
```yaml
autonomous_agent:
  # Core settings
  check_interval: 300  # seconds (5 minutes)
  auto_post_scheduled: true
  enable_campaigns: true
  enable_network_growth: true

  # Per-cycle limits
  max_posts_per_cycle: 20
  max_engagements_per_cycle: 10
  max_connection_requests_per_cycle: 3
  max_incoming_requests_per_cycle: 5
  process_message_sequences: true
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
│   ├── engagement_manager.py  # Comments, likes, etc.
│   ├── connection_manager.py  # Connection quality tracking
│   └── campaign_manager.py    # Campaign management & analytics
│
├── automation_modes/      # Modular automation system
│   ├── base.py           # Base automation mode class
│   ├── manager.py        # Automation manager & scheduler
│   ├── feed_engagement.py    # Feed scrolling & engagement
│   ├── post_response.py      # Auto-reply to post comments
│   ├── connection_sync.py    # Auto-import LinkedIn connections
│   ├── group_networking.py   # LinkedIn group automation
│   ├── connection_outreach.py  # Connection requests
│   ├── influencer_engagement.py  # Engage with influencers
│   ├── job_market_research.py    # Job tracking & recruiter engagement
│   ├── direct_messaging.py       # DM campaigns
│   ├── content_repurposing.py    # Repost top performers
│   └── passive_listening.py      # Keyword monitoring & trends
│
├── database/              # Data persistence
│   ├── models.py         # SQLAlchemy models (Post, Comment, Campaign, Connection, Activity, etc.)
│   └── db.py             # Database operations
│
├── utils/                # Utilities
│   ├── scheduler.py      # Post scheduling
│   ├── safety_monitor.py # Activity tracking & rate limiting
│   ├── campaign_executor.py  # Campaign execution engine
│   ├── network_growth.py     # Connection automation & sequences
│   ├── analytics_engine.py   # Performance analytics
│   ├── analytics_visualizer.py  # Rich terminal visualization
│   ├── ab_testing_engine.py    # A/B testing with statistical analysis
│   └── variant_generator.py    # Content variant generation for tests
│
├── autonomous_agent_v2.py   # Autonomous agent v2.0 (integrated system)
├── automation_cli.py        # Automation modes CLI
├── demo_automation_modes.py # Automation modes demo
├── main.py                  # Main CLI entry point
├── config.yaml             # Configuration
└── requirements.txt        # Dependencies
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

**Recently Completed:**
- ✅ Advanced analytics dashboard
- ✅ Targeted engagement campaigns (hashtag/company/influencer)
- ✅ Connection management automation
- ✅ Auto-import LinkedIn connections (connection sync mode)
- ✅ Interactive menu CLI for beginners
- ✅ Direct messaging automation (message sequences)
- ✅ SafetyMonitor with rate limiting
- ✅ Network growth automation
- ✅ A/B testing framework with statistical analysis

**Upcoming Features:**
- 🚧 **Automation Modes - Full Implementation:**
  - Group Networking (join groups, engage, send requests)
  - Connection Outreach (targeted connection requests)
  - Influencer Engagement (engage with industry leaders)
  - Job Market Research (track companies, engage with recruiters)
  - Direct Messaging (message campaigns)
  - Content Repurposing (auto-repost top performers)
  - Passive Listening (monitor keywords, track mentions)
- Lead generation and tracking
- Multi-account support
- Content calendar planning
- Voice & tone learning from existing posts

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
