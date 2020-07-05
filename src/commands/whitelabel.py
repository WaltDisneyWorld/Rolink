from resources.structures.Bloxlink import Bloxlink # pylint: disable=import-error
from resources.exceptions import Message, Error # pylint: disable=import-error
from discord import Object

is_premium = Bloxlink.get_module("utils", attrs=["is_premium"])


@Bloxlink.command
class WhiteLabelCommand(Bloxlink.Module):
    """change the profile picture and name of _most_ Bloxlink responses"""

    def __init__(self):
        self.permissions = Bloxlink.Permissions().build("BLOXLINK_MANAGER")
        self.category = "Premium"
        self.hidden = True
        self.aliases = ["custombot", "customizebot"]
        self.free_to_use = True

    async def __main__(self, CommandArgs):
        response = CommandArgs.response
        guild_data = CommandArgs.guild_data
        prefix = CommandArgs.prefix

        guild = CommandArgs.message.guild

        premium_status, _ = await is_premium(guild.owner or Object(id=guild.owner_id))

        if not premium_status.features.get("premium"):
            if guild_data.get("customBot"):
                return await self.disable(CommandArgs)

            raise Error("This command is reserved for __Bloxlink Premium subscribers!__ You may find out "
                        f"more information with the ``{prefix}donate`` command.")



        if guild_data.get("customBot"):
            chosen_option = (await CommandArgs.prompt([{
                "prompt": "You already have your bot customized! Would you like to "
                          "**disable** the customization, or **customize** it again?",
                "name": "choice",
                "type": "choice",
                "choices": ("disable", "customize"),
                "footer": "Say **disable** or **customize**."
            }]))["choice"]

            if chosen_option == "disable":
                return await self.disable(CommandArgs)


        parsed_args = await CommandArgs.prompt([
            {
                "prompt": "We will now walk you through customizing the responses "
                          "of Bloxlink.\nThis will change the **username** and **profile picture** "
                          "of __most bot responses__ with the power of Webhooks! The bot will "
                          "appear the same in the member list since, officially, the bot remains the same.",
                "name": "_",
                "footer": "Say anything to continue."
            },
            {
                "prompt": "What would you like the bot to be called? This will change the **username** "
                          "of the responses. Examples include your Group/entity name, game name, etc.",
                "name": "bot_name",
                "max": 32
            },
            {
                "prompt": "Please either provide a **direct link** to your entity logo, or **drag the image** "
                          "to your chat. If you drag the image to your chat, then the image must not be "
                          "deleted, or the responses will remain unchanged!",
                "name": "bot_avatar",
                "type": "image",
                "delete_original": False
            }
        ])

        bot_name = parsed_args["bot_name"]
        bot_avatar = parsed_args["bot_avatar"]

        guild_data["customBot"] = {
            "name": bot_name,
            "avatar": bot_avatar
        }
        await self.r.db("canary").table("guilds").insert(guild_data, conflict="update").run()

        await response.success("Successfully saved your new **white-label** configuration!")


    @Bloxlink.subcommand()
    async def disable(self, CommandArgs):
        """disable the white-label responses"""

        response = CommandArgs.response
        guild_data = CommandArgs.guild_data

        if not guild_data.get("customBot"):
            raise Message("You have no white-label configuration saved!", type="silly")

        guild_data.pop("customBot", None)
        await self.r.db("canary").table("guilds").insert(guild_data, conflict="replace").run()

        await response.success("Successfully disabled your **white-label** configuration!")
