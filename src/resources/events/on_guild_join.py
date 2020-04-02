from ..structures.Bloxlink import Bloxlink
from resources.exceptions import UserNotVerified # pylint: disable=import-error
from discord.errors import Forbidden, HTTPException
from resources.constants import WELCOME_MESSAGE

validate_guild = Bloxlink.get_module("utils", attrs=["validate_guild"])


@Bloxlink.module
class GuildJoinEvent(Bloxlink.Module):
    def __init__(self):
        pass

    async def __setup__(self):

        @Bloxlink.event
        async def on_guild_join(guild):
            if not await validate_guild(guild):
                await guild.leave()
