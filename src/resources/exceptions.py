class BloxlinkException(Exception):
    pass

class PermissionError(BloxlinkException):
    pass

class CancelledPrompt(BloxlinkException):
    pass
