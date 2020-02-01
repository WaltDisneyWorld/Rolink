from resources.structures.Bloxlink import Bloxlink # pylint: disable=import-error

@Bloxlink.command
class AutoRolesCommand(Bloxlink.Module):
    """completely updates members that join the server. by default, this is ENABLED."""

    def __init__(self):
        self.permissions = Bloxlink.Permissions().build("BLOXLINK_MANAGER")

    async def __main__(self, CommandArgs):
        response = CommandArgs.response
        guild_data = CommandArgs.guild_data

        toggle = not guild_data.get("autoRoles", True)

        guild_data["autoRoles"] = toggle

        await self.r.table("guilds").insert(guild_data, conflict="update").run()

        if toggle:
            await response.success("Successfully **enabled** Auto-Roles!")
        else:
            await response.success("Successfully **disabled** Auto-Roles!")
