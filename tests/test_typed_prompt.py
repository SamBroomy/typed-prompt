from typing import List, Optional

import pytest
from pydantic import BaseModel, Field

from typed_prompt import BasePrompt, RenderOutput


class BasicVariables(BaseModel):
    """Simple variables model for basic test cases."""

    name: str
    age: int
    role: Optional[str] = None


class BasicConfig(BaseModel):
    """Simple configuration model for testing config integration."""

    temperature: float = Field(default=0.7, ge=0, le=2)
    model: str = Field(default="gpt-4")


class TestBasicPromptFunctionality:
    """Test the basic functionality of prompt creation and rendering."""

    def test_simple_prompt_creation(self):
        """Test that we can create a simple prompt with basic variables."""

        class SimplePrompt(BasePrompt[BasicVariables]):
            """Hello {{name}}, you are {{age}} years old."""

            prompt_template: str = "{{role if role}} What would you like to know?"
            variables: BasicVariables

        vars = BasicVariables(name="Alice", age=30)
        prompt = SimplePrompt(variables=vars)
        result = prompt.render()

        assert isinstance(result, RenderOutput)
        assert result.system_prompt is not None
        assert "Hello Alice, you are 30 years old" in result.system_prompt
        assert "What would you like to know?" == result.user_prompt

    def test_prompt_rendering(self):
        """Test that we can render a prompt with additional variables."""

        class AdditionalVarPrompt(BasePrompt[BasicVariables]):
            """Hello {{name}}, you are {{age}} years old."""

            prompt_template: str = "{{role}} What would you like to know?"
            variables: BasicVariables

        vars = BasicVariables(name="Bob", age=25)
        prompt = AdditionalVarPrompt(variables=vars)
        result1 = prompt.render(role="Hello!")
        assert result1.system_prompt is not None
        assert "Hello Bob, you are 25 years old" in result1.system_prompt
        assert "Hello! What would you like to know?" == result1.user_prompt

        result2 = prompt.render()
        assert result2.system_prompt is not None
        assert "None What would you like to know?" == result2.user_prompt

    def test_optional_variable_handling(self):
        """Test that optional variables are handled correctly."""

        class OptionalPrompt(BasePrompt[BasicVariables]):
            """{{name}} {% if role %}({{role}}) - {{age}}{% endif %}"""

            prompt_template: str = "Hello!"
            variables: BasicVariables

            def render(self, **extra_vars) -> RenderOutput:
                return super().render(**extra_vars)

        # Test without optional role
        vars1 = BasicVariables(name="Bob", age=25)
        prompt1 = OptionalPrompt(variables=vars1)
        result1 = prompt1.render()
        assert result1.system_prompt is not None
        assert "Bob" in result1.system_prompt
        assert ")" not in result1.system_prompt
        assert "25" not in result1[1]

        vars2 = BasicVariables(name="Bob", age=25, role="developer")
        prompt2 = OptionalPrompt(variables=vars2)
        result2 = prompt2.render()
        assert result2.system_prompt is not None
        assert "Bob (developer)" in result2.system_prompt
        assert "25" in result2.system_prompt


class TestPromptValidation:
    """Test the validation features of the prompt system."""

    def test_missing_variable_detection(self):
        """Test that using undefined variables raises an error."""
        with pytest.raises(ValueError) as excinfo:

            class InvalidPrompt(BasePrompt[BasicVariables]):
                prompt_template: str = "What is {{undefined_var}}?"
                variables: BasicVariables

                def render(self, **extra_vars) -> RenderOutput:
                    return super().render(**extra_vars)

        assert "Template uses variables not defined" in str(excinfo.value)

    def test_unused_variable_detection(self):
        """Test that defining unused variables raises an error."""
        with pytest.raises(ValueError) as excinfo:

            class UnusedVarPrompt(BasePrompt[BasicVariables]):
                prompt_template: str = "Hello {{name}}!"  # 'age' and 'role' unused
                variables: BasicVariables

                def render(self, **extra_vars) -> RenderOutput:
                    return super().render(**extra_vars)

        assert (
            "Variables defined in variables model or render method are not used"
            in str(excinfo.value)
        )

    def test_render_method_variable_validation(self):
        """Test that variables can be properly provided through render method."""

        class RenderVarPrompt(BasePrompt[BasicVariables]):
            prompt_template: str = (
                "{{name}} of {{age}} who {{role}} wants to learn {{topic}}"
            )
            variables: BasicVariables

            def render(self, *, topic: str, **extra_vars) -> RenderOutput:
                extra_vars["topic"] = topic
                return super().render(**extra_vars)

        vars = BasicVariables(name="Charlie", age=35, role="manager")
        prompt = RenderVarPrompt(variables=vars)
        result = prompt.render(topic="Python")
        assert result.system_prompt is None
        assert "Charlie of 35 who manager wants to learn Python" in result.user_prompt


class TestConfigurationIntegration:
    """Test the integration of configuration with prompts."""

    def test_custom_config_handling(self):
        """Test that custom configurations can be integrated and accessed."""

        class ConfiguredPrompt(BasePrompt[BasicVariables]):
            prompt_template: str = "Hello {{name}} of age {{age}} with role {{role}}"
            variables: BasicVariables
            config: BasicConfig = Field(default_factory=BasicConfig)

            def render(self, **extra_vars) -> RenderOutput:
                return super().render(**extra_vars)

        vars = BasicVariables(name="David", age=40)
        config = BasicConfig(temperature=0.9, model="gpt-3.5-turbo")
        prompt = ConfiguredPrompt(variables=vars, config=config)

        assert prompt.config.temperature == 0.9
        assert prompt.config.model == "gpt-3.5-turbo"


class TestComplexTemplates:
    """Test more complex template features and edge cases."""

    def test_nested_conditionals(self):
        """Test that complex conditional logic in templates works correctly."""

        class ComplexTemplatePrompt(BasePrompt[BasicVariables]):
            """{% if role %}
            {{name}} is a {{role}}
            {% if age < 30 %}
            They are a junior {{role}}
            {% else %}
            They are a senior {{role}}
            {% endif %}
            {% else %}
            {{name}} is {{age}} years old
            {% endif %}"""

            prompt_template: str = "Hello!"
            variables: BasicVariables

            def render(self, **extra_vars) -> RenderOutput:
                return super().render(**extra_vars)

        # Test with role and young age
        vars1 = BasicVariables(name="Eve", age=25, role="developer")
        prompt1 = ComplexTemplatePrompt(variables=vars1)
        result1 = prompt1.render()
        assert result1.system_prompt is not None
        assert "junior developer" in result1.system_prompt

        # Test with role and senior age
        vars2 = BasicVariables(name="Frank", age=45, role="developer")
        prompt2 = ComplexTemplatePrompt(variables=vars2)
        result2 = prompt2.render()
        assert result2.system_prompt is not None
        assert "senior developer" in result2.system_prompt


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_invalid_template_syntax(self):
        """Test that invalid Jinja2 syntax is caught."""
        with pytest.raises(Exception) as excinfo:

            class InvalidSyntaxPrompt(BasePrompt[BasicVariables]):
                prompt_template: str = "Hello {{name}}}}"  # Extra }
                variables: BasicVariables

                def render(self, **extra_vars) -> RenderOutput:
                    return super().render(**extra_vars)

        assert "template" in str(excinfo.value).lower()

    def test_type_validation(self):
        """Test that type validation works for variables."""

        class TypedPrompt(BasePrompt[BasicVariables]):
            prompt_template: str = "{{name}} is {{age}} and is a {{role}}"
            variables: BasicVariables

            def render(self, **extra_vars) -> RenderOutput:
                return super().render(**extra_vars)

        # Test with invalid age type
        with pytest.raises(Exception) as excinfo:
            TypedPrompt(
                variables=BasicVariables(name="Greg", age="thirty", role="manager")
            )  # age should be int

        assert "type" in str(excinfo.value).lower()


def test_real_world_scenario():
    """Test a realistic scenario combining multiple features."""

    class ArticleConfig(BaseModel):
        style: str = Field(default="formal")
        max_length: int = Field(default=1000)
        include_examples: bool = Field(default=True)

    class ArticleVariables(BaseModel):
        author: str
        topic: str
        target_audience: str
        key_points: List[str] = Field(default_factory=list)
        technical_level: str = Field(default="intermediate")
        config: ArticleConfig = Field(default_factory=ArticleConfig)

    class ArticlePrompt(BasePrompt[ArticleVariables]):
        """You are helping {{author}} write an article about {{topic}}
        for {{target_audience}} audience at a {{technical_level}} level.
        {% if key_points %}
        Key points to cover:
        {% for point in key_points %}
        - {{point}}
        {% endfor %}
        {% endif %}"""

        prompt_template: str = """
        Please write an {{config.style}} article
        {% if config.include_examples %}with practical examples{% endif %}
        within {{config.max_length}} words.
        """

        variables: ArticleVariables

    vars = ArticleVariables(
        author="Helen",
        topic="Python Type Hints",
        target_audience="developers",
        key_points=["Basic syntax", "Generic types"],
        technical_level="advanced",
        config=ArticleConfig(style="technical", max_length=1500, include_examples=True),
    )

    prompt = ArticlePrompt(variables=vars)
    result = prompt.render()
    assert result.system_prompt is not None
    assert "Helen" in result.system_prompt
    assert "Python Type Hints" in result.system_prompt
    assert "Basic syntax" in result.system_prompt
    assert "Generic types" in result.system_prompt

    assert "technical" in result.user_prompt
    assert "1500" in result.user_prompt
    assert "practical examples" in result.user_prompt


class TestPromptTemplateNotDefined:
    """Test the behavior when prompt_template is not defined."""

    def test_prompt_template_not_defined(self):
        """Test that an error is raised when prompt_template is not defined."""

        with pytest.raises(ValueError) as excinfo:

            class NoTemplatePrompt(BasePrompt[BasicVariables]):
                variables: BasicVariables

                def render(self, **extra_vars) -> RenderOutput:
                    return super().render(**extra_vars)

        assert "prompt_template" in str(excinfo.value)


class TestVairableModelNotDefined:
    """Test the behavior when variables model is not defined."""

    def test_variable_model_not_defined(self):
        """Test that an error is raised when variables model is not defined."""

        with pytest.raises(ValueError) as excinfo:

            class NoVariablesPrompt(BasePrompt):
                prompt_template: str = "Hello {{name}}"
                variables: BasicVariables

                def render(self, **extra_vars) -> RenderOutput:
                    return super().render(**extra_vars)

        assert "variables model" in str(excinfo.value)


class TestVariablesNotDefined:
    """Test the behavior when variables are not defined."""

    def test_variables_not_defined(self):
        """Test that an error is raised when variables are not defined."""

        with pytest.raises(ValueError) as excinfo:

            class NoVariablesPrompt(BasePrompt[BasicVariables]):
                prompt_template: str = "Hello {{name}}"

                def render(self, **extra_vars) -> RenderOutput:
                    return super().render(**extra_vars)

        assert "variables" in str(excinfo.value)
