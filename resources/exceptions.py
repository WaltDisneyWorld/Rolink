class BloxlinkException(Exception):
    """Parent exception for all Bloxlink exceptions"""

    pass

class CancelledPrompt(BloxlinkException):
    """Raised when a user cancels the prompt"""

    pass

class RobloxAPIError(BloxlinkException):
    """Raised if the Roblox API is down"""

    pass

class PermissionError(BloxlinkException):
    """Raised if Bloxlink does not have permission to do an action"""

    pass

class BloxlinkNotFound(BloxlinkException):
    """Parent exception for all NotFound errors"""

    pass

class GroupNotFound(BloxlinkNotFound):
    """Raised if a group doesn't exist"""

    pass

class UserNotFound(BloxlinkNotFound):
    """Raised if a Roblox Username doesn't exist"""

    pass
