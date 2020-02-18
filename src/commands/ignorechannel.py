from resources.structures.Bloxlink import Bloxlink # pylint: disable=import-error

@Bloxlink.command
class IgnoreChannelCommand(Bloxlink.Module):
    """toggle commands in the current channel by non-admins"""

    def __init__(self):
        self.permissions = Bloxlink.Permissions().build("BLOXLINK_MANAGER")

    async def __main__(self, CommandArgs):
        channel = CommandArgs.message.channel
        channel_id = str(channel.id)

        guild = CommandArgs.message.guild

        response = CommandArgs.response
        guild_data = CommandArgs.guild_data

        ignored_channels = guild_data.get("ignoredChannels", {})
        ignored_channels[channel_id] = not ignored_channels.get(channel_id, False)

        disabled = bool(ignored_channels[channel_id])

        await self.r.table("guilds").insert({
            "id": str(guild.id),
            "ignoredChannels": ignored_channels
        }, conflict="update").run()

        if disabled:
            await response.success("Successfully **disabled** commands from this channel by non-admins.\n"
                                   "If you would like to grant a certain person access to use commands, give them a role called "
                                   "``Bloxlink Bypass``."
            )
        else:
            await response.success("Successfully **enabled** commands in this channel.")
