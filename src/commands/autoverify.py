from resources.structures.Bloxlink import Bloxlink # pylint: disable=import-error

@Bloxlink.command
class AutoVerifyCommand(Bloxlink.Module):
    """give the Verified role to linked members when they join the server. by default, this is ENABLED."""

    def __init__(self):
        self.permissions = Bloxlink.Permissions().build("BLOXLINK_MANAGER")
        self.category = "Administration"

    async def __main__(self, CommandArgs):
        response = CommandArgs.response
        guild_data = CommandArgs.guild_data

        toggle = not guild_data.get("autoVerification", True)

        guild_data["autoVerification"] = toggle

        await self.r.table("guilds").insert(guild_data, conflict="update").run()

        if toggle:
            await response.success("Successfully **enabled** Auto-Verification!")
        else:
            await response.success("Successfully **disabled** Auto-Verification!")
