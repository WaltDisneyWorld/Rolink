class BloxlinkException(Exception):
    pass

class CancelCommand(BloxlinkException):
    pass

class Message(CancelCommand):
    pass

class CancelledPrompt(CancelCommand):
    pass

class PermissionError(BloxlinkException):
    pass

class BadUsage(BloxlinkException):
    pass
