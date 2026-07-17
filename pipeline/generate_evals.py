#!/usr/bin/env python3
"""
Generate eval tasks from a SKILL.md file.

Parses the skill's frontmatter and body to extract domain, key behaviors,
and output format, then generates domain-specific eval tasks using
built-in templates. No API calls required.

Usage:
  python generate_evals.py --skill-path <path> --output-dir <dir> [--num-tasks 10]
"""

import argparse
import json
import os
import re
import random
import hashlib
from pathlib import Path
from datetime import datetime


# =============================================================================
# Domain Detection
# =============================================================================

DOMAIN_KEYWORDS = {
    "marketing": [
        "landing page", "homepage", "conversion", "cro", "cta", "headline",
        "social proof", "testimonial", "pricing page", "feature page",
        "email capture", "lead", "funnel", "a/b test", "optimization",
        "marketing", "copywriting", "ad copy", "value proposition",
        "above the fold", "bounce rate", "signup", "onboarding",
    ],
    "cold_outreach": [
        "cold email", "outreach", "prospecting", "follow-up", "sequence",
        "subject line", "personalization", "reply rate", "breakup email",
        "sales email", "sdr", "b2b", "prospect", "pipeline",
    ],
    "coding": [
        "code review", "debugging", "refactoring", "testing", "api",
        "database", "migration", "deployment", "ci/cd", "docker",
        "typescript", "python", "react", "nextjs", "sql", "git",
        "pull request", "code quality", "linting", "type safety",
    ],
    "writing": [
        "blog", "article", "essay", "documentation", "report",
        "whitepaper", "case study", "technical writing", "content",
        "editing", "proofreading", "style guide", "grammar",
    ],
    "design": [
        "ui/ux", "wireframe", "mockup", "prototype", "layout",
        "typography", "color palette", "design system", "component",
        "accessibility", "responsive", "navigation", "visual hierarchy",
    ],
}


def detect_domain(skill_name: str, description: str, body: str) -> str:
    """Detect the primary domain of a skill from its name, description, and body."""
    text = f"{skill_name} {description} {body}".lower()

    scores = {}
    for domain, keywords in DOMAIN_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text)
        scores[domain] = score

    if not scores or max(scores.values()) == 0:
        return "marketing"  # default

    return max(scores, key=scores.get)


# =============================================================================
# Skill Parsing
# =============================================================================

def parse_frontmatter(content: str) -> dict:
    """Extract YAML frontmatter from SKILL.md content."""
    match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
    if not match:
        return {}

    fm_text = match.group(1)
    result = {}
    for line in fm_text.strip().split('\n'):
        line = line.strip()
        if ':' in line:
            key, _, value = line.partition(':')
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and value:
                result[key] = value
    return result


def extract_key_behaviors(body: str) -> list[str]:
    """Extract key behaviors/skills from the SKILL.md body."""
    behaviors = []

    # Look for section headers that describe behaviors
    headers = re.findall(r'^#{1,3}\s+(.+)$', body, re.MULTILINE)
    for h in headers:
        h_lower = h.lower().strip()
        # Skip generic headers
        if h_lower in ('overview', 'introduction', 'related skills', 'prerequisites',
                       'table of contents', 'references', 'quick reference'):
            continue
        behaviors.append(h.strip())

    # Look for "should" / "must" / "always" / "never" patterns (skill rules)
    rules = re.findall(r'(?:should|must|always|never|do not|avoid)\s+(.{10,80})', body, re.IGNORECASE)
    for rule in rules[:10]:
        cleaned = rule.strip().rstrip('.')
        if cleaned and len(cleaned) > 10:
            behaviors.append(cleaned)

    return behaviors[:20]


def extract_output_format(body: str) -> str:
    """Detect the expected output format from the skill body."""
    body_lower = body.lower()

    if 'output format' in body_lower or '## output' in body_lower:
        # Extract the section
        match = re.search(r'##\s*(?:output format|output)\s*\n(.*?)(?=\n##|\Z)', body, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()[:500]

    if 'quick wins' in body_lower and 'high-impact' in body_lower:
        return "CRO format: Quick Wins, High-Impact Changes, Test Ideas, Copy Alternatives"
    if 'page copy' in body_lower and 'annotations' in body_lower:
        return "Copywriting format: Page Copy, Annotations, Alternatives"
    if 'subject line' in body_lower and 'follow-up' in body_lower:
        return "Cold email format: Subject line, body, CTA"

    return "Markdown response with structured sections"


def parse_skill(skill_path: str) -> dict:
    """Parse a SKILL.md file and extract metadata."""
    path = Path(skill_path)
    if not path.exists():
        raise FileNotFoundError(f"SKILL.md not found: {skill_path}")

    content = path.read_text(encoding='utf-8')
    frontmatter = parse_frontmatter(content)

    # Extract body (everything after frontmatter)
    body_match = re.match(r'^---\s*\n.*?\n---\s*\n', content, re.DOTALL)
    body = content[body_match.end():] if body_match else content

    name = frontmatter.get('name', path.stem)
    description = frontmatter.get('description', '')
    domain = detect_domain(name, description, body)
    key_behaviors = extract_key_behaviors(body)
    output_format = extract_output_format(body)

    return {
        "name": name,
        "description": description,
        "domain": domain,
        "key_behaviors": key_behaviors,
        "output_format": output_format,
        "body_length": len(body),
    }


# =============================================================================
# Task Templates by Domain
# =============================================================================

COMPANY_NAMES = [
    "FlowBoard", "DataPulse", "NestHub", "CloudScale", "TaskPilot",
    "SecureVault", "GreenLeaf", "Brightwave", "MindfulApp", "WriteRight",
    "FitTrack Pro", "MealPrep AI", "DesignFlow", "CodeBridge", "PetPal",
    "TeamCollab", "CloudHost", "SonicPure", "RouteOptima", "HireFlow",
    "MediaFlow", "StyleHub", "HealthBridge", "WorkNest", "PaySecure",
    "StreamTech", "NimbusCRM", "RecruitPro", "FastFreight", "GrowthStack",
    "FreshBooks Cloud", "DataDash", "AdOptimize", "KubeEasy", "TalentSync",
    "FinScale", "GreenLeaf Logistics", "CloudDeploy", "TeamSync", "SonicPure X1",
]

INDUSTRIES = [
    "B2B SaaS", "e-commerce", "health tech", "fintech", "logistics",
    "marketing agency", "developer tools", "HR tech", "edtech", "legal tech",
    "real estate", "fitness", "food & beverage", "travel", "media",
    "non-profit", "consulting", "manufacturing", "retail", "insurance",
]

AUDIENCES = [
    "marketing managers", "CTOs", "VPs of Engineering", "product managers",
    "small business owners", "freelancers", "enterprise buyers", "developers",
    "sales teams", "HR directors", "founders", "operations managers",
    "content creators", "e-commerce store owners", "agency owners",
]

TRAFFIC_SOURCES = [
    "Google Ads", "Facebook ads", "LinkedIn ads", "organic search",
    "email campaigns", "referral partners", "Instagram ads", "Twitter ads",
    "content marketing", "word of mouth", "podcast appearances",
]


# --- Marketing Templates ---

MARKETING_TASK_TEMPLATES = [
    {
        "type": "landing_page_cro",
        "prompt": "Analyze this SaaS landing page for conversion optimization. The page is for {company} - {industry_description}. Hero headline: '{company} - {generic_headline}'. CTA button: '{weak_cta}'. The page has a features section listing {feature_count} features, {trust_signals}, and a {form_fields}-field contact form. Traffic comes from {traffic_source}.",
        "criteria templates": [
            "Output contains a 'Quick Wins' section",
            "Output contains a 'High-Impact Changes' section",
            "Output contains a 'Test Ideas' section",
            "Identifies the headline as too vague/generic",
            "Recommends a stronger headline alternative",
            "Identifies the CTA as weak and suggests a stronger alternative",
            "Provides at least 2 CTA copy alternatives",
            "Notes the absence of trust signals or recommends improving them",
            "Recommends specific changes to reduce form friction",
        ],
    },
    {
        "type": "pricing_page",
        "prompt": "Perform a CRO audit on this pricing page for {company} - {industry_description}. The page shows 3 tiers: Starter ({price1}), Professional ({price2}), Enterprise ({price3}). {plan_details} There is no FAQ about plan differences, no toggle for monthly vs annual pricing, and no money-back guarantee. Traffic is mostly {traffic_source}.",
        "criteria templates": [
            "Output follows the Quick Wins / High-Impact Changes / Test Ideas structure",
            "Identifies that the page lacks guidance on 'which plan is right for me'",
            "Recommends adding plan descriptions or use-case matching",
            "Notes the absence of annual pricing toggle",
            "Identifies the CTA as generic and provides alternatives",
            "Recommends adding a guarantee or risk reversal",
            "Suggests adding social proof near pricing",
            "Provides at least 2 CTA alternatives",
            "Recommends adding an FAQ section",
            "At least one test idea targets the pricing layout",
        ],
    },
    {
        "type": "homepage",
        "prompt": "Evaluate this B2B SaaS homepage for {company} - {industry_description}. Current page: Hero headline: '{company}: {professional_headline}'. Subheadline: '{vague_subheadline}'. CTA: '{weak_cta}'. Below the fold: a paragraph about the company's founding, a team photo, and a 'Contact Us' form. No pricing info, no product screenshots, no customer logos. Traffic comes from {traffic_source}.",
        "criteria templates": [
            "Output follows the 4-section CRO format",
            "Identifies '{weak_cta}' as a weak CTA and suggests alternatives",
            "Notes the homepage leads with company story instead of visitor value",
            "Recommends adding product screenshots or a demo video",
            "Flags the absence of social proof",
            "Suggests adding a clear value proposition",
            "Recommends adding pricing or a 'See Pricing' CTA",
            "Provides at least 2 alternative headlines",
            "Notes that 'Contact Us' is high-friction for cold visitors",
            "At least one recommendation addresses the traffic source",
        ],
    },
    {
        "type": "blog_cro",
        "prompt": "Review this blog post page for {company} - {industry_description}. The blog post is titled '{blog_title}'. At the very bottom of the post, there is a single CTA: '{generic_cta}'. No inline CTAs, no content upgrades, no email capture. Traffic comes from {traffic_source}.",
        "criteria templates": [
            "Output follows the Quick Wins / High-Impact Changes / Test Ideas structure",
            "Identifies that a single bottom-of-post CTA misses multiple stopping points",
            "Recommends adding inline CTAs at natural content breaks",
            "Suggests a content-specific lead magnet",
            "Notes the generic CTA and suggests making it topic-relevant",
            "Recommends a contextual CTA matching the blog topic",
            "Provides at least 2 alternative CTA copy options",
            "Suggests adding a 'Related Posts' section",
            "At least one recommendation addresses non-ready visitors",
            "CTA alternatives avoid weak patterns like 'Learn More'",
        ],
    },
    {
        "type": "paid_landing_page",
        "prompt": "Analyze this landing page used for paid ads. The page is for {company} - {industry_description}. The ad promises '{ad_hook}'. The landing page headline: '{weak_headline}'. Subheadline: '{vague_subheadline}'. The page has: features list, app download buttons, and a footer. No testimonials, no proof for the ad's claim. Navigation bar is present with 5+ links.",
        "criteria templates": [
            "Output follows the 4-section CRO format",
            "Identifies message mismatch between the ad and the landing page headline",
            "Recommends headline that mirrors the ad's promise",
            "Notes the navigation bar undermines single-page focus for paid traffic",
            "Recommends removing or simplifying navigation",
            "Flags absence of proof for the ad's claim",
            "Identifies the headline as weak/company-centric",
            "Provides at least 2 alternative headlines",
            "Recommends adding a risk reversal",
            "At least one test addresses message match or navigation",
        ],
    },
    {
        "type": "signup_flow",
        "prompt": "Review this signup flow for {company} - {industry_description}. The signup page has: headline 'Create Your Account', a form with fields: Email, Password, Confirm Password, Full Name, Job Title, Company Name, Company Size, Industry, How did you hear about us, Terms checkbox. There is a 'Create Account' button. No social proof, no mention of free trial. Traffic comes from {traffic_source}.",
        "criteria templates": [
            "Output follows the 4-section CRO format",
            "Identifies the form has too many fields for a signup flow",
            "Recommends reducing to essential fields",
            "Notes the headline is functional but not motivating",
            "Recommends adding a benefit-oriented headline",
            "Identifies the absence of social proof near the form",
            "Recommends adding a free trial mention",
            "Provides at least 2 alternative CTA buttons",
            "Suggests splitting into multi-step form if fields are required",
            "At least one recommendation addresses perceived commitment",
        ],
    },
    {
        "type": "feature_page",
        "prompt": "Perform CRO analysis on this feature page for {company} - {industry_description}. The page is for the '{feature_name}' feature. Headline: '{feature_name} Feature'. Body: a paragraph explaining how it works technically. A screenshot. A '{cta}' CTA button. No benefit explanation, no use cases, no before/after examples, no testimonials. Traffic comes from {traffic_source}.",
        "criteria templates": [
            "Output follows the 4-section CRO format",
            "Identifies that the headline is feature-named rather than benefit-oriented",
            "Recommends rewriting headline to connect feature to customer outcome",
            "Notes the technical language is inappropriate for the audience",
            "Recommends replacing technical explanation with benefit language",
            "Suggests adding before/after examples",
            "Recommends use cases",
            "Provides at least 2 alternative headlines",
            "Notes the page lacks a clear path to try or buy beyond the single CTA",
            "At least one recommendation makes the feature tangible through examples",
        ],
    },
    {
        "type": "about_page",
        "prompt": "Evaluate this about page for {company} - {industry_description}. The page has: headline 'About {company}', a paragraph about the company's mission to '{vague_mission}', a timeline of milestones, team photos with names and titles, and a 'Contact Us' CTA at the bottom. No client testimonials, no performance data, no differentiator section. Traffic comes from {traffic_source}.",
        "criteria templates": [
            "Output follows the 4-section CRO format",
            "Identifies that the page tells company facts but doesn't connect mission to client benefit",
            "Recommends leading with client outcomes instead of company milestones",
            "Notes absence of proof points",
            "Recommends adding a differentiator section",
            "Identifies that 'Contact Us' is high-friction for an about page",
            "Recommends a softer CTA or next step",
            "Provides at least 2 alternative headlines",
            "Suggests adding client logos or credentials for trust",
            "At least one recommendation addresses the referral context",
        ],
    },
    {
        "type": "lead_capture",
        "prompt": "Analyze this lead capture form page for {company} - {industry_description}. The page has: headline '{strong_headline}', a form with {form_fields} fields, and a '{cta}' CTA button. Trust signals: {trust_signals}. Traffic comes from {traffic_source}.",
        "criteria templates": [
            "Output follows the 4-section CRO format",
            "Evaluates the headline strengths and weaknesses",
            "Notes the form friction level",
            "Recommends adding more social proof",
            "Suggests adding a preview of what they get after submitting",
            "Recommends adding a guarantee or risk reversal",
            "Provides at least 2 test ideas specific to this form",
            "At least one copy alternative for the CTA",
            "Recommends addressing the 'what happens after I submit?' question",
            "Notes how well the page handles the traffic source context",
        ],
    },
    {
        "type": "ecommerce_product",
        "prompt": "Perform a CRO audit on this e-commerce product page for {company} - a {product_type}. The page has: headline '{company} - {generic_headline}', a product image gallery, a features section with {feature_count} technical specs, price {price} with a '{cta}' button, and a reviews section showing {rating} stars from {review_count} reviews but no written testimonials. No competitor comparison, no FAQ, no money-back guarantee. Traffic comes from {traffic_source}.",
        "criteria templates": [
            "Output follows the 4-section CRO format",
            "Identifies that the headline is feature-oriented rather than benefit-oriented",
            "Recommends connecting features to customer outcomes",
            "Notes absence of a guarantee or risk reversal near the CTA",
            "Recommends surfacing written testimonials from reviews",
            "Suggests adding a comparison section",
            "Provides alternative headline(s) that are outcome-focused",
            "Identifies that too many specs may overwhelm non-technical buyers",
            "Recommends FAQ section to handle objections",
            "At least one recommendation addresses pricing anxiety",
        ],
    },
    {
        "type": "email_capture",
        "prompt": "Write email capture section copy for the blog of {company} - {industry_description}. The blog publishes articles about {topic}. The email capture appears at the bottom of every blog post. Current copy: 'Subscribe to our newsletter for updates.' Target audience: {audience}.",
        "criteria templates": [
            "Headline for the email capture section is specific",
            "Copy communicates what subscribers get",
            "Specific content examples are mentioned",
            "CTA communicates the value of subscribing",
            "Copy addresses 'what's in it for me?'",
            "At least 2 alternative headlines/CTAs are provided",
            "Copy is concise",
            "No exclamation points",
            "Annotations explain why the chosen approach works",
            "Copy avoids generic promises",
        ],
    },
    {
        "type": "hero_section",
        "prompt": "Write hero section copy for {company} - {industry_description}. Product: {product_description}. Key differentiator: {differentiator}. Target audience: {audience}. Voice: {voice}.",
        "criteria templates": [
            "Output contains Headline, Subheadline, CTA, and at least 2 headline alternatives",
            "Headline addresses the audience's pain or desired outcome",
            "Copy communicates the differentiator without jargon",
            "Subheadline adds specificity",
            "CTA communicates the outcome",
            "Copy uses customer language",
            "At least one headline alternative uses a proven formula",
            "No exclamation points",
            "Active voice used throughout",
            "Annotations explain the approach chosen",
        ],
    },
    {
        "type": "page_copy_rewrite",
        "prompt": "Rewrite this page copy for {company} - {industry_description}. Current headline: '{bad_headline}'. Current body: '{bad_body}'. Target audience: {audience}. Voice: {voice}.",
        "criteria templates": [
            "Rewritten headline replaces jargon with clear benefit language",
            "Body copy uses simple words",
            "No marketing buzzwords remain",
            "Copy connects features to specific customer outcomes",
            "Active voice is used throughout",
            "Copy includes a specific proof point or example",
            "Output includes annotations explaining changes",
            "At least 2 headline alternatives are provided",
            "CTA is specific and value-oriented",
            "Rewrite passes the 'read it aloud' test",
        ],
    },
    {
        "type": "cta_audit",
        "prompt": "Write CTA copy for a {page_count}-page website for {company} - {industry_description}. The site needs CTAs for: {page_list}. Product: {product_description}. Target: {audience}. Voice: {voice}.",
        "criteria templates": [
            "All {page_count} CTAs are provided and each is unique",
            "No CTA uses weak patterns",
            "Each CTA follows the [Action Verb] + [What They Get] formula",
            "CTAs are context-appropriate for each page",
            "CTAs match the specified voice",
            "At least one CTA includes a qualifier",
            "No exclamation points in any CTA",
            "CTAs are short (under 6 words each)",
            "Homepage hero CTA is the strongest",
            "Annotations explain why each CTA was chosen",
        ],
    },
    {
        "type": "feature_launch",
        "prompt": "Write landing page copy for a new feature launch: '{feature_name}' in {company} - {industry_description}. The feature {feature_benefit}. Target audience: {audience}. Voice: {voice}.",
        "criteria templates": [
            "Output contains Page Copy, Annotations, and Alternatives sections",
            "Headline communicates the outcome, not just the feature name",
            "Copy addresses the specific pain",
            "Feature is connected to benefit and outcome chain",
            "Copy differentiates from the current approach",
            "CTA communicates what they get",
            "Subheadline adds a specific detail",
            "Copy uses 'you/your' more than 'we/our'",
            "At least one section uses a before/after comparison",
            "No exclamation points in body copy",
        ],
    },
]

# --- Cold Outreach Templates ---

COLD_OUTREACH_TASK_TEMPLATES = [
    {
        "type": "cold_email_single",
        "prompt": "Write a cold email to {prospect_name}, {prospect_role} at {company} ({company_description}). You're selling {product_name} - {product_description}. Value prop: {value_prop}. Proof: {proof_point}. Goal: {goal}.",
        "criteria templates": [
            "Subject line is 2-4 words, lowercase, no punctuation tricks",
            "Subject line does NOT contain the prospect's first name or product name",
            "Email opens with an observation about {company}",
            "Email uses 'you/your' more than 'I/we'",
            "Personalization connects to the problem",
            "Specific proof point is included",
            "Single CTA that is interest-based",
            "No 30-minute meeting request",
            "Email is under {word_limit} words",
            "No jargon: 'synergy', 'leverage', 'best-in-class' are absent",
            "No feature dump",
        ],
    },
    {
        "type": "cold_email_followup",
        "prompt": "Write a {email_count}-email follow-up sequence for cold outreach to {prospect_name}, {prospect_role} at {company} ({company_description}). You're selling {product_name} - {product_description}. Email 1 was sent {days_since} days ago. Goal: {goal}.",
        "criteria templates": [
            "Each email stands alone",
            "Each email adds a new angle or piece of proof",
            "None of the emails open with 'Just following up' or 'Just checking in'",
            "Subject lines are different across all emails",
            "Each email has one clear, low-friction CTA",
            "Last email acknowledges it's the final touch",
            "No email asks for a 30-minute meeting",
            "Each email is under {word_limit} words",
            "All emails use contractions and sound human",
            "No email contains AI phrases",
        ],
    },
    {
        "type": "cold_email_trigger",
        "prompt": "Write a cold email to {prospect_name}, {prospect_role} at {company}. The company recently {trigger_event}. You're selling {product_name} - {product_description}. Value prop: {value_prop}. Proof: {proof_point}. Goal: {goal}.",
        "criteria templates": [
            "Subject line is 2-4 words, lowercase",
            "Opening connects the trigger event to the ongoing challenge",
            "Email leads with their world",
            "One specific proof point is included",
            "CTA is interest-based",
            "Email uses 'you/your' predominantly",
            "Email is under {word_limit} words",
            "No feature dump",
            "Voice sounds like a peer who understands their industry",
            "No fake urgency",
        ],
    },
    {
        "type": "cold_email_csuite",
        "prompt": "Write a cold email to {prospect_name}, {prospect_role} at {company} ({company_description}). You're selling {product_name}. Value prop: {value_prop}. Proof: {proof_point}. Goal: {goal}. Note: C-suite so ultra-brief and peer-level.",
        "criteria templates": [
            "Subject line is 2-4 words, lowercase",
            "Email is ultra-brief (under {word_limit} words)",
            "Opening is direct and peer-level",
            "Value is communicated in terms they care about",
            "One proof point that speaks to business outcomes",
            "CTA is extremely low-friction",
            "No technical jargon",
            "Uses contractions",
            "Sounds like a peer, not a vendor",
            "No more than 5 sentences total",
        ],
    },
]


# =============================================================================
# Task Generation
# =============================================================================

def generate_task_id(skill_name: str, index: int) -> str:
    """Generate a task ID like 'cro_001'."""
    # Split on hyphens first (e.g., "cold-email" -> "cold")
    parts = skill_name.lower().split('-')
    if len(parts) > 1:
        prefix = re.sub(r'[^a-z]', '', parts[0])[:8]
    else:
        # For single-word names, use common abbreviations
        name_lower = skill_name.lower()
        abbreviations = {
            "copywriting": "copy",
            "marketing": "mktg",
            "advertising": "ads",
            "analytics": "anal",
            "automation": "auto",
            "optimization": "opt",
            "conversion": "conv",
            "deployment": "deploy",
        }
        prefix = abbreviations.get(name_lower, re.sub(r'[^a-z]', '', name_lower)[:5])
    return f"{prefix}_{index:03d}"


def fill_template(template: str, company: str, **kwargs) -> str:
    """Fill a template string with randomized specifics."""
    result = template

    # Company-specific fills
    result = result.replace("{company}", company)

    # Generic fills with defaults
    defaults = {
        "{industry_description}": kwargs.get("industry", "B2B SaaS"),
        "{generic_headline}": random.choice([
            "The Best Way to Manage Your Work",
            "Built for Modern Teams",
            "Simple. Powerful. Fast.",
            "Your All-in-One Solution",
        ]),
        "{professional_headline}": random.choice([
            "Advanced Analytics for Modern Commerce",
            "Intelligent Platform for Growing Teams",
            "Enterprise-Grade Infrastructure, Startup Speed",
        ]),
        "{vague_subheadline}": random.choice([
            "We help businesses make better decisions with our powerful platform.",
            "The best way to manage your workflow.",
            "Built for teams who demand more.",
        ]),
        "{weak_cta}": random.choice(["Sign Up", "Learn More", "Get Started", "Submit", "Contact Us"]),
        "{cta}": random.choice(["Try It Now", "Get Started", "Learn More", "Sign Up"]),
        "{weak_headline}": random.choice([
            f"Welcome to {company}",
            f"{company} - Features",
            f"About {company}",
        ]),
        "{bad_headline}": random.choice([
            f"{company} Leverages Advanced AI to Optimize Your Workflow",
            f"Cutting-Edge {company} Platform",
            f"{company}: Next-Generation Solutions",
        ]),
        "{bad_body}": random.choice([
            f"Our cutting-edge machine learning algorithms analyze your patterns and utilize predictive analytics to streamline your productivity pipeline.",
            f"We leverage innovative technology to revolutionize how your team collaborates and facilitates seamless workflow optimization.",
        ]),
        "{feature_count}": str(random.choice([5, 6, 8, 10, 12])),
        "{form_fields}": str(random.choice([4, 6, 8, 10, 12])),
        "{trust_signals}": random.choice([
            "no testimonials, no customer logos, no case studies",
            "3 customer logos and a star rating",
            "a testimonials section with 2 quotes",
        ]),
        "{price1}": random.choice(["$9/mo", "$19/mo", "$29/mo"]),
        "{price2}": random.choice(["$29/mo", "$49/mo", "$79/mo"]),
        "{price3}": random.choice(["$99/mo", "$149/mo", "Custom"]),
        "{price}": random.choice(["$49", "$99", "$199", "$299"]),
        "{rating}": str(random.choice([3.8, 4.0, 4.2, 4.5])),
        "{review_count}": str(random.choice([23, 47, 87, 156, 312])),
        "{plan_details}": random.choice([
            "The Professional plan has a 'Recommended' badge.",
            "All plans list features as bullet points.",
            "No explanation of what each plan is best for.",
        ]),
        "{traffic_source}": random.choice(TRAFFIC_SOURCES),
        "{blog_title}": random.choice([
            "10 Science-Backed Benefits of Daily Habits",
            "How to Improve Your Productivity by 50%",
            "The Complete Guide to Getting Started",
        ]),
        "{generic_cta}": random.choice([
            "Download Our App - Available on iOS and Android",
            "Subscribe to Our Newsletter",
            "Learn More About Our Product",
        ]),
        "{ad_hook}": random.choice([
            "Save 10 hours per week with automated workflows",
            "Cut your costs by 30% in 60 days",
            "Join 10,000+ teams already using our platform",
        ]),
        "{feature_name}": random.choice([
            "Grammar Check", "Auto-Report", "Smart Search", "Team Sync",
            "Budget Tracker", "AI Assistant", "Analytics Dashboard",
        ]),
        "{vague_mission}": random.choice([
            "provide innovative solutions for modern businesses",
            "democratize access to powerful tools",
            "help teams work more efficiently",
        ]),
        "{audience}": random.choice(AUDIENCES),
        "{voice}": random.choice([
            "friendly and accessible, not technical",
            "professional but approachable",
            "confident, straightforward, no fear-mongering",
            "warm, reassuring, trustworthy",
        ]),
        "{product_type}": random.choice([
            "wireless noise-canceling headphone",
            "smart home device",
            "fitness tracker",
            "project management tool",
        ]),
        "{differentiator}": random.choice([
            "Works with 500+ devices from any brand",
            "All team members are verified with background checks",
            "AI-powered analytics that learn from your data",
            "Setup takes 5 minutes, not 5 hours",
        ]),
        "{product_description}": random.choice([
            "A smart home hub that connects all your devices",
            "An AI meal planning app",
            "A collaborative design tool for marketing teams",
            "An encrypted password manager for small businesses",
        ]),
        "{topic}": random.choice([
            "SEO, paid ads, and content marketing",
            "productivity and time management",
            "remote team collaboration",
            "data analytics and business intelligence",
        ]),
        "{page_count}": str(random.choice([5, 7, 9])),
        "{page_list}": "Homepage, Features, Pricing, About, Blog, Contact",
        "{feature_benefit}": random.choice([
            "automatically generates weekly reports with AI insights",
            "reduces deployment time from hours to minutes",
            "provides real-time collaboration for distributed teams",
        ]),
        "{product_name}": random.choice([
            "CloudDeploy", "DataPulse", "TeamSync", "SecureStack",
            "KubeEasy", "HireFlow", "AdOptimize", "RouteOptima",
        ]),
        "{value_prop}": random.choice([
            "They're likely running multiple tools and lack a unified view",
            "Their current process is manual and time-consuming",
            "They're scaling fast and infrastructure is becoming a bottleneck",
        ]),
        "{proof_point}": random.choice([
            "Helped a similar company reduce costs by 30% in Q1",
            "Improved efficiency by 40% for a 200-person team",
            "Cut deployment time from 2 hours to 12 minutes",
        ]),
        "{goal}": random.choice([
            "Get a 15-minute intro call",
            "Get a reply expressing interest",
            "Get a reply (not a meeting)",
        ]),
        "{prospect_name}": random.choice([
            "Sarah Chen", "Marcus Rodriguez", "Priya Patel",
            "James Liu", "Elena Vasquez", "David Park",
        ]),
        "{prospect_role}": random.choice([
            "VP of Marketing", "CTO", "Head of People",
            "VP of Engineering", "Marketing Director", "CEO",
        ]),
        "{company_description}": random.choice([
            "a 200-person B2B SaaS company",
            "a 50-person health tech startup",
            "a 120-person remote-first company",
            "a 300-person fintech company",
        ]),
        "{trigger_event}": random.choice([
            "raised $40M Series C",
            "was featured in TechCrunch",
            "posted about Kubernetes challenges on LinkedIn",
            "achieved SOC 2 compliance",
        ]),
        "{word_limit}": str(random.choice([80, 100, 120, 130, 150])),
        "{email_count}": str(random.choice([3, 4, 5])),
        "{days_since}": str(random.choice([3, 5, 7])),
    }

    for placeholder, value in defaults.items():
        if placeholder in result:
            result = result.replace(placeholder, value)

    return result


def fill_criteria(templates: list[str], company: str, **kwargs) -> list[str]:
    """Fill criteria templates with actual values."""
    # Default values for common placeholders in criteria
    defaults = {
        "{company}": company,
        "{weak_cta}": "Sign Up",
        "{page_count}": "7",
        "{word_limit}": "150",
        "{email_count}": "3",
    }
    defaults.update(kwargs)

    criteria = []
    for template in templates:
        criterion = template
        for placeholder, value in defaults.items():
            criterion = criterion.replace(placeholder, str(value))
        criteria.append(criterion)
    return criteria


def generate_tasks_for_skill(skill: dict, num_tasks: int = 10) -> dict:
    """Generate eval tasks for a parsed skill."""
    domain = skill["domain"]
    name = skill["name"]

    # Select templates based on domain
    if domain == "cold_outreach":
        templates = COLD_OUTREACH_TASK_TEMPLATES
    else:
        templates = MARKETING_TASK_TEMPLATES

    # Shuffle and select - cycle through templates if we need more than available
    random.seed(hashlib.md5(name.encode()).hexdigest())  # deterministic per skill
    available = templates.copy()
    random.shuffle(available)

    # Cycle through templates to fill num_tasks
    selected = []
    while len(selected) < num_tasks:
        for t in available:
            if len(selected) >= num_tasks:
                break
            selected.append(t)
        if len(selected) >= num_tasks:
            break
        # Re-shuffle for next cycle to add variety
        random.shuffle(available)

    tasks = []
    used_companies = set()

    for i, template_info in enumerate(selected[:num_tasks]):
        task_id = generate_task_id(name, i + 1)

        # Pick a unique company name
        company = random.choice(COMPANY_NAMES)
        attempts = 0
        while company in used_companies and attempts < 20:
            company = random.choice(COMPANY_NAMES)
            attempts += 1
        used_companies.add(company)

        industry = random.choice(INDUSTRIES)

        # Fill the prompt
        prompt = fill_template(
            template_info["prompt"],
            company=company,
            industry=industry,
        )

        # Fill the criteria
        criteria = fill_criteria(
            template_info["criteria templates"],
            company=company,
        )

        # Generate scoring rubric
        rubric = {
            "pass": f"All output sections present, specific issues identified for {company}, actionable recommendations with rationale",
            "fail": "Missing required output sections, or recommendations are generic without tying to the specific scenario",
        }

        tasks.append({
            "id": task_id,
            "skill": name,
            "prompt": prompt,
            "verification_criteria": criteria,
            "scoring_rubric": rubric,
        })

    return {
        "skill_name": name,
        "generated_at": datetime.now().isoformat(),
        "domain": domain,
        "task_count": len(tasks),
        "tasks": tasks,
    }


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Generate eval tasks from a SKILL.md file"
    )
    parser.add_argument(
        "--skill-path", required=True,
        help="Path to the SKILL.md file"
    )
    parser.add_argument(
        "--output-dir", required=True,
        help="Output directory for tasks.json"
    )
    parser.add_argument(
        "--num-tasks", type=int, default=10,
        help="Number of tasks to generate (default: 10)"
    )

    args = parser.parse_args()

    # Parse the skill
    print(f"Parsing skill: {args.skill_path}")
    skill = parse_skill(args.skill_path)
    print(f"  Name: {skill['name']}")
    print(f"  Domain: {skill['domain']}")
    print(f"  Key behaviors: {len(skill['key_behaviors'])}")
    print(f"  Output format: {skill['output_format'][:80]}...")

    # Generate tasks
    print(f"\nGenerating {args.num_tasks} eval tasks...")
    result = generate_tasks_for_skill(skill, args.num_tasks)

    # Save output
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "tasks.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\nSaved {len(result['tasks'])} tasks to: {output_path}")

    # Also save skill analysis
    analysis_path = output_dir / "skill_analysis.json"
    with open(analysis_path, "w", encoding="utf-8") as f:
        json.dump(skill, f, indent=2, ensure_ascii=False)

    print(f"Skill analysis saved to: {analysis_path}")

    # Print summary
    print(f"\n=== SUMMARY ===")
    print(f"Skill: {skill['name']}")
    print(f"Domain: {skill['domain']}")
    print(f"Tasks generated: {len(result['tasks'])}")
    print(f"Task IDs: {[t['id'] for t in result['tasks']]}")


if __name__ == "__main__":
    main()
