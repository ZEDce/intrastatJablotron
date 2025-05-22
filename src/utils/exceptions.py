"""
Custom exceptions pre Intrastat aplikáciu.
"""


class IntrastatError(Exception):
    """Základná exception pre Intrastat aplikáciu."""
    pass


class ConfigurationError(IntrastatError):
    """Exception pre chyby v konfigurácii."""
    pass


class PDFProcessingError(IntrastatError):
    """Exception pre chyby pri spracovaní PDF súborov."""
    pass


class AIAnalysisError(IntrastatError):
    """Exception pre chyby pri AI analýze."""
    pass


class DataValidationError(IntrastatError):
    """Exception pre chyby pri validácii dát."""
    pass


class CSVProcessingError(IntrastatError):
    """Exception pre chyby pri práci s CSV súbormi."""
    pass


class WeightCalculationError(IntrastatError):
    """Exception pre chyby pri výpočte hmotností."""
    pass


class CustomsCodeError(IntrastatError):
    """Exception pre chyby pri priradení colných kódov."""
    pass


class FileOperationError(IntrastatError):
    """Exception pre chyby pri operáciách so súbormi."""
    pass


class RateLimitExceededError(IntrastatError):
    """Exception pre prekročenie rate limitu API."""
    pass 