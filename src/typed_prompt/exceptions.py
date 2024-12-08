class PromptValidationError(ValueError):
    """Base exception for prompt validation errors."""


class UndeclaredVariableError(PromptValidationError):
    """Raised when an undeclared variable is detected in the prompt.

    Both `prompt_template` and a `variables` model must be defined in the class."""

    def __init__(self) -> None:
        super().__init__("Undeclared Variables")


class MissingVariablesError(PromptValidationError):
    """Raised when variables used in the prompt template are not defined in the variables model."""

    def __init__(self, missing_variables: set[str]) -> None:
        self.missing_variables = missing_variables
        super().__init__(f"Missing required variables: {missing_variables}.")


class UnusedVariablesError(PromptValidationError):
    """Raised when variables defined in variables model or render method are not used"""

    def __init__(self, unused_variables: set[str]) -> None:
        self.unused_variables = unused_variables
        super().__init__(f"Unused variables detected: {unused_variables}.")
