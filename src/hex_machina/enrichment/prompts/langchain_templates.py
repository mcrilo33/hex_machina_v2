"""LangChain-aligned prompt templates."""

from typing import Dict

from langchain_core.prompts import ChatPromptTemplate

# LangChain-aligned prompt templates
CONTENT_COMPLETENESS_TEMPLATE = ChatPromptTemplate.from_template(
    """You are an expert content evaluator. Your task is to determine if an article's content is complete and identify any issues that might indicate incomplete or problematic content.

Article Title: {title}
Article Content: {content}

Please evaluate the completeness of this article and identify any issues. Consider the following:

1. Is the content complete and readable?
2. Are there any signs of truncated content?
3. Are there any anti-bot or subscription walls?
4. Is this actually an article or just a list/error page?
5. Are there any other issues that would make this content incomplete?

Respond with ONLY a JSON object containing exactly these two fields:
- "is_complete": boolean (true if the article is complete and readable)
- "detected_issues": array of strings (empty if no issues, otherwise list the issues found)

Valid issue types:
- "anti_bot_page" - Content is blocked by anti-bot measures
- "subscription_wall" - Content requires subscription to access
- "truncated_content" - Content appears to be cut off or incomplete
- "error_page" - Page shows an error instead of content
- "not_an_article" - Content is not actually an article
- "list_of_articles" - Page is just a list of articles, not a single article

Do not include any additional fields or explanations. Return only the JSON object."""
)


# Template registry for easy access
LANGCHAIN_TEMPLATES: Dict[str, ChatPromptTemplate] = {
    "content_completeness": CONTENT_COMPLETENESS_TEMPLATE,
}


def get_langchain_template(template_name: str) -> ChatPromptTemplate:
    """Get a LangChain prompt template by name.

    Args:
        template_name: Name of the template to retrieve

    Returns:
        LangChain ChatPromptTemplate

    Raises:
        ValueError: If template not found
    """
    if template_name not in LANGCHAIN_TEMPLATES:
        raise ValueError(
            f"Template '{template_name}' not found. Available templates: {list(LANGCHAIN_TEMPLATES.keys())}"
        )

    return LANGCHAIN_TEMPLATES[template_name]


def create_custom_template(template_string: str) -> ChatPromptTemplate:
    """Create a custom LangChain prompt template from a string.

    Args:
        template_string: Template string with variables in {variable} format

    Returns:
        LangChain ChatPromptTemplate
    """
    return ChatPromptTemplate.from_template(template_string)
