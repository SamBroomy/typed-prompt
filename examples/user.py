import asyncio

from pydantic import BaseModel, Field

from typed_prompt import AsyncBasePrompt, BasePrompt, RenderedOutput


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


def run_basic_chat_example():
    """Example 1: Demonstrate basic sync prompt usage with configuration."""
    print("\n=== Basic Chat Example ===")
    chat_config = ChatConfig(temperature=0.9, streaming=False)
    var = ChatVariables(username="Alice", role="developer", expertise_level="intermediate")
    prompt = ChatPrompt(variables=var, config=chat_config)
    result = prompt.render(topic="Python metaclasses")
    print(f"System: {result.system_prompt}")
    print(f"User: {result.user_prompt}")


def run_validation_examples():
    """Example 2 & 3: Demonstrate template validation."""
    print("\n=== Validation Examples ===")
    try:

        class InvalidPrompt(BasePrompt[ChatVariables]):
            """System prompt using {{username}}."""

            prompt_template: str = "Please explain {{unknown_var}}"
            variables: ChatVariables

    except ValueError as e:
        print(f"Missing Variable Error: {e}")

    try:

        class UnusedVarsPrompt(BasePrompt[ChatVariables]):
            """Simple greeting."""

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


def run_code_review_example():
    """Example 4: Demonstrate complex sync prompt with code review."""
    print("\n=== Code Review Example ===")
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
    print(f"System: {result.system_prompt}")
    print(f"User: {result.user_prompt}")


# Example 5: Async Image Generation
class ImageGenVars(BaseModel):
    style: str
    subject: str
    dimensions: tuple[int, int] = (1024, 1024)


class AsyncImagePrompt(AsyncBasePrompt[ImageGenVars]):
    """You are a skilled artist creating {{style}} style images."""

    prompt_template: str = """Create an image of {{subject}} with dimensions {{dimensions}}"""
    variables: ImageGenVars


async def run_async_image_example():
    """Example 5: Demonstrate async image generation prompt."""
    print("\n=== Async Image Generation Example ===")
    image_prompt = AsyncImagePrompt(variables=ImageGenVars(style="abstract", subject="flowers"))
    result = await image_prompt.render()
    print(f"System: {result.system_prompt}")
    print(f"User: {result.user_prompt}")


# Example 6: Async Translation with Additional Context
class TranslationVars(BaseModel):
    source_lang: str
    target_lang: str
    formality: str = "neutral"


class AsyncTranslationPrompt(AsyncBasePrompt[TranslationVars]):
    """You are a professional translator from {{source_lang}} to {{target_lang}}
    maintaining {{formality}} tone."""

    prompt_template: str = """Translate the following {{context_type}} text:
    {{text}}"""
    variables: TranslationVars

    async def render(self, *, text: str, context_type: str = "general", **extra_vars) -> RenderedOutput:
        extra_vars.update({"text": text, "context_type": context_type})
        return await super().render(**extra_vars)


async def run_async_translation_example():
    """Example 6: Demonstrate async translation prompt."""
    print("\n=== Async Translation Example ===")
    translation_prompt = AsyncTranslationPrompt(variables=TranslationVars(source_lang="en", target_lang="fr"))
    result = await translation_prompt.render(text="Hello, how are you?", context_type="casual")
    print(f"System: {result.system_prompt}")
    print(f"User: {result.user_prompt}")


# Example 7: Async Code Completion with Complex Template
class CompletionVars(BaseModel):
    language: str
    style_guide: str | None = None
    max_tokens: int = 500


class AsyncCompletionPrompt(AsyncBasePrompt[CompletionVars]):
    """You are a code completion assistant for {{language}}.
    {% if style_guide %}Following {{style_guide}} conventions.{% endif %}
    Keep responses within {{max_tokens}} tokens."""

    prompt_template: str = """Complete the following code:
    {% if context %}Background context:
    {{context}}
    {% endif %}

    Code to complete:
    ```{{language}}
    {{code}}
    ```
    """
    variables: CompletionVars

    async def render(self, *, code: str, context: str | None = None, **extra_vars) -> RenderedOutput:
        extra_vars.update({"code": code, "context": context})
        return await super().render(**extra_vars)


async def run_async_completion_example():
    """Example 7: Demonstrate async code completion prompt."""
    print("\n=== Async Code Completion Example ===")
    completion_prompt = AsyncCompletionPrompt(variables=CompletionVars(language="python", style_guide="PEP8"))
    result = await completion_prompt.render(code="def add(a, b):", context="Add two numbers")
    print(f"System: {result.system_prompt}")
    print(f"User: {result.user_prompt}")


def run_sync_examples():
    """Run all synchronous examples."""
    print("\n=== Running Synchronous Examples ===")
    run_basic_chat_example()
    run_validation_examples()
    run_code_review_example()


async def run_async_examples():
    """Run all async examples."""
    print("\n=== Running Asynchronous Examples ===")
    await run_async_image_example()
    await run_async_translation_example()
    await run_async_completion_example()


async def main():
    """Run all examples in proper order."""
    # Run sync examples first
    run_sync_examples()

    # Then run async examples
    await run_async_examples()


if __name__ == "__main__":
    """Execute all examples."""
    print("=== Typed Prompt Examples ===")
    print("Running examples to demonstrate both sync and async usage...")
    asyncio.run(main())
