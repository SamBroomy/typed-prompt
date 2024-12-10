[![PyPI version](https://badge.fury.io/py/typed-prompt.svg)](https://badge.fury.io/py/typed-prompt)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/typed-prompt)](https://pypi.org/project/typed-prompt/)

# typed-prompt

A type-safe, validated prompt management system for LLMs that catches errors early, enforces type safety, and provides a structured way to manage prompts.
Uses Pydantic models for variable validation and Jinja2 templates for prompt rendering.

> **Note**: This library is in early development and subject to change.

## Why typed-prompt?

I have always found it challenging to manage dynamic prompts for LLMs. The process is error-prone, with issues often discovered only at runtime. typed-prompt aims to solve this problem by providing a structured, type-safe way to manage prompts that catches errors early and enforces type safety.

> **Disclaimer**: This is a personal project to solve gripes ive had in the past and not affiliated with any organization. It is a work in progress and subject to change.
>
> I will be adding more features and examples in the future. If you have any suggestions or feedback, feel free to open an issue!

## Quick Examples

### 1. Basic Usage with Validation

```python
from typed_prompt import BasePrompt
from pydantic import BaseModel
from typing import Optional

# Define your variables
class UserVars(BaseModel):
    name: str
    expertise: str

# This works - all template variables are defined
class ValidPrompt(BasePrompt[UserVars]):
    """Helping {{name}} with {{expertise}} level knowledge."""
    prompt_template: str = "Explain {{topic}} to me"
    variables: UserVars

    def render(self, *, topic: str, **extra_vars) -> RenderOutput:
        extra_vars["topic"] = topic
        return super().render(**extra_vars)

# This fails immediately - 'unknown_var' not defined
class InvalidPrompt(BasePrompt[UserVars]):
    prompt_template: str = "What is {{unknown_var}}?"  # ValueError!
    variables: UserVars

# This fails - 'expertise' defined but never used
class UnusedVarPrompt(BasePrompt[UserVars]):
    prompt_template: str = "Hello {{name}}"  # ValueError!
    variables: UserVars
```

### 2. Conditional Templates

```python
from typing import Union

class TemplateVars(BaseModel):
    user_type: Union["expert", "beginner"]
    name: str
    preferences: Optional[dict] = None

class ConditionalPrompt(BasePrompt[TemplateVars]):
    """{% if user_type == 'expert' %}
    Technical advisor for {{name}}
    {% else %}
    Friendly helper for {{name}}
    {% endif %}"""

    prompt_template: str = """
    {% if preferences %}
    Considering your preferences: {% for k, v in preferences.items() %}
    - {{k}}: {{v}}{% endfor %}
    {% endif %}
    How can I help with {{topic}}?
    """
    variables: TemplateVars

    def render(self, *, topic: str, **extra_vars) -> RenderOutput:
        extra_vars["topic"] = topic
        return super().render(**extra_vars)
```

### 3. LLM configuration defined with the template

```python
from typed_prompt import RenderOutput
from pydantic import BaseModel, Field


class MyConfig(BaseModel):
    temperature: float = Field(default=0.7, ge=0, le=2)
    model: str = Field(default="gpt-4")

class MyPrompt(BasePrompt[UserVars]):
    """Assistant for {{name}}"""
    prompt_template: str = "Help with {{topic}}"
    variables: UserVars
    config: MyConfig = Field(default_factory=MyConfig)

    def render(self, *, topic: str, **extra_vars) -> RenderOutput:
        extra_vars["topic"] = topic
        return super().render(**extra_vars)

# Use custom config
prompt = MyPrompt(
    variables=UserVars(name="Alice", expertise="intermediate"),
    config=MyConfig(temperature=0.9, model="gpt-3.5-turbo")
)
```

> **Note**: Using None as a value for optional variables will render as `None` in the prompt.
> e.g "Test example `{{var}}` will render as `Test example None` if `var` is `None`.
> This is the default behaviour of jinja.
>Therefore you need to handle this in your jinja2 template.
> e.g `{{if var}}` or `{{var | default('default value')}}` or however you want to handle it.

## Key Features

### Early Validation

The library validates your prompt templates during class definition:

- Missing variables are caught immediately
- Unused variables are detected
- Template syntax is verified
- Type checking is enforced

### Type Safety

All variables are validated through Pydantic:

- Required vs optional fields
- Type constraints
- Custom validators
- Nested models

### Flexible Configuration

Attach custom configuration to prompts:

- Model parameters
- Custom settings
- Validation rules
- Default values

## Why Early Validation Matters

Consider this example:

```python
# Without typed-prompt
def create_prompt(user_data):
    template = "Hello {{username}}, your level is {{level}}"
    # Error only discovered when rendering with wrong data
    return template.format(**user_data)  # KeyError at runtime!

# With typed-prompt
class UserPrompt(BasePrompt[UserVars]):
    prompt_template: str = "Hello {{unknown_var}}"  # Error immediately!
    variables: UserVars
```

The library catches template errors at definition time.

## Installation

```bash
uv add tpyed-prompt
```

or

```bash
pip install typed-prompt
```

## Examples

For more examples and detailed documentation, check the [examples](./examples) directory.

To run the examples:

```bash
uv run python examples/user.py
```

## Core Concepts

### The Prompt Structure

typed-prompt uses a two-part prompt structure that matches common LLM interaction patterns:

1. **System Prompt**: Provides context or instructions for the AI model. You can define this in two ways:
   - As a class docstring (recommended for better code organization)
   - As a `system_prompt_template` class attribute

2. **User Prompt**: Contains the actual prompt template that will be sent to the model. This is always defined in the `prompt_template` class attribute.

### Variable Management

Variables in typed-prompt are handled through three complementary mechanisms:

1. **Variables Model**: A Pydantic model that defines the core variables your prompt needs:

   ```python
   class UserVariables(BaseModel):
       name: str
       age: int
       occupation: Optional[str] = None
   ```

2. **Render Method Parameters**: Additional variables can be defined as keyword-only arguments in a custom render method:

   ```python
   def render(self, *, learning_topic: str, **extra_vars) -> RenderOutput:
       extra_vars["learning_topic"] = learning_topic
       return super().render(**extra_vars)
   ```

3. **Extra Variables**: One-off variables can be passed directly to the render method.

### Template Validation

The library performs comprehensive validation to catch common issues early:

1. **Missing Variables**: Ensures all variables used in templates are defined either in the variables model or render method
2. **Unused Variables**: Identifies variables that are defined but never used in templates
3. **Template Syntax**: Validates Jinja2 template syntax at class definition time
4. **Type Checking**: Leverages Pydantic's type validation for all variables

### Working with External Templates

For complex prompts, you can load templates from external files:

```python
class ComplexPrompt(BasePrompt[ComplexVariables]):
    system_prompt_template = Path("templates/system_prompt.j2").read_text()

    prompt_template: str = Path("templates/user_prompt.j2").read_text()

```

> **Note**: With templating engines like Jinja2, you can normally hot reload templates, but this is not supported in typed-prompt as the templates are validated at class definition time.

## API Reference

### BasePrompt[T]

The foundational class for creating structured prompts.

#### Type Parameters

- `T`: A Pydantic BaseModel subclass defining the structure of template variables

#### Class Attributes

- `system_prompt_template`: Optional[str] - System prompt template
- `prompt_template`: str - User prompt template
- `variables`: T - Instance of the variables model

#### Methods

- `render(**extra_vars) -> RenderOutput`: Renders both prompts with provided variables

### RenderOutput

A NamedTuple providing structured access to rendered prompts:

- `system_prompt`: Optional[str] - The rendered system prompt
- `user_prompt`: str - The rendered user prompt

## Best Practices

### Template Organization

Structure your templates for maximum readability and maintainability:

1. **Use Docstrings for System Prompts**: When possible, define system prompts in class docstrings for better code organization:

   ```python
   class UserPrompt(BasePrompt[UserVariables]):
       """You are having a conversation with {{name}}, a {{age}}-year-old {{occupation}}."""
       prompt_template: str = "What would you like to discuss?"
   ```

2. **Separate Complex Templates**: For longer templates, use external files:

   ```python
    system_prompt_template = Path("templates/system_prompt.j2").read_text()
   ```

## Common Patterns

### Conditional Content

Use Jinja2's conditional syntax for dynamic content:

```python
class DynamicPrompt(BasePrompt[Variables]):
    prompt_template: str = """
    {% if expert_mode %}
    Provide a detailed technical explanation of {{topic}}
    {% else %}
    Explain {{topic}} in simple terms
    {% endif %}
    """
```

## Contributing

Contributions are welcome!

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## TODO

- [ ] Optionals will still render as `None` in the prompt.

- [ ] Make Jinja2 optional, (for very simple templating just use string formatting e.g `f"Hello {name}"`). Maybe shoulda started simpler lol.

- [ ] Output OpenAI compatible Message objects.

- [ ] The ability to define, not just a system prompt and a single prompt, but prompt chains. eg `system_prompt -> user_prompt -> assistant_response -> user_prompt -> assistant_response -> ...`
