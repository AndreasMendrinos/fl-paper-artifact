class ProviderClientError(RuntimeError):
    """Base error raised by provider HTTP clients."""


class ProviderConnectionError(ProviderClientError):
    """Raised when the provider cannot be reached."""


class ProviderResponseError(ProviderClientError):
    """Raised when a provider returns an invalid response."""