from ..structures.Bloxlink import Bloxlink # pylint: disable=import-error
from config import BOTS # pylint: disable=import-error, no-name-in-module
from discord.errors import NotFound


@Bloxlink.module
class GuildRemoveEvent(Bloxlink.Module):
    def __init__(self):
        pass

    async def __setup__(self):

        @Bloxlink.event
        async def on_guild_remove(guild):
            guild_id = str(guild.id)

            hasBot = False

            for bot_id in BOTS.values():
                try:
                    await guild.fetch_member(bot_id)
                except NotFound:
                    pass
                else:
                    hasBot = True

            if not hasBot:
                guild_data = await self.r.table("guilds").get(guild_id).run() or {"id": guild_id}

                guild_data.pop("hasBot", None)
                await self.r.table("guilds").insert(guild_data, conflict="replace").run()
