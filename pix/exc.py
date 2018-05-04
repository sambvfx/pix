"""
Pix Exceptions
"""


class PIXError(Exception):
    """
    General PIX related error.
    """
    pass


class PIXInvalidProjectError(PIXError):
    """
    Error raised when a requested project does not exist.
    """
    pass


class PIXPluginPathError(PIXError):
    """
    Error raised when a specified plugin path cannot be loaded.
    """
    pass
