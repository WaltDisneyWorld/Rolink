from resources.structures.Bloxlink import Bloxlink # pylint: disable=import-error
from resources.constants import DEFAULTS, BROWN_COLOR # pylint: disable=import-error

post_event = Bloxlink.get_module("utils", attrs=["post_event"])

@Bloxlink.command
class DynamicRolesCommand(Bloxlink.Module):
    """automatically create missing group roles. by default, this is ENABLED."""

    def __init__(self):
        self.permissions = Bloxlink.Permissions().build("BLOXLINK_MANAGER")
        self.category = "Administration"
        self.hidden = True

    async def __main__(self, CommandArgs):
        response = CommandArgs.response

        author = CommandArgs.message.author

        guild = CommandArgs.message.guild
        guild_data = CommandArgs.guild_data

        toggle = not guild_data.get("dynamicRoles", DEFAULTS.get("dynamicRoles"))

        guild_data["dynamicRoles"] = toggle

        await self.r.table("guilds").insert(guild_data, conflict="update").run()

        if toggle:
            await post_event(guild, guild_data, "configuration", f"{author.mention} has **enabled** ``dynamicRoles``.", BROWN_COLOR)
            await response.success("Successfully **enabled** Dynamic Roles!")
        else:
            await post_event(guild, guild_data, "configuration", f"{author.mention} has **disabled** ``dynamicRoles``.", BROWN_COLOR)
            await response.success("Successfully **disabled** Dynamic Roles!")
