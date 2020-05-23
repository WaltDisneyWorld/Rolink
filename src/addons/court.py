from resources.constants import ARROW # pylint: disable=import-error


class TestCourtCommand:
    """test court command"""
    pass


class CourtAddon:
    """provides commands for managing judicial proceedings"""

    def __init__(self):
        self.commands = [TestCourtCommand]

    def load_commands(self):
        return self.commands

    def __str__(self):
        return f"**{self.__class__.__name__.replace('Addon', '').lower()}** {ARROW} {self.__doc__}"
