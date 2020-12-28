from resources.constants import ARROW # pylint: disable=import-error

class VerificationAddon:
    """core verification functionality"""

    def __init__(self):
        self.default_enabled = True
        self.toggleable = False

    def __str__(self):
        return self.__class__.__name__.replace("Addon", "").lower()

    def __repr__(self):
        return f"**{self.__str__()}** {ARROW} {self.__doc__}"
