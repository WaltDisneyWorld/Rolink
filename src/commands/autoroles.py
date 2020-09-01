from resources.structures.Bloxlink import Bloxlink # pylint: disable=import-error
from resources.constants import DEFAULTS, BROWN_COLOR # pylint: disable=import-error

post_event = Bloxlink.get_module("utils", attrs=["post_event"])


@Bloxlink.command
class AutoRolesCommand(Bloxlink.Module):
    """completely update members that join the server. by default, this is ENABLED."""

    def __init__(self):
        self.permissions = Bloxlink.Permissions().build("BLOXLINK_MANAGER")
        self.category = "Administration"
        self.hidden = True

    async def __main__(self, CommandArgs):
        response = CommandArgs.response

        author = CommandArgs.message.author

        guild = CommandArgs.message.guild
        guild_data = CommandArgs.guild_data

        toggle = not guild_data.get("autoRoles", DEFAULTS.get("autoRoles"))

        guild_data["autoRoles"] = toggle

        await self.r.table("guilds").insert(guild_data, conflict="update").run()

        if toggle:
            await post_event(guild, guild_data, "configuration", f"{author.mention} has **enabled** ``autoRoles``.", BROWN_COLOR)
            await response.success("Successfully **enabled** Auto-Roles!")
        else:
            await post_event(guild, guild_data, "configuration", f"{author.mention} has **disabled** ``autoRoles``.", BROWN_COLOR)
            await response.success("Successfully **disabled** Auto-Roles!")
