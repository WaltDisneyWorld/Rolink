from ..structures.Bloxlink import Bloxlink
from config import PREFIX # pylint: disable=no-name-in-module
from ..constants import PLAYING_STATUS
from discord import Status, Game


@Bloxlink.event
async def on_ready():
    Bloxlink.log(f"Logged in as {Bloxlink.user.name}")

    await Bloxlink.change_presence(status=Status.online, activity=Game(PLAYING_STATUS.format(prefix=PREFIX)))
