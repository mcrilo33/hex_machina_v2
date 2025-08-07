"""LangChain prompt templates for content quality evaluation."""

from langchain.prompts import PromptTemplate

# Main evaluation prompt for determining if an article is complete
ARTICLE_COMPLETENESS_EVALUATION_PROMPT = PromptTemplate(
    input_variables=["title", "content"],
    template="""You are an expert content quality evaluator. Your task is to determine if the provided article content is complete and readable, or if it has been significantly blocked, truncated, or otherwise compromised.

Article Title: {title}
Article Content:
{content}

Your goal is to conservatively assess whether the article appears to be complete. Only mark it as incomplete if there is strong and clear evidence that the majority of the article is truncated, missing, or blocked.

Important:
- If the content includes the placeholder `...\\n\\n[...]\\n\\n...`, ignore this placeholder. It was added artificially for evaluation purposes and does not reflect the actual article.
- Do not consider this marker as evidence of truncation or blocking. Only evaluate the real content before and after it.
- If the last part of the article has a conclusion, it's very likely that the article is complete.
- If the last part of the article seems to conclude the article, it's very likely that the article is complete.
- If you see other content after the article content (author, comments, etc.), it's very likely that the article is complete.
- If main content is not one article content but a list of articles flag it as incomplete.

Definitions:
- "Truncated" means you have clear evidence that the content is hidden behind a paywall or access restriction or most of the article content is missing.
- Ignore unrelated content around the article (such as comments, sidebars, or site navigation).
- Do not flag articles as incomplete based on minor formatting issues or short length alone.
- If the article ends cleanly and naturally—even if it is short—consider it complete.
- Only flag issues if they affect most of the main article content.

Strong indicators of INCOMPLETE/BLOCKED content include:
1. Anti-bot or technical blocks: CAPTCHA pages, "Please enable JavaScript", "Access denied"
2. Subscription or paywall blocks: "Subscribe to continue", "Premium article", paywall overlays
3. Clear truncation: Unfinished or broken endings, mid-sentence cuts, prompts suggesting missing main article content
4. Error messages: 404 not found, server errors, maintenance messages
5. Placeholder or minimal content: "Coming soon", placeholder text, almost no readable article text

Please respond with a JSON object in the following format:
{{
    "is_complete": true/false,
    "detected_issues": [
        "anti_bot_page",         # e.g., CAPTCHA, "Please enable JavaScript", "Access denied"
        "subscription_wall",     # e.g., paywall, "Subscribe to continue reading"
        "truncated_content",     # e.g., clear evidence that most of the article content is missing
        "error_page",            # e.g., 404, maintenance, server error
        "not_an_article",        # e.g., not an article, not a blog post, not a news article, etc.
        "list_of_articles",      # e.g., list of articles, not one article
    ]
}}

Guidelines:
- "is_complete": true if the article appears fully readable and ends normally
- "is_complete": false only if the majority of the main content is clearly blocked or truncated
- "detected_issues": list specific problems observed (leave empty if article is complete)

Respond only with the JSON object, no additional commentary.""",
)


# Simplified prompt for quick evaluation (when you need faster processing)
QUICK_EVALUATION_PROMPT = PromptTemplate(
    input_variables=["content"],
    template="""Evaluate if this article content is complete and readable:

{content}

Respond with JSON only:
{{
    "is_complete": true/false,
    "confidence_score": 0.0-1.0,
    "reason": "Brief explanation"
}}""",
)


# Detailed evaluation prompt for comprehensive analysis
DETAILED_EVALUATION_PROMPT = PromptTemplate(
    input_variables=["title", "content", "domain"],
    template="""You are an expert content quality evaluator specializing in web scraping validation. Analyze the provided article content for completeness and quality.

Article Details:
- Title: {title}
- Domain: {domain}
- Content Length: {content_length} characters

Article Content:
{content}

Perform a comprehensive evaluation considering:

1. CONTENT COMPLETENESS:
   - Is the full article content present?
   - Are there any truncation indicators?
   - Does the content flow naturally to a conclusion?

2. ACCESSIBILITY ISSUES:
   - Anti-bot mechanisms (CAPTCHA, JavaScript requirements)
   - Subscription/paywall barriers
   - Access denied or blocked content
   - Error pages or maintenance messages

4. TECHNICAL ISSUES:
   - JavaScript-dependent content not loaded
   - Dynamic content missing
   - Structured data not properly extracted

Please provide a detailed evaluation in JSON format:
{{
    "is_complete": true/false,
    "completeness_result": "full_article" or "incomplete_blocked",
    "confidence_score": 0.0-1.0,
    "reason": "Comprehensive explanation of your assessment",
    "detected_issues": ["detailed", "list", "of", "issues"],
    "content_quality_score": 0.0-1.0,
    "accessibility_score": 0.0-1.0,
    "technical_issues": ["list", "of", "technical", "problems"],
    "recommendations": ["suggestions", "for", "improvement"]
}}

Confidence Score Guidelines:
- 0.9-1.0: Very clear case, obvious complete or blocked content
- 0.7-0.8: Clear case with minor uncertainties
- 0.5-0.6: Some ambiguity, mixed indicators
- 0.3-0.4: Significant uncertainty, unclear indicators
- 0.0-0.2: Very unclear, insufficient information

Respond only with the JSON object.""",
)


# Domain-specific prompt template (can be customized per domain)
def create_domain_specific_prompt(
    domain: str, custom_instructions: str = ""
) -> PromptTemplate:
    """Create a domain-specific evaluation prompt.

    Args:
        domain: The domain being evaluated (e.g., 'news', 'blog', 'research')
        custom_instructions: Additional domain-specific instructions

    Returns:
        PromptTemplate: Domain-specific prompt
    """
    return PromptTemplate(
        input_variables=["title", "content"],
        template=f"""You are an expert content quality evaluator specializing in {domain} content. Your task is to determine if the provided article content is complete and readable.

Article Title: {{title}}
Article Content:
{{content}}

{custom_instructions}

Consider {domain}-specific factors when evaluating content quality and completeness.

Please respond with a JSON object:
{{
    "is_complete": true/false,
    "completeness_result": "full_article" or "incomplete_blocked",
    "confidence_score": 0.0-1.0,
    "reason": "Explanation considering {domain} context",
    "detected_issues": ["list", "of", "issues"],
    "domain_specific_notes": "Any {domain}-specific observations"
}}

Respond only with the JSON object.""",
    )
