from resources.structures.Bloxlink import Bloxlink # pylint: disable=import-error

@Bloxlink.command
class DynamicRolesCommand(Bloxlink.Module):
    """automatically create missing group roles. by default, this is ENABLED."""

    def __init__(self):
        self.permissions = Bloxlink.Permissions().build("BLOXLINK_MANAGER")

    async def __main__(self, CommandArgs):
        response = CommandArgs.response
        guild_data = CommandArgs.guild_data

        toggle = not guild_data.get("dynamicRoles", True)

        guild_data["dynamicRoles"] = toggle

        await self.r.table("guilds").insert(guild_data, conflict="update").run()

        if toggle:
            await response.success("Successfully **enabled** Dynamic Roles!")
        else:
            await response.success("Successfully **disabled** Dynamic Roles!")
