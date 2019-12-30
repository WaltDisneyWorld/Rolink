class BloxlinkException(Exception):
    def __init__(self, arg=None, type="error"):
        self.type = type


class CancelCommand(BloxlinkException):
    pass

class Messages(CancelCommand):
    def __init__(self, *args, type="info", **kwargs):
        super().__init__(*args, type=type, **kwargs)

class Message(Messages):
    def __init__(self, *args, type="info", **kwargs):
        super().__init__(*args, type=type, **kwargs)

class Error(Messages):
    pass

class CancelledPrompt(CancelCommand):
    pass

class PermissionError(BloxlinkException):
    pass

class BadUsage(BloxlinkException):
    pass

class RobloxAPIError(BloxlinkException):
    pass

class RobloxNotFound(BloxlinkException):
    pass

class RobloxDown(BloxlinkException):
    pass

class UserNotVerified(BloxlinkException):
    pass
