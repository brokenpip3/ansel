class AnselError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class ConfigError(AnselError):
    def __init__(self, message: str):
        super().__init__(f"Configuration error: {message}")


class RepoError(AnselError):
    def __init__(self, message: str):
        super().__init__(f"Repository error: {message}")


class TemplateError(AnselError):
    def __init__(self, message: str):
        super().__init__(f"Template error: {message}")
