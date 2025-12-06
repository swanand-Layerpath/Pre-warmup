"""Lead scoring system - analyzes pre-warm conversations and assigns Cold/Warm/Hot scores."""

import re
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


def score_lead(transcript: str) -> Dict[str, Any]:
    """
    Analyze pre-warm conversation transcript and assign lead score.

    Scoring criteria:
    - HOT (7-10 points): Clear pain point, urgent timeline, authority, budget signals
    - WARM (4-6 points): Has pain point, exploring solutions, decent timeline
    - COLD (0-3 points): Just browsing, no urgency, unclear needs

    Args:
        transcript: Full conversation transcript from pre-warm call

    Returns:
        Dict with score, category, and reasoning
    """

    score = 0
    signals = []

    transcript_lower = transcript.lower()

    # 1. URGENCY SIGNALS (0-3 points)
    urgency_score = 0

    urgent_keywords = [
        'asap', 'urgent', 'immediately', 'right now', 'this week', 'this month',
        'as soon as possible', 'quickly', 'need it now', 'deadline'
    ]
    medium_urgency = [
        'next quarter', 'q1', 'q2', 'q3', 'q4', 'few months',
        'planning to', 'soon', 'coming up'
    ]

    if any(keyword in transcript_lower for keyword in urgent_keywords):
        urgency_score = 3
        signals.append("🔥 High urgency timeline")
    elif any(keyword in transcript_lower for keyword in medium_urgency):
        urgency_score = 2
        signals.append("⏰ Medium urgency timeline")
    elif 'timeline' in transcript_lower or 'when' in transcript_lower:
        urgency_score = 1
        signals.append("📅 Has timeline awareness")

    score += urgency_score

    # 2. PAIN POINT SIGNALS (0-3 points)
    pain_score = 0

    pain_keywords = [
        'problem', 'issue', 'struggling', 'difficult', 'challenge', 'pain',
        'frustrated', 'losing', 'waste', 'inefficient', 'broken', 'failing',
        'need to fix', 'need to improve', 'need help', 'not working'
    ]
    opportunity_keywords = [
        'looking to improve', 'want to', 'trying to', 'hoping to',
        'would like to', 'exploring', 'considering'
    ]

    pain_count = sum(1 for keyword in pain_keywords if keyword in transcript_lower)

    if pain_count >= 3:
        pain_score = 3
        signals.append("💥 Strong pain point articulated")
    elif pain_count >= 1:
        pain_score = 2
        signals.append("⚠️ Clear pain point identified")
    elif any(keyword in transcript_lower for keyword in opportunity_keywords):
        pain_score = 1
        signals.append("💡 Opportunity awareness")

    score += pain_score

    # 3. AUTHORITY/DECISION MAKER (0-2 points)
    authority_score = 0

    decision_roles = [
        'founder', 'ceo', 'cto', 'vp', 'director', 'head of', 'lead',
        'owner', 'manager', 'decision maker'
    ]
    influencer_roles = [
        'team lead', 'senior', 'coordinator', 'specialist'
    ]

    if any(role in transcript_lower for role in decision_roles):
        authority_score = 2
        signals.append("👑 Decision maker role")
    elif any(role in transcript_lower for role in influencer_roles):
        authority_score = 1
        signals.append("🎯 Influencer role")

    score += authority_score

    # 4. CURRENT SOLUTION SIGNALS (0-2 points)
    solution_score = 0

    # Using competitors or manual process = good signal
    manual_indicators = [
        'manual', 'manually', 'spreadsheet', 'excel', 'google sheets',
        'doing it ourselves', 'homegrown', 'built our own'
    ]
    competitor_indicators = [
        'currently using', 'right now we', 'we have', 'we use'
    ]
    no_solution = [
        "don't have", "haven't found", "nothing really", "not using anything",
        "no tool", "no solution"
    ]

    if any(keyword in transcript_lower for keyword in no_solution):
        solution_score = 2
        signals.append("🆕 No current solution (greenfield)")
    elif any(keyword in transcript_lower for keyword in manual_indicators):
        solution_score = 2
        signals.append("📊 Manual process (ripe for automation)")
    elif any(keyword in transcript_lower for keyword in competitor_indicators):
        solution_score = 1
        signals.append("🔄 Using existing solution (replacement opportunity)")

    score += solution_score

    # 5. ENGAGEMENT QUALITY (0-2 points bonus/penalty)
    engagement_score = 0

    # Check for detailed responses (longer = more engaged)
    words = transcript.split()
    avg_response_length = len(words) / max(transcript.count('?'), 1)  # Words per question

    if avg_response_length > 30:
        engagement_score = 2
        signals.append("💬 Highly engaged (detailed responses)")
    elif avg_response_length > 15:
        engagement_score = 1
        signals.append("✅ Good engagement")
    elif avg_response_length < 5:
        engagement_score = -1
        signals.append("😐 Low engagement (short responses)")

    score += engagement_score

    # DETERMINE CATEGORY
    if score >= 7:
        category = "🔥 HOT"
        summary = "High-priority lead. Strong signals for close."
    elif score >= 4:
        category = "🌡️ WARM"
        summary = "Qualified lead. Nurture and follow up."
    else:
        category = "❄️ COLD"
        summary = "Low priority. May need more education."

    return {
        "score": score,
        "max_score": 12,
        "category": category,
        "summary": summary,
        "signals": signals,
        "breakdown": {
            "urgency": urgency_score,
            "pain_point": pain_score,
            "authority": authority_score,
            "current_solution": solution_score,
            "engagement": engagement_score
        }
    }


def extract_key_insights(transcript: str) -> Dict[str, Any]:
    """
    Extract key insights from the transcript for the founder.

    Args:
        transcript: Full conversation transcript

    Returns:
        Dict with extracted information
    """

    insights = {
        "company_description": None,
        "role": None,
        "pain_point": None,
        "current_tools": None,
        "timeline": None
    }

    # Simple extraction logic - look for patterns
    # In production, you'd use the actual chat history structure

    lines = transcript.split('\n')
    for i, line in enumerate(lines):
        line_lower = line.lower()

        # Look for company description (usually after "what does X do?")
        if 'company do' in line_lower or 'what do you do' in line_lower:
            if i + 1 < len(lines):
                insights["company_description"] = lines[i + 1].strip()

        # Look for role
        if 'role' in line_lower or 'what do you do there' in line_lower:
            if i + 1 < len(lines):
                insights["role"] = lines[i + 1].strip()

        # Look for pain point
        if 'help with' in line_lower or 'trying to solve' in line_lower or 'hoping' in line_lower:
            if i + 1 < len(lines):
                insights["pain_point"] = lines[i + 1].strip()

        # Look for tools
        if 'tools' in line_lower or 'using' in line_lower:
            if i + 1 < len(lines):
                insights["current_tools"] = lines[i + 1].strip()

        # Look for timeline
        if 'timeline' in line_lower or 'when' in line_lower or 'urgent' in line_lower:
            if i + 1 < len(lines):
                insights["timeline"] = lines[i + 1].strip()

    return insights
