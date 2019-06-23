class BloxlinkException(Exception):
    pass

class Message(BloxlinkException):
    pass

class PermissionError(BloxlinkException):
    pass

class CancelledPrompt(BloxlinkException):
    pass

class BadUsage(BloxlinkException):
    pass
