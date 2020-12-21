from resources.structures.Bloxlink import Bloxlink # pylint: disable=import-error
from resources.constants import NICKNAME_TEMPLATES, DEFAULTS, UNVERIFIED_TEMPLATES, BROWN_COLOR # pylint: disable=import-error
from resources.exceptions import Message # pylint: disable=import-error
from discord.errors import NotFound, HTTPException, Forbidden


post_event = Bloxlink.get_module("utils", attrs=["post_event"])
set_guild_value = Bloxlink.get_module("cache", attrs=["set_guild_value"])


@Bloxlink.command
class JoinDMCommand(Bloxlink.Module):
    """greets people who join the server. by default, this is ENABLED for verified members."""

    def __init__(self):
        self.permissions = Bloxlink.Permissions().build("BLOXLINK_MANAGER")
        self.category = "Administration"
        self.arguments = [{
            "prompt": "Would you like to alter/disable the DM messages for **verified** or **unverified** users?",
            "type": "choice",
            "choices": ("verified", "unverified"),
            "name": "subcommand"
        }]
        self.hidden = True

    async def __main__(self, CommandArgs):
        subcommand = CommandArgs.parsed_args["subcommand"]
        if subcommand == "verified":
            await self.verified(CommandArgs)
        elif subcommand == "unverified":
            await self.unverified(CommandArgs)

    @Bloxlink.subcommand()
    async def verified(self, CommandArgs):
        """set the DM message of people who are VERIFIED on Bloxlink"""

        guild_data = CommandArgs.guild_data
        verifiedDM = guild_data.get("verifiedDM", DEFAULTS.get("welcomeMessage"))

        author = CommandArgs.message.author
        guild = CommandArgs.message.guild

        response = CommandArgs.response

        if verifiedDM:
            response.delete(await response.send("When people join your server and are **VERIFIED** on Bloxlink, they will "
                                               f"receive this DM:"))
            response.delete(await response.send(f"```{verifiedDM}```"))

        parsed_args_1 = (await CommandArgs.prompt([{
            "prompt": "Would you like to **change** the DM people get when they join and are verified, or "
                        "would you like to **disable** this feature?\n\nPlease specify: (change, disable)",
            "name": "option",
            "type": "choice",
            "choices": ("change", "disable")
        }]))["option"]

        if parsed_args_1 == "change":
            parsed_args_2 = (await CommandArgs.prompt([{
                "prompt": "What would you like the text of the Verified Join DM to be? You may use "
                            f"these templates: ```{NICKNAME_TEMPLATES}```",
                "name": "text",
                "formatting": False
            }]))["text"]

            guild_data["verifiedDM"] = parsed_args_2
            await set_guild_value(guild, "verifiedDM", parsed_args_2)

            await self.r.table("guilds").insert(guild_data, conflict="update").run()

        elif parsed_args_1 == "disable":
            guild_data["verifiedDM"] = None
            await set_guild_value(guild, "verifiedDM", None)

            await self.r.table("guilds").insert(guild_data, conflict="replace").run()

        await post_event(guild, guild_data, "configuration", f"{author.mention} ({author.id}) has **changed** the ``joinDM`` option for ``verified`` members.", BROWN_COLOR)

        raise Message(f"Successfully **{parsed_args_1}d** your DM message.", type="success")

    @Bloxlink.subcommand()
    async def unverified(self, CommandArgs):
        """set the DM message of people who are UNVERIFIED on Bloxlink"""

        guild = CommandArgs.message.guild
        guild_data = CommandArgs.guild_data
        unverifiedDM = guild_data.get("unverifiedDM")

        response = CommandArgs.response

        if unverifiedDM:
            response.delete(await response.send("When people join your server and are **UNVERIFIED** on Bloxlink, they will "
                                               f"receive this DM:"))
            response.delete(await response.send(f"```{unverifiedDM}```"))


        parsed_args_1 = (await CommandArgs.prompt([{
            "prompt": "Would you like to **change** the DM people get when they join and are unverified, or "
                        "would you like to **disable** this feature?\n\nPlease specify: (change, disable)",
            "name": "option",
            "type": "choice",
            "choices": ("change", "disable")
        }]))["option"]

        if parsed_args_1 == "change":
            parsed_args_2 = (await CommandArgs.prompt([{
                "prompt": "What would you like the text of the Unverified Join DM to be? You may use "
                            f"these templates: ```{UNVERIFIED_TEMPLATES}```",
                "name": "text",
                "formatting": False
            }]))["text"]

            guild_data["unverifiedDM"] = parsed_args_2
            await set_guild_value(guild, "unverifiedDM", parsed_args_2)

            await self.r.table("guilds").insert(guild_data, conflict="update").run()

        elif parsed_args_1 == "disable":
            guild_data["unverifiedDM"] = None
            await set_guild_value(guild, "unverifiedDM", None)

            await self.r.table("guilds").insert(guild_data, conflict="replace").run()

        author = CommandArgs.message.author
        guild = CommandArgs.message.guild

        await post_event(guild, guild_data, "configuration", f"{author.mention} ({author.id}) has **changed** the ``joinDM`` option for ``unverified`` members.", BROWN_COLOR)

        raise Message(f"Successfully **{parsed_args_1}d** your DM message.", type="success")
