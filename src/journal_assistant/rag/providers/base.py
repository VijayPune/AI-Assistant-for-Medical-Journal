"""Shared provider configuration errors."""

class ProviderNotReady(RuntimeError):
    """Provider credentials or explicit external-processing approval are absent."""
