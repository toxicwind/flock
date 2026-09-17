---
name: audience-adaptive-comms
description: "Adapt stakeholder communication to the target audience (CEO, VP, Tech Lead, or Operations), adjusting detail level, language, and focus. Output tailored emails, briefings, or slide outlines. Trigger when a user asks for an executive briefing, stakeholder update, project status report for leadership, cross-team sync, or mentions writing to a VP, CEO, or tech lead."
license: MIT
---

# audience-adaptive-comms

Automatically adjusts the granularity, language, and focus of communication content based on the target audience role. Supports four common audience types—CEO, VP, Tech Lead, and Operations—covering both upward reporting and cross-functional communication scenarios.

## Workflow

### Step 1: Gather Raw Information

Ask the user for the following:

- **Communication topic**: What they're reporting or syncing on (project progress, issue escalation, decision request, results showcase, etc.)
- **Raw material**: All details the user has (can be rough notes, technical docs, data reports, chat logs, or any other format)
- **Target audience**: Who will read this (CEO / VP / Tech Lead / Operations / Other role—if the audience doesn't fit the four types above, ask the user to describe the role's function and priorities, then adapt from the closest audience strategy)
- **Communication purpose**: Status update, resource request, decision request, risk alert, or results showcase
- **Output format**: Email, meeting talking points, Slack/Teams message, slide outline, or formal document

If the user has already specified some of this in their initial request, skip the corresponding confirmation.

### Step 2: Determine Audience Profile and Adaptation Strategy

Based on the target audience, automatically apply the following adaptation strategies:

---

## Audience Adaptation Strategies

### CEO / Founder

**Key concerns**: Strategic impact, business value, key decision points, risks and opportunities

**Granularity adjustment**:
- Highest level of abstraction—keep only conclusions and decision items
- Entire briefing should fit on 1 page or within 3 minutes of verbal delivery
- Remove all technical implementation details and process descriptions
- Keep only the 1–3 most critical metrics

**Language style**:
- Use business language, not technical jargon
- "We completed the microservices migration" → "System reliability improved 40%, supporting 3x traffic growth next quarter"
- "Database query optimization" → "User experience improved—page load time reduced by 2 seconds"
- Avoid abbreviations and industry jargon unless the CEO is known to be familiar with them

**Structure template**:

# [Topic] — One-Line Conclusion

## Key Takeaway
Summarize the most important information and recommended action in 1–2 sentences.

## Key Metrics
- Metric 1: Value + trend (↑/↓ X%)
- Metric 2: Value + gap to target

## Decisions Needed / For Your Awareness (as applicable)
- Decision 1: Option A vs Option B, recommend X, one-sentence rationale
- Decision 2: ...

## Risk Alerts (if any)
- Risk description → Impact scope → Mitigation plan

---

### VP / Department Head

**Key concerns**: Department goal attainment, resource allocation, cross-team dependencies, milestone progress, team health

**Granularity adjustment**:
- Mid-to-high level abstraction—retain key process milestones and decision context
- Can drill down to specific projects or workflows, but not to code/operational level
- Include trend data and comparisons (week-over-week, vs. targets)
- Be specific about resource and staffing information

**Language style**:
- Department-common professional terminology is fine
- Emphasize goal alignment and resource efficiency
- "API refactor is 70% done" → "Core API rework is 70% complete; remaining work needs 1 additional engineer-week from backend, expected delivery next Thursday"
- Problem descriptions should include impact assessment and resource requirements

**Structure template**:

# [Topic] Status Update

## Overall Status
One paragraph summarizing current state, whether on track, and key achievements.

## Milestone Progress

| Milestone | Status | Progress | ETA | Notes |
|---|---|---|---|---|
| Milestone 1 | In Progress | 70% | MM-DD | On track |
| Milestone 2 | Delayed | 40% | MM-DD | Brief reason |

## Key Results
- Result 1: Quantified description + business impact
- Result 2: ...

## Issues & Support Needed
- **Issue 1**: Description → Impact on goals → Resources/decisions needed
- **Issue 2**: ...

## Cross-Team Dependencies
- Dependency → Item → Current status → Expected timeline

## Next Phase Plan
List 3–5 priority items with expected outcomes, ordered by priority.

---

### Tech Lead / Architect

**Key concerns**: Technical approach, architectural impact, performance metrics, tech debt, implementation risks

**Granularity adjustment**:
- Mid-to-low level abstraction—can include technical approach comparisons and architecture decisions
- Provide specific technical metrics (QPS,