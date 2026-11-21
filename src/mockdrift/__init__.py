"""mockdrift: check mock call shapes against the real definitions."""

from .analyze import Finding, Report, analyze

__version__ = "0.1.0"
__all__ = ["Finding", "Report", "analyze", "__version__"]
