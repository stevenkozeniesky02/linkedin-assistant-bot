# Network Growth Integration - Summary

## Overview

Successfully integrated **Lead Scoring Engine** and **Message Sequence Engine** into the existing `network_growth.py` automation system.

---

## 1. Lead Scoring Engine Integration

### Features Added

**Smart Prospect Scoring (0-100 scale)**
- Profile quality scoring (30% weight)
- Engagement history tracking (25% weight)
- Mutual connection analysis (20% weight)
- Company targeting (15% weight)
- Activity level detection (10% weight)

**Priority Tiers**
- Critical (80-100): Top prospects, reach out immediately
- High (60-79): Strong prospects, prioritize
- Medium (40-59): Worth connecting with
- Low (20-39): Low priority
- Ignore (<20): Not worth the effort

### Implementation Details

**Modified Methods:**
- `send_connection_request()`: Now scores prospects before sending requests
  - Filters out prospects below minimum threshold (default: 40/100)
  - Shows score breakdown and context hints
  - Customizes messages based on score factors

- `_generate_connection_message()`: Enhanced with score context
  - Acknowledges engagement history
  - Mentions mutual connections
  - References target companies

**New Methods:**
- `batch_score_prospects()`: Score multiple prospects and return sorted by score
- `get_prospect_score_stats()`: Get statistics on scored prospects

### Database Changes

Added to `ConnectionRequest` model:
```python
lead_score = Column(Float)              # Overall lead score (0-100)
score_breakdown = Column(Text)          # JSON-encoded breakdown
priority_tier = Column(String(20))      # critical, high, medium, low, ignore
```

### Configuration

```yaml
network_growth:
  use_lead_scoring: true           # Enable/disable lead scoring
  min_lead_score: 40               # Minimum score to send request (0-100)

  # Target companies (high priority)
  target_companies:
    - "Google"
    - "Microsoft"
    - "Amazon"

  # Target titles/keywords
  target_titles:
    - "Engineering Manager"
    - "Product Manager"
    - "VP Engineering"

  # Target industries
  target_industries:
    - "Computer Software"
    - "Internet"
    - "Information Technology"
```

### Example Usage

```python
# Automatic scoring when sending request
growth_automation.send_connection_request(
    profile_url="https://linkedin.com/in/john-doe",
    name="John Doe",
    title="Engineering Manager",
    company="Google",
    location="San Francisco, CA",
    industry="Computer Software",
    mutual_connections=5,
    has_profile_photo=True,
    connection_count=500,
    recent_activity=datetime.now() - timedelta(days=2),
    source='manual'
)
# Output:
# ✅ Lead score: 78.5/100 (Priority: high)
#    🎯 Target company employee
#    🤝 Strong mutual connections

# Batch scoring
prospects = [...]
scored = growth_automation.batch_score_prospects(prospects)
stats = growth_automation.get_prospect_score_stats(scored)
# Output:
# {
#   'total_prospects': 50,
#   'average_score': 52.3,
#   'critical_priority': 5,
#   'high_priority': 12,
#   'medium_priority': 20,
#   'low_priority': 10,
#   'ignore': 3
# }
```

---

## 2. Message Sequence Engine Integration

### Features Added

**A/B Testing for Message Sequences**
- Create variant A and variant B sequences
- Statistical comparison with minimum sample requirements
- Auto-detect winner with 10% lift threshold
- Confidence intervals and p-values

**Behavioral Triggers**
- Profile view trigger: Auto-enroll when someone views your profile
- Post engagement trigger: Auto-enroll when someone engages with your content
- Automatic enrollment in appropriate sequences

**Sequence Branching**
- Different paths based on response/no-response
- Conditional logic for sequence flow
- Dynamic step selection

**Timezone-Based Scheduling**
- Auto-detect timezone from location
- Schedule messages at optimal local times (default: 9am their time)
- Avoid sending messages at inconvenient hours

### Implementation Details

**Modified Methods:**
- `enroll_in_sequence()`: Now supports timezone scheduling
  - Detects timezone from connection's location
  - Schedules first message at appropriate local time
  - Falls back to UTC if timezone detection fails

- `process_due_sequence_messages()`: Checks behavioral triggers
  - Runs behavioral trigger checks before processing messages
  - Auto-enrolls connections based on triggers
  - Returns count of new enrollments

**New Methods:**
- `create_ab_test_sequence()`: Create A/B test with two variants
- `get_ab_test_results()`: Get A/B test results and winner
- `_check_behavioral_triggers()`: Check and process behavioral triggers

### Configuration

```yaml
network_growth:
  # Message sequence settings
  use_sequence_ab_testing: true      # Enable A/B testing
  use_behavioral_triggers: true      # Enable behavioral triggers
  use_timezone_scheduling: true      # Enable timezone scheduling
```

### Example Usage

**A/B Testing:**
```python
# Create A/B test for welcome messages
variant_a = [
    {"delay_days": 0, "template": "welcome"},
    {"delay_days": 3, "template": "follow_up"}
]

variant_b = [
    {"delay_days": 0, "template": "welcome_personalized"},
    {"delay_days": 5, "template": "value_add"}
]

ab_test = growth_automation.create_ab_test_sequence(
    name="Welcome Message Test",
    variant_a_steps=variant_a,
    variant_b_steps=variant_b,
    split_ratio=0.5,  # 50/50 split
    trigger_type='new_connection',
    description="Testing welcome message approaches"
)
# Output:
# ✅ Created A/B test: Welcome Message Test
#    Variant A: Sequence 15
#    Variant B: Sequence 16
#    Split: 50% A / 50% B

# Later, check results
results = growth_automation.get_ab_test_results(
    variant_a_id=15,
    variant_b_id=16
)
# Output:
# {
#   'variant_a': {'responses': 12, 'total': 50, 'response_rate': 0.24},
#   'variant_b': {'responses': 18, 'total': 50, 'response_rate': 0.36},
#   'winner': 'variant_b',
#   'lift': 0.50,  # 50% improvement
#   'confidence': 0.95
# }
```

**Behavioral Triggers:**
```python
# Create sequence with behavioral trigger
sequence = growth_automation.create_message_sequence(
    name="Post Engagement Follow-up",
    steps=[
        {"delay_days": 0, "template": "thanks_for_engagement"},
        {"delay_days": 2, "template": "follow_up"}
    ],
    trigger_type='post_engagement',  # Trigger on engagement
    description="Follow up with people who engage with posts"
)

# Triggers are automatically checked when processing messages
result = growth_automation.process_due_sequence_messages()
# Output:
# {
#   'messages_sent': 3,
#   'errors': 0,
#   'total_processed': 3,
#   'new_enrollments': 5  # 5 people auto-enrolled via triggers
# }
```

**Timezone Scheduling:**
```python
# Enroll with timezone scheduling (automatic)
connection = db.query(Connection).filter_by(location="London, UK").first()
enrollment = growth_automation.enroll_in_sequence(
    connection_id=connection.id,
    sequence_id=sequence.id
)
# Output:
# 🌍 Using timezone scheduling for London, UK
# ✓ Enrolled connection 123 in sequence 'Welcome Series'
# (First message will be sent at 9am London time)
```

---

## 3. Files Modified

### Core Integration
- `/utils/network_growth.py` - Main integration point (180 lines added)
  - Added LeadScoringEngine and MessageSequenceEngine imports
  - Updated `__init__()` to initialize both engines
  - Updated `send_connection_request()` for lead scoring
  - Updated `_generate_connection_message()` for score context
  - Updated `enroll_in_sequence()` for timezone scheduling
  - Updated `process_due_sequence_messages()` for behavioral triggers
  - Added 6 new methods for lead scoring and A/B testing

### Database Models
- `/database/models.py` - Added lead scoring fields
  - `ConnectionRequest.lead_score` (Float)
  - `ConnectionRequest.score_breakdown` (Text/JSON)
  - `ConnectionRequest.priority_tier` (String)

### New Utilities (Already Created)
- `/utils/lead_scoring.py` - 428 lines
- `/utils/message_sequence_engine.py` - 540 lines

---

## 4. Database Migration Required

To use the new lead scoring features, you need to add the new columns to the database:

```sql
-- Add lead scoring columns to connection_requests table
ALTER TABLE connection_requests ADD COLUMN lead_score FLOAT;
ALTER TABLE connection_requests ADD COLUMN score_breakdown TEXT;
ALTER TABLE connection_requests ADD COLUMN priority_tier VARCHAR(20);
```

Or use SQLAlchemy to recreate tables (for development):
```python
from database.models import Base
from database import engine

# WARNING: This drops all data! Only for development!
Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)
```

---

## 5. Next Steps

### Testing
1. Test lead scoring with real prospect data
2. Test A/B sequence creation and winner selection
3. Test behavioral triggers (profile views, engagement)
4. Test timezone scheduling with different locations

### Configuration
1. Update `config.yaml` with target companies, titles, industries
2. Set minimum lead score threshold based on your criteria
3. Enable/disable features as needed

### Monitoring
1. Track lead scores over time
2. Monitor A/B test results
3. Review behavioral trigger enrollments
4. Analyze timezone scheduling effectiveness

---

## 6. Benefits

### Lead Scoring
- **Efficiency**: Focus on high-quality prospects (40+ score)
- **Better targeting**: Prioritize based on engagement, mutuals, company
- **Personalization**: Tailor messages based on score factors
- **Data-driven**: Track which factors correlate with acceptance

### Message Sequences
- **Optimization**: A/B test different message approaches
- **Automation**: Behavioral triggers reduce manual work
- **Timing**: Timezone scheduling improves response rates
- **Intelligence**: Branching allows conditional flows

---

## 7. Configuration Example

```yaml
network_growth:
  # Connection requests
  max_requests_per_day: 10
  personalize_requests: true

  # Lead scoring
  use_lead_scoring: true
  min_lead_score: 40

  target_companies:
    - "Google"
    - "Microsoft"
    - "Amazon"
    - "Meta"

  target_titles:
    - "Engineering Manager"
    - "Product Manager"
    - "VP Engineering"
    - "Director of Engineering"

  target_industries:
    - "Computer Software"
    - "Internet"
    - "Information Technology"

  # Message sequences
  auto_enroll_new_connections: true
  use_sequence_ab_testing: true
  use_behavioral_triggers: true
  use_timezone_scheduling: true

  # Auto-accept
  auto_accept_enabled: false
  auto_accept_criteria:
    industries: ["Computer Software", "Internet"]
    title_keywords: ["Engineer", "Manager", "Developer"]
    min_mutual_connections: 2
```

---

**Integration completed successfully!**

All features are now available and ready to use. The system provides intelligent prospect scoring, automated message optimization, and behavioral targeting for maximum network growth efficiency.
