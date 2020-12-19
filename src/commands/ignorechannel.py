from resources.structures.Bloxlink import Bloxlink # pylint: disable=import-error
from resources.constants import BROWN_COLOR # pylint: disable=import-error

post_event = Bloxlink.get_module("utils", attrs=["post_event"])
set_guild_value = Bloxlink.get_module("cache", attrs=["set_guild_value"])



@Bloxlink.command
class IgnoreChannelCommand(Bloxlink.Module):
    """toggle commands in the current channel for non-admins"""

    def __init__(self):
        self.permissions = Bloxlink.Permissions().build("BLOXLINK_MANAGER")
        self.category = "Administration"
        self.aliases = ["ignore"]

    async def __main__(self, CommandArgs):
        channel = CommandArgs.message.channel
        channel_id = str(channel.id)

        guild  = CommandArgs.message.guild
        author = CommandArgs.message.author

        response   = CommandArgs.response
        guild_data = CommandArgs.guild_data

        ignored_channels = guild_data.get("ignoredChannels", {})
        ignored_channels[channel_id] = not ignored_channels.get(channel_id, False)

        disabled = bool(ignored_channels[channel_id])

        await self.r.table("guilds").insert({
            "id": str(guild.id),
            "ignoredChannels": ignored_channels
        }, conflict="update").run()

        await set_guild_value(guild, "ignoredChannels", ignored_channels)

        if disabled:
            await response.success("Successfully **disabled** commands from this channel for non-admins.\n"
                                   "If you would like to grant a certain person access to use commands, give them a role called "
                                   "``Bloxlink Bypass``."
            )
            await post_event(guild, guild_data, "configuration", f"{author.mention} ({author.id}) has **disabled** all commands for channel {channel.mention}.", BROWN_COLOR)
        else:
            await response.success("Successfully **enabled** commands in this channel.")
            await post_event(guild, guild_data, "configuration", f"{author.mention} ({author.id}) has **enabled** all commands for channel {channel.mention}.", BROWN_COLOR)
