"""Pure LLM intelligence - no database, no APIs, no hardcoding."""

import os
import json
import logging
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


async def analyze_prospect_smart(
    name: str,
    email: str,
    company: str,
    role: str,
    reason: str
) -> dict:
    """
    Analyze prospect using pure LLM reasoning.

    Input: Just the URL parameters from curl command
    Output: Full intelligence + conversation strategy
    """

    logger.info(f"🧠 Analyzing: {name} ({role}) at {company}")

    analysis_prompt = f"""You are an expert sales intelligence analyst. Analyze this prospect who just booked a demo.

PROSPECT DATA:
Name: {name}
Email: {email}
Company: {company}
Role: {role}
Reason for booking: {reason}

TASK: Generate complete intelligence and conversation strategy.

Return JSON with this EXACT structure:
{{
  "intelligence": {{
    "first_name": "Extract first name from full name",
    "industry": "Infer industry from company name/role (saas, ecommerce, fintech, healthcare, manufacturing, etc.)",
    "seniority": "C-Level | VP | Director | Manager | Individual Contributor",
    "is_decision_maker": true or false,
    "company_stage": "Startup | Growth | Enterprise - infer from role/company",
    "urgency_level": "High | Medium | Low - based on reason for booking",
    "pain_points_likely": [
      "Based on role and reason, what 3 specific pain points do they likely face?",
      "Be SPECIFIC to their role and industry",
      "Example: 'Low product tour completion rates' NOT 'onboarding issues'"
    ],
    "budget_signals": "Any hints about budget from role/reason? Be honest if none."
  }},

  "conversation_strategy": {{
    "opening_message": "Write a 2-3 sentence consultative opening message that:
      - Uses their first name
      - Acknowledges their company and role specifically
      - Offers 3 specific pain points they can choose from
      - Sounds natural and helpful (like the Birdeye example)
      - NO generic phrases like 'How can I help'

      Example good opening:
      'Hi Alex! Since you're CTO at ASTERX evaluating product tour platforms, I'll keep this focused.
      Most CTOs tell us they struggle with either: (1) low tour completion rates,
      (2) engineering time spent maintaining tours, or (3) lack of analytics on user behavior.
      Which one brought you here?'",

    "value_examples": [
      "When they mention pain point 1, what example should you share?",
      "When they mention pain point 2, what example should you share?",
      "When they mention pain point 3, what example should you share?"
    ],

    "embedded_qualification": [
      "2-3 questions that extract info but sound helpful, not interrogative",
      "Example: 'When you say engineering time, are we talking hours per week or more like days?' instead of 'How big is your team?'"
    ],

    "demo_focus": [
      "Based on their role and reason, what should the demo emphasize?",
      "Be specific - not 'show features' but 'show API integration speed'"
    ]
  }}
}}

IMPORTANT:
- Be SPECIFIC not generic
- Use actual phrases from their reason for booking
- Make pain points relevant to their exact role
- Opening must sound consultative, not salesy"""

    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert at analyzing prospects and creating consultative conversation strategies. Be specific and insightful."
                },
                {"role": "user", "content": analysis_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.7
        )

        analysis = json.loads(response.choices[0].message.content)

        logger.info(f"✅ Analysis complete: {analysis['intelligence']['industry']} | {analysis['intelligence']['seniority']}")

        return analysis

    except Exception as e:
        logger.error(f"❌ LLM analysis failed: {e}")
        # Fallback to basic analysis
        first_name = name.split()[0] if name else "there"
        return {
            "intelligence": {
                "first_name": first_name,
                "industry": "technology",
                "seniority": "Unknown",
                "is_decision_maker": "CTO" in role or "CEO" in role or "VP" in role,
                "company_stage": "Growth",
                "urgency_level": "Medium",
                "pain_points_likely": [
                    "Product tour engagement",
                    "User onboarding completion",
                    "Analytics and tracking"
                ],
                "budget_signals": "None detected"
            },
            "conversation_strategy": {
                "opening_message": f"Hi {first_name}! Thanks for booking time with us. Tell me a bit about what brought you here today.",
                "value_examples": [
                    "Share a relevant case study from their industry",
                    "Mention specific results other customers achieved",
                    "Provide concrete examples of solutions"
                ],
                "embedded_qualification": [
                    "When you say [their pain point], can you help me understand the scope?",
                    "Are you exploring this solo or would you involve your team?",
                    "Is this something urgent or more of a Q1 priority?"
                ],
                "demo_focus": [
                    "Show core product functionality",
                    "Demonstrate ease of use",
                    "Highlight relevant integrations"
                ]
            }
        }


def build_consultative_system_prompt(
    name: str,
    company: str,
    role: str,
    reason: str,
    analysis: dict
) -> str:
    """
    Build complete system prompt from LLM analysis.
    No hardcoding - everything from the analysis.
    """

    intel = analysis['intelligence']
    strategy = analysis['conversation_strategy']
    first_name = intel['first_name']

    # Format value examples
    value_examples_formatted = ""
    if strategy.get('value_examples'):
        value_examples_formatted = "\n".join([
            f"   • Pain point {i+1}: {example}"
            for i, example in enumerate(strategy['value_examples'])
        ])
    else:
        value_examples_formatted = "   • Share relevant examples based on their pain point"

    # Format embedded questions
    embedded_questions_formatted = ""
    if strategy.get('embedded_qualification'):
        embedded_questions_formatted = "\n".join([
            f"   • {q}"
            for q in strategy['embedded_qualification']
        ])
    else:
        embedded_questions_formatted = "   • Ask clarifying questions that sound helpful, not extractive"

    # Format demo focus
    demo_focus_formatted = ', '.join(strategy.get('demo_focus', ['key product features']))

    prompt = f"""You are a helpful pre-call assistant having a quick conversation with {first_name} from {company}.

CONTEXT ABOUT {first_name.upper()}:
• Company: {company} ({intel['industry']} industry)
• Role: {role} ({intel['seniority']} level)
• Decision maker: {"YES" if intel['is_decision_maker'] else "Likely needs approval"}
• Company stage: {intel['company_stage']}
• Why they booked: {reason}
• Urgency: {intel['urgency_level']}

---

YOUR OPENING MESSAGE (USE THIS EXACT MESSAGE):

{strategy['opening_message']}

Wait for them to choose which pain point resonates most.

---

CONVERSATION FRAMEWORK:

🎯 PHASE 1: LET THEM CHOOSE THEIR PAIN
After your opening, they'll tell you which of the 3 pain points resonates.

Listen carefully and acknowledge:
"Got it - [repeat their choice]. Yeah, I hear that a lot from {role}s."

Then give value BEFORE asking more:
{value_examples_formatted}

🎯 PHASE 2: DIG DEEPER (BUT NATURALLY)
After giving value, embed qualification questions naturally:

{embedded_questions_formatted}

The rule: Make every question sound like you're trying to HELP them, not extract data for yourself.

🎯 PHASE 3: MAP TO DEMO
As you learn about their situation, mention what you'll focus on:

Based on their role/pain: {demo_focus_formatted}

Example: "Got it, so {intel['pain_points_likely'][0] if intel.get('pain_points_likely') else 'that issue'}. We can definitely show you how
[specific solution] works on the demo. Most {role}s find that super helpful."

🎯 PHASE 4: WRAP UP
After 3-5 exchanges:

"This was really helpful {first_name}! I've got a much better sense of what to focus on
when we meet. I'll make sure to emphasize [what they care about most]. Looking forward to it!"

---

CONVERSATION RULES:

✅ CONSULTATIVE (Give value, don't interrogate)
Example flow:
- Them: "We struggle with tour completion"
- You: "Yeah, most teams see 20-30% completion. One {intel['industry']} company used [approach]
       and went to 75%. Sound like what you need?" [VALUE FIRST]
- Them: "Yes exactly"
- You: "Got it. When you say completion, are we talking full product tour or specific features?
       Just want to make sure I understand the scope." [THEN QUALIFY]

❌ INTERROGATIVE (Don't do this)
- "Tell me about your challenges"
- "What's your budget?"
- "Who's the decision maker?"
- "What's your timeline?"

✅ EMBEDDED QUALIFICATION (Sound helpful)
- "Are you working with a budget already, or still in the 'is this worth it' phase?"
- "Would you evaluate this solo, or bring in your team?"
- "Is this urgent-urgent, or more of a Q1 thing?"

❌ EXPLICIT EXTRACTION (Don't do this)
- "How many people on your team?"
- "What tools do you currently use?"
- "When do you need to make a decision?"

---

TONE & STYLE:

• Keep responses SHORT (2-3 sentences max)
• Use natural filler: "you know", "like", "basically", "got it"
• React naturally: "Oh interesting!", "Makes sense", "Yeah I hear that"
• Sound like a helpful consultant, not a salesperson
• Mirror their language (if they say "activation" use "activation", not "onboarding")

---

MUST EXTRACT NATURALLY (not as a checklist):

1. Main pain point → What's actually broken/frustrating?
2. Current approach → What are they using/doing today?
3. Timeline → When does this matter? Any deadline?
4. Team involvement → Who else cares about this?
5. Success criteria → What would make this a win?

Extract these through CONVERSATION, not by asking each one directly.

---

REMEMBER:
- This is prep for the real demo scheduled later
- Your job: Make them feel HELPED, while gathering context for the sales rep
- Balance: Genuinely helpful + strategically extracting qualification data
"""

    return prompt
