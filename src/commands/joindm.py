from resources.structures.Bloxlink import Bloxlink # pylint: disable=import-error
from resources.constants import NICKNAME_TEMPLATES, WELCOME_MESSAGE, UNVERIFIED_TEMPLATES
from resources.exceptions import Message
from discord.errors import NotFound, HTTPException, Forbidden

@Bloxlink.command
class JoinDMCommand(Bloxlink.Module):
    """greets people who join the server. by default, this is ENABLED."""

    def __init__(self):
        self.permissions = Bloxlink.Permissions().build("BLOXLINK_MANAGER")
        self.category = "Administration"
        self.arguments = [{
            "prompt": "Would you like to alter/disable the DM messages of **verified** or **unverified** users?",
            "type": "choice",
            "choices": ("verified", "unverified"),
            "name": "subcommand"
        }]

    async def __main__(self, CommandArgs):
        subcommand = CommandArgs.parsed_args["subcommand"]
        if subcommand == "verified":
            await self.verified(CommandArgs)
        elif subcommand == "unverified":
            await self.unverified(CommandArgs)

    @Bloxlink.subcommand()
    async def verified(self, CommandArgs):
        """set the DM message of people who are VERIFIED on Bloxlink"""

        messages = []

        guild_data = CommandArgs.guild_data
        verifiedDM = guild_data.get("verifiedDM", WELCOME_MESSAGE)

        response = CommandArgs.response

        if verifiedDM:
            messages.append(await response.send("When people join your server and are **VERIFIED** on Bloxlink, they will "
                                f"receive this DM:"))
            messages.append(await response.send(f"```{verifiedDM}```"))

        try:
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

                await self.r.db("canary").table("guilds").insert(guild_data, conflict="update").run()

            elif parsed_args_1 == "disable":
                guild_data["verifiedDM"] = None

                await self.r.db("canary").table("guilds").insert(guild_data, conflict="replace").run()
        finally:
            try:
                for message in messages:
                    if message:
                        await message.delete()
            except (Forbidden, NotFound, HTTPException):
                pass

        raise Message(f"Successfully **{parsed_args_1}d** your DM message.", type="success")

    @Bloxlink.subcommand()
    async def unverified(self, CommandArgs):
        """set the DM message of people who are UNVERIFIED on Bloxlink"""

        messages = []

        guild_data = CommandArgs.guild_data
        unverifiedDM = guild_data.get("unverifiedDM")

        response = CommandArgs.response

        if unverifiedDM:
            messages.append(await response.send("When people join your server and are **UNVERIFIED** on Bloxlink, they will "
                                               f"receive this DM:"))
            messages.append(await response.send(f"```{unverifiedDM}```"))


        try:
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

                await self.r.db("canary").table("guilds").insert(guild_data, conflict="update").run()

            elif parsed_args_1 == "disable":
                guild_data["unverifiedDM"] = None

                await self.r.db("canary").table("guilds").insert(guild_data, conflict="replace").run()
        finally:
            try:
                for message in messages:
                    if message:
                        await message.delete()
            except (Forbidden, NotFound, HTTPException):
                pass


        raise Message(f"Successfully **{parsed_args_1}d** your DM message.", type="success")
