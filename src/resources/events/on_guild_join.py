from ..structures.Bloxlink import Bloxlink

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
