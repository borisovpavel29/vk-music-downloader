class VkApiError(RuntimeError):
    """Raised on VK API errors."""


class HlsParseError(RuntimeError):
    """Raised when HLS playlist parsing fails."""


class MissingDependencyError(RuntimeError):
    """Raised when optional dependency is missing."""

