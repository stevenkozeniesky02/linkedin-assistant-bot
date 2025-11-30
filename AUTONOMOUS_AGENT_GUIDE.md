# Autonomous LinkedIn Agent Guide

## Overview

The Autonomous LinkedIn Agent is a fully automated system that runs continuously to:
- **Auto-post** scheduled content at optimal times
- **Auto-engage** with posts in your feed (likes & comments)
- **Auto-reply** to comments on your posts
- **Learn & optimize** engagement patterns over time

## Quick Start

### 1. Configure the Agent

Edit `config.yaml` and customize the `autonomous_agent` section:

```yaml
autonomous_agent:
  # Enable/disable features
  enable_engagement: true      # Auto-comment on feed posts
  reply_to_comments: true      # Reply to comments on your posts
  auto_post_scheduled: true    # Post scheduled content automatically

  # Timing
  check_interval: 300          # Check every 5 minutes (300 seconds)

  # Safety limits (avoid spam detection)
  max_engagements_per_cycle: 3
  max_replies_per_cycle: 5

  # Strategy: conservative, balanced, or aggressive
  engagement_strategy: 'balanced'
```

### 2. Run the Agent

**Default settings:**
```bash
python main.py autonomous
```

**Custom check interval:**
```bash
python main.py autonomous --check-interval 600  # Check every 10 minutes
```

**Different engagement strategy:**
```bash
python main.py autonomous --strategy aggressive  # More engagement
python main.py autonomous --strategy conservative  # Less engagement
```

**Or run directly:**
```bash
python autonomous_agent.py
```

### 3. Stop the Agent

Press `Ctrl+C` to gracefully stop the autonomous agent.

## How It Works

### Autonomous Cycle

Every cycle (default: 5 minutes), the agent:

1. **Checks for scheduled posts** → Posts any content due to be published
2. **Scans LinkedIn feed** → Finds interesting posts to engage with
3. **Generates AI comments** → Creates authentic, relevant comments
4. **Posts comments** → Engages with selected posts
5. **Checks your posts** → Looks for new comments to reply to
6. **Replies to comments** → AI-generated replies to user comments
7. **Sleeps** → Waits for next cycle

### Engagement Strategies

**Conservative:**
- 1 engagement per cycle
- Best for maintaining low profile
- ~12 engagements per hour (at 5min intervals)

**Balanced (Default):**
- 3 engagements per cycle
- Good mix of visibility and safety
- ~36 engagements per hour

**Aggressive:**
- 5 engagements per cycle
- Maximum visibility
- ~60 engagements per hour
- ⚠️ Higher spam detection risk

## Safety Features

### Built-in Protection

1. **Random delays** - Human-like timing between actions (30-120 seconds)
2. **Engagement limits** - Configurable max actions per cycle
3. **Smart scheduling** - Respects LinkedIn's rate limits
4. **Session management** - Automatically saves/restores login sessions

### Best Practices

✅ **DO:**
- Start with `conservative` strategy
- Monitor first few cycles manually
- Schedule posts during business hours
- Use authentic, industry-relevant content
- Keep check_interval >= 300 seconds (5 minutes)

❌ **DON'T:**
- Run multiple instances simultaneously
- Set check_interval < 120 seconds
- Use aggressive strategy 24/7
- Auto-post controversial content
- Ignore LinkedIn's platform guidelines

## Example Workflows

### 1. Daily Auto-Poster

Schedule 1-2 posts per day, let agent post them automatically:

```bash
# Schedule posts first
python main.py schedule --post-id 10
python main.py schedule --post-id 11

# Run agent to auto-post
python main.py autonomous --strategy conservative
```

### 2. Engagement Bot

Focus on commenting and engaging with your network:

```yaml
# config.yaml
autonomous_agent:
  enable_engagement: true
  auto_post_scheduled: false  # Disable auto-posting
  engagement_strategy: 'balanced'
```

```bash
python main.py autonomous
```

### 3. Full Automation

Set it and forget it - complete LinkedIn automation:

```bash
# Bulk generate content
python main.py bulk-generate --count 10

# Schedule posts throughout the week
python main.py schedule --post-id 12 --date "tomorrow 9am"
python main.py schedule --post-id 13 --date "thursday 2pm"

# Run autonomous agent
python main.py autonomous --strategy balanced
```

## Monitoring

### Real-Time Logs

The agent provides rich console output:

```
============================================================
Autonomous Agent Cycle - 2024-12-01 14:30:00
============================================================

Found 1 scheduled post(s) to publish

Publishing scheduled post: AI trends in 2024
✓ Post 12 published successfully

Checking feed for engagement opportunities...

Engaging with post by John Doe
  Great insights on machine learning trends...
✓ Comment posted successfully

✓ Cycle completed

Sleeping for 300 seconds...
```

### Analytics

Check your performance:

```bash
python main.py analyze-performance
python main.py stats
```

## Troubleshooting

### Agent won't start

1. Check LinkedIn credentials in session
2. Ensure Ollama/AI provider is running
3. Verify database is initialized:
   ```bash
   python migrate_db.py
   ```

### No engagements happening

1. Check `enable_engagement: true` in config
2. Verify posts exist in feed
3. Increase `max_engagements_per_cycle`
4. Check LinkedIn login is valid

### Scheduled posts not posting

1. Verify `auto_post_scheduled: true`
2. Check scheduled_time is in the past
3. Ensure posts are marked as scheduled:
   ```bash
   python main.py view-scheduled
   ```

### Browser stays open

This is normal - agent uses persistent browser session for faster operation. Browser closes when agent stops.

## Advanced Configuration

### Custom Delays

```yaml
autonomous_agent:
  random_delays: true
  min_delay_between_actions: 45  # Minimum 45 seconds
  max_delay_between_actions: 180  # Maximum 3 minutes
```

### Selective Engagement

Combine with `engagement` settings:

```yaml
engagement:
  engage_with:
    - 'connections'      # Only engage with your connections
    - 'industry_leaders' # Target specific profiles
  comment_tone: 'supportive'  # AI comment style
```

## Running as a Service

### macOS (launchd)

Create `~/Library/LaunchAgents/com.linkedin.autonomous.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.linkedin.autonomous</string>
    <key>ProgramArguments</key>
    <array>
        <string>/path/to/venv/bin/python</string>
        <string>/path/to/autonomous_agent.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
```

Load:
```bash
launchctl load ~/Library/LaunchAgents/com.linkedin.autonomous.plist
```

### Linux (systemd)

Create `/etc/systemd/system/linkedin-autonomous.service`:

```ini
[Unit]
Description=LinkedIn Autonomous Agent
After=network.target

[Service]
Type=simple
User=yourusername
WorkingDirectory=/path/to/linkedin-assistant-bot
ExecStart=/path/to/venv/bin/python autonomous_agent.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable:
```bash
sudo systemctl enable linkedin-autonomous
sudo systemctl start linkedin-autonomous
```

## Support

For issues or questions:
1. Check logs in `linkedin_assistant.log`
2. Review database: `sqlite3 linkedin_assistant.db`
3. Test individual features before enabling autonomous mode

---

**Remember**: With great automation comes great responsibility. Use the autonomous agent ethically and in compliance with LinkedIn's Terms of Service.
