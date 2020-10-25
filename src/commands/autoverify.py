from resources.structures.Bloxlink import Bloxlink # pylint: disable=import-error
from resources.constants import DEFAULTS, BROWN_COLOR # pylint: disable=import-error

post_event = Bloxlink.get_module("utils", attrs=["post_event"])

@Bloxlink.command
class AutoVerifyCommand(Bloxlink.Module):
    """give the Verified role to linked members when they join the server. by default, this is ENABLED."""

    def __init__(self):
        self.permissions = Bloxlink.Permissions().build("BLOXLINK_MANAGER")
        self.category = "Administration"
        self.hidden = True

    async def __main__(self, CommandArgs):
        response = CommandArgs.response
        author   = CommandArgs.message.author
        guild    = CommandArgs.message.guild
        locale   = CommandArgs.locale

        guild_data = CommandArgs.guild_data

        toggle = not guild_data.get("autoVerification", DEFAULTS.get("autoVerification"))

        guild_data["autoVerification"] = toggle

        await self.r.table("guilds").insert(guild_data, conflict="update").run()

        if toggle:
            await post_event(guild, guild_data, "configuration", locale("commands.autoverify.events.enable", user=author), BROWN_COLOR)
            await response.success(locale("commands.autoverify.enable"))
        else:
            await post_event(guild, guild_data, "configuration", locale("commands.autoverify.events.disable", user=author), BROWN_COLOR)
            await response.success(locale("commands.autoverify.disable"))
