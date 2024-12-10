from pydantic import BaseModel, Field

from typed_prompt import BasePrompt, RenderedOutput


# Example 1: Basic Prompt with Custom Configuration
class ChatConfig(BaseModel):
    """Custom configuration for chat-based prompts."""

    temperature: float = Field(default=0.7, ge=0, le=2)
    model: str = Field(default="gpt-4")
    context_window: int = Field(default=4096, gt=0)
    streaming: bool = Field(default=True)


class ChatVariables(BaseModel):
    username: str
    role: str
    expertise_level: str | None = "beginner"


class ChatPrompt(BasePrompt[ChatVariables]):
    """You are assisting {{username}} who is a {{role}}
    with {{expertise_level}} level expertise."""

    prompt_template: str = "Can you help me understand {{topic}} in detail?"
    variables: ChatVariables
    config: ChatConfig = Field(default_factory=ChatConfig)

    def render(self, *, topic: str, **extra_vars) -> RenderedOutput:
        extra_vars["topic"] = topic
        return super().render(**extra_vars)


# Usage
chat_config = ChatConfig(temperature=0.9, streaming=False)
var = ChatVariables(username="Alice", role="developer", expertise_level="intermediate")
prompt = ChatPrompt(variables=var, config=chat_config)
result = prompt.render(topic="Python metaclasses")
print(f"System: {result.system_prompt}")
print(f"User: {result.user_prompt}")

# Example 2: Template Validation - Missing Variable Error
try:

    class InvalidPrompt(BasePrompt[ChatVariables]):
        """System prompt using {{username}}."""

        # This will fail at class definition because 'unknown_var'
        # is not defined in ChatVariables or render method
        prompt_template: str = "Please explain {{unknown_var}}"
        variables: ChatVariables

except ValueError as e:
    print(f"Validation Error: {e}")

# Example 3: Template Validation - Unused Variable Warning
try:

    class UnusedVarsPrompt(BasePrompt[ChatVariables]):
        """Simple greeting."""

        # This will fail because 'role' and 'expertise_level'
        # are defined but never used in templates
        prompt_template: str = "Hello {{username}}!"
        variables: ChatVariables

except ValueError as e:
    print(f"Unused Variables Error: {e}")


# Example 4: Complex Real-World Example - Code Review Assistant
class ReviewConfig(BaseModel):
    """Configuration for code review prompts."""

    temperature: float = Field(default=0.8, ge=0, le=2)
    max_tokens: int = Field(default=1000, gt=0)
    model: str = Field(default="gpt-4")
    review_depth: str = Field(default="detailed", pattern="^(brief|detailed|security-focused)$")


class ReviewVariables(BaseModel):
    reviewer_name: str
    programming_language: str
    code_context: str | None = None
    review_focus: list[str] = Field(default_factory=list)


class CodeReviewPrompt(BasePrompt[ReviewVariables]):
    """You are an experienced code reviewer named {{reviewer_name}}
    specializing in {{programming_language}} development.
    {% if code_context %}
    Context for this review: {{code_context}}
    {% endif %}
    {% if review_focus %}
    Focus areas: {% for area in review_focus %}
    - {{area}}{% endfor %}
    {% endif %}
    Please provide a {{review_depth}} review of the code."""

    prompt_template: str = """
    Review the following {{programming_language}} code:

    ```{{programming_language}}
    {{code_snippet}}
    ```

    {% if specific_concerns %}
    Please pay special attention to: {{specific_concerns}}
    {% endif %}
    """

    variables: ReviewVariables
    config: ReviewConfig = Field(default_factory=ReviewConfig)

    def render(
        self, *, code_snippet: str, specific_concerns: str | None = None, review_depth: str = "detailed", **extra_vars
    ) -> RenderedOutput:
        extra_vars.update({
            "code_snippet": code_snippet,
            "specific_concerns": specific_concerns,
            "review_depth": review_depth,
        })
        return super().render(**extra_vars)


# Usage
config = ReviewConfig(temperature=0.7, review_depth="security-focused")

review_vars = ReviewVariables(
    reviewer_name="SecurityExpert",
    programming_language="Python",
    code_context="Authentication module review",
    review_focus=["security", "performance", "maintainability"],
)

review_prompt = CodeReviewPrompt(variables=review_vars, config=config)
result = review_prompt.render(
    code_snippet="def authenticate(user, pwd): return user == 'admin' and pwd == '1234'",
    specific_concerns="Potential security vulnerabilities",
)
