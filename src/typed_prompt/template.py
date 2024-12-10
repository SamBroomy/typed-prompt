import re
from abc import ABC
from inspect import Parameter, signature
from textwrap import dedent
from typing import Any, Generic, NamedTuple, TypeVar

import jinja2
import jinja2.meta
import jinja2.nodes
from pydantic import BaseModel, ConfigDict
from pydantic._internal._model_construction import ModelMetaclass

from typed_prompt.exceptions import MissingVariablesError, UndeclaredVariableError, UnusedVariablesError


class PromptMeta(ModelMetaclass):
    """Metaclass for the BasePrompt class that handles template validation and compilation.

    This metaclass performs comprehensive validation during class creation to ensure
    prompt templates are well-formed and all variables are properly managed. It provides
    early detection of common issues like missing or unused variables.

    Validation steps include:
    1. Validating required prompt templates and variable models
    2. Ensuring all template variables are properly defined
    3. Detecting unused variables to prevent code bloat
    4. Compiling templates for efficient rendering
    5. Validating template syntax

    Attributes:
        compiled_system_prompt_template (Optional[jinja2.Template]): Compiled system prompt
        compiled_prompt_template (jinja2.Template): Compiled user prompt
        base_regex (re.Pattern): Regular expression for base class name

    Example:
        This metaclass automatically validates prompt classes:

        ```python
        class UserPrompt(BasePrompt[UserVariables]):
            '''System prompt template in docstring'''

            prompt_template = "User prompt here"
            variables: UserVariables
        ```

        If validation fails, clear error messages are provided:
        - Missing variables: "Template uses variables not defined..."
        - Unused variables: "Variables defined but not used..."
        - Missing templates: "Both 'prompt_template' and a 'variables' model must be defined..."
    """

    compiled_system_prompt_template: jinja2.Template | None
    compiled_prompt_template: jinja2.Template
    base_regex = re.compile(r"^BasePrompt(?:\[[^\]]+\])?$")

    def __new__(mcs, cls_name: str, bases: tuple[type[Any], ...], namespace: dict[str, Any], /, **kwargs: Any) -> type:
        """Create a new prompt class with validated templates and compiled Jinja2 templates.

        This method performs comprehensive validation of the prompt class definition:
        1. Validates template and variable model presence
        2. Sets up the Jinja2 environment
        3. Extracts and validates template variables
        4. Compiles templates for efficient rendering
        5. Validates variable coverage

        Args:
            cls_name: Name of the class being created
            bases: Tuple of base classes
            namespace: Dictionary of class attributes
            **kwargs: Additional keyword arguments for class creation

        Returns:
            type: The newly created class with validated templates

        Raises:
            ValueError: If templates are missing or variables are undefined
            jinja2.TemplateError: If template syntax is invalid
        """
        cls = super().__new__(mcs, cls_name, bases, namespace, **kwargs)
        # Skip validation for the base class itself
        if cls.base_regex.match(cls_name):
            return cls
        # Extract template configuration from class namespace
        fetch_prompt_template: str | None = namespace.get("prompt_template")
        # Extract the variables model from the class annotations
        variables_model: BaseModel | None = namespace.get("__annotations__", {}).get("variables")
        # Validate that the template and variables model are defined
        if not fetch_prompt_template or not variables_model:
            raise UndeclaredVariableError
        # Setup and validate templates
        template_env: jinja2.Environment = cls._setup_template_env()
        prompt_template: str = cls._get_template_string(fetch_prompt_template)
        template_node = template_env.parse(prompt_template)
        template_vars = jinja2.meta.find_undeclared_variables(template_node)
        # Handle system prompt template
        fetch_system_prompt_template: str | None = namespace.get("system_prompt_template", namespace.get("__doc__"))
        system_prompt_template: str = ""
        system_template_vars = set()
        if fetch_system_prompt_template:
            system_prompt_template: str = cls._get_template_string(fetch_system_prompt_template)
            system_template_node = template_env.parse(system_prompt_template)
            system_template_vars = jinja2.meta.find_undeclared_variables(system_template_node)
        # Validate variable coverage
        template_vars |= system_template_vars
        variable_fields = set(variables_model.model_fields.keys())
        # Handle custom render method parameters
        render_method = namespace.get("render")
        render_params: set[str] = set()
        if render_method and render_method != BasePrompt.render:
            render_params = {
                name
                for name, param in signature(render_method).parameters.items()
                if param.kind == Parameter.KEYWORD_ONLY
            }
        variable_fields |= render_params
        # Check for missing variables
        missing_vars = template_vars - variable_fields
        if missing_vars:
            raise MissingVariablesError(missing_vars)
        # Check for unused variables
        unused_vars = variable_fields - template_vars
        if unused_vars:
            raise UnusedVariablesError(unused_vars)

        # Compile templates
        cls.compiled_system_prompt_template = (
            template_env.from_string(system_prompt_template) if fetch_system_prompt_template else None
        )
        cls.compiled_prompt_template = template_env.from_string(prompt_template)

        return cls

    @staticmethod
    def _setup_template_env() -> jinja2.Environment:
        """Initialize and configure the Jinja2 environment.

        Returns:
            jinja2.Environment: Configured Jinja2 environment for template processing
        """

        return jinja2.Environment(autoescape=False, trim_blocks=True, lstrip_blocks=True)

    @staticmethod
    def _get_template_string(template_string: str) -> str:
        """Process and clean up a template string.

        Args:
            template_string: Raw template string from class definition

        Returns:
            str: Processed template string with consistent formatting
        """
        return dedent(template_string).strip()


class RenderedOutput(NamedTuple):
    """Structured output from prompt rendering.

    This class provides named access to the rendered system and user prompts,
    making it easier to work with the render results in a type-safe way.

    Attributes:
        system_prompt (Optional[str]): The rendered system prompt, if defined
        user_prompt (str): The rendered user prompt

    Example:
        ```python
        print(f"System: {result.system_prompt}")
        print(f"User: {result.user_prompt}")
        ```
    """

    system_prompt: str | None
    user_prompt: str


T = TypeVar("T", bound=BaseModel)


class BasePrompt(BaseModel, Generic[T], ABC, metaclass=PromptMeta):
    """Base class for creating type-safe, validated prompt templates.

    This class provides the foundation for creating structured prompts with:
    - Type validation through Pydantic
    - Template validation and compilation
    - System and user prompt support
    - Flexible variable handling

    The class uses a generic type parameter T that must be a Pydantic BaseModel
    defining the structure of template variables.

    Template variables can be defined in three ways:
    1. In the variables model (required fields)
    2. In the custom render method (as keyword-only arguments)
    3. As extra variables passed to render (for one-off use)

    Example:
    ```python
    class UserVariables(BaseModel):
        name: str
        age: int
        occupation: Optional[str] = None
        # learning_topic: Optional[str] = None


    class UserPrompt(BasePrompt[UserVariables]):
        \"\"\"You are talking to {{name}}, age {{age}}
        {%- if occupation %}, a {{occupation}}{% endif %}.

        Please provide a personalized response considering their background.\"\"\"

        # Or instead of defining the system prompt using the docstring,
        # you can define it as a class attribute if you prefer.
        # system_prompt_template: str = "..."

        prompt_template = "What would you like to learn about {{topic}}?"
        variables: UserVariables

        # If you want to pass in a variable that is not part of the UserVariables model,
        # you can do so by redefining the render method
        # Below as an minimum viable example,
        # we pass in the learning_topic variable as a keyword argument

        def render(self, *, topic: str, **extra_vars) -> RenderOutput:
            extra_vars["topic"] = topic
            return super().render(**extra_vars)


    ```

    Notes:
        - None values will be rendered in the jinja template as `None`
        - System prompts can be defined either in the class docstring or as a
          system_prompt_template class attribute
        - All template variables must be defined either in the variables model or
          as keyword-only parameters in the render method
        - The class validates templates and variables at definition time
        - Unused variables are detected and reported as errors
    """

    system_prompt_template: str | None = None
    prompt_template: str
    variables: T

    model_config = ConfigDict(arbitrary_types_allowed=True, protected_namespaces=())

    def render(self, **extra_vars: Any) -> RenderedOutput:
        """Render prompt templates with provided variables.

        This method combines the variables model data with any additional variables
        to render both the system prompt (if defined) and the user prompt. It
        returns a RenderOutput containing both rendered prompts.

        For custom rendering logic, override this method and implement keyword-only
        parameters for template variables not defined in the variables model.

        Args:
            **extra_vars: Additional template variables not in variables model

        Returns:
            RenderOutput: Named tuple containing system_prompt and user_prompt

        Example:
            Custom render method with additional parameters:
            ```python
            def render(self, *, topic: str, difficulty: str = "intermediate", **extra_vars) -> RenderOutput:
                extra_vars.update({"topic": topic, "difficulty": difficulty})
                return super().render(**extra_vars)
            ```
        """

        variables_dict = self.variables.model_dump()
        context = {**variables_dict, **extra_vars}

        system_prompt = (
            self.compiled_system_prompt_template.render(**context).strip()
            if self.compiled_system_prompt_template
            else None
        )
        user_prompt = self.compiled_prompt_template.render(**context).strip()

        return RenderedOutput(system_prompt, user_prompt)

    async def render_async(self, **extra_vars: Any) -> RenderedOutput:
        variables_dict = self.variables.model_dump()
        context = {**variables_dict, **extra_vars}

        system_prompt = (
            (await self.compiled_system_prompt_template.render_async(**context)).strip()
            if self.compiled_system_prompt_template
            else None
        )
        user_prompt = (await self.compiled_prompt_template.render_async(**context)).strip()

        return RenderedOutput(system_prompt, user_prompt)
