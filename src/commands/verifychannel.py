from resources.structures.Bloxlink import Bloxlink # pylint: disable=import-error
from resources.exceptions import PermissionError, Error # pylint: disable=import-error
from resources.constants import DEFAULTS # pylint: disable=import-error
from discord.utils import find
from discord.errors import Forbidden, NotFound, HTTPException

@Bloxlink.command
class VerifyChannelCommand(Bloxlink.Module):
    """create a special channel where messages are deleted"""

    def __init__(self):
        self.permissions = Bloxlink.Permissions().build("BLOXLINK_MANAGER")
        self.aliases = ["verificationchannel"]
        self.category = "Administration"

    async def __main__(self, CommandArgs):
        response = CommandArgs.response
        guild_data = CommandArgs.guild_data
        prefix = CommandArgs.prefix

        guild = CommandArgs.message.guild

        async with response.loading():

            try:
                category = find(lambda c: c.name == "Verification", guild.categories) or \
                        await guild.create_category("Verification")

                verify_info = find(lambda t: t.name == "verify-instructions", category.channels) or \
                            await guild.create_text_channel("verify-instructions", category=category)

                verify_channel = find(lambda t: t.name == "verify", category.channels) or \
                                await guild.create_text_channel("verify", category=category)

                sample_channel = await guild.create_text_channel("sample-channel")

            except Forbidden:
                raise PermissionError("I was unable to create the necessary channels. Please ensure I have the "
                                    "``Manage Channels`` permission.")

            except HTTPException:
                raise Error("You have too many channels or categories! Please delete some before continuing.")

            try:
                await verify_info.send("This server uses Bloxlink to manage Roblox verification. In "
                                    "order to unlock all the features of this server, you'll need "
                                    "to verify your Roblox account with your Discord account!\n\nTo "
                                    f"do this, run ``{prefix}verify`` in {verify_channel.mention} and follow the instructions.")

                await sample_channel.send("This is a sample channel that only Verified users " \
                                        "can read. This channel is not important, you may freely delete it.\n" \
                                        "To create another sample channel, right click this channel and click 'Clone " \
                                        "Text Channel', or just run this command again.")

            except (Forbidden, NotFound):
                raise PermissionError("I was unable to send messages to the created channels. Please give me the "
                                    "proper permissions.")


            try:
                await verify_info.set_permissions(guild.me, send_messages=True, read_messages=True)

                verified_role_name = guild_data.get("verifiedRoleName", DEFAULTS.get("verifiedRoleName"))

                for role in guild.roles:
                    if role.name != guild.me.name:
                        await verify_info.set_permissions(role, send_messages=False, read_messages=True)
                        await verify_channel.set_permissions(role, send_messages=True, read_messages=True)

                    if role.name == verified_role_name:
                        for target, overwrite in sample_channel.overwrites.items():
                            await sample_channel.set_permissions(target, overwrite=None)

                        await sample_channel.set_permissions(guild.default_role, send_messages=False, read_messages=False)
                        await sample_channel.set_permissions(role, send_messages=True, read_messages=True)


            except Forbidden:
                raise PermissionError("Unable to set permissions to the channels. Please ensure I have the "
                                    "``Manage Channels`` and ``Manage Roles`` permission.")

            except NotFound:
                raise Error("Please do not delete the created channels while I'm setting them up...")


        await self.r.table("guilds").insert({
            "id": str(guild.id),
            "verifyChannel": str(verify_channel.id)
        }, conflict="update").run()

        await response.success(f"All done! Your new verification channel is {verify_channel.mention} and " \
                                "is now managed by Bloxlink.")