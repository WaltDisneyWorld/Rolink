from resources.structures.Bloxlink import Bloxlink # pylint: disable=import-error
from resources.constants import ARROW # pylint: disable=import-error


class Test2AddonCommand(Bloxlink.Module):
    """test test test"""

    def __init__(self):
        pass

    async def __main__(self, CommandArgs):
        response = CommandArgs.response

        await response.send("hello from an add-on test2")
