"""typed-prompt: A type-safe prompt management system for large language models.

This module provides a structured way to create, validate, and manage prompts for large
language models while maintaining type safety and template validation. It combines
Pydantic's type validation with Jinja2's templating system to create a robust
prompt management solution.

The library enforces a clear separation between:
- Prompt content (system and user prompts)
- Variables (through Pydantic models)
- Configuration (for model parameters)

Key Features:
    - Type-safe prompt templates using Pydantic models
    - Built-in template validation during class definition
    - Support for system prompts and user prompts
    - Flexible variable handling with optional parameters
    - Configuration management for model parameters
    - Comprehensive validation including unused variable detection
"""

from typed_prompt import exceptions
from typed_prompt.template import BasePrompt, RenderedOutput

__all__ = ["BasePrompt", "RenderedOutput", "exceptions"]
