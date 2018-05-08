"""
Pix Exceptions
"""


class PIXError(Exception):
    """
    General PIX related error.
    """
    pass


class PIXLoginError(PIXError):
    """
    Error raised when there are issues logging into PIX.
    """
    pass
