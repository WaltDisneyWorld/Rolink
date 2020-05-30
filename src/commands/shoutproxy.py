from resources.structures.Bloxlink import Bloxlink # pylint: disable=import-error
from resources.exceptions import Error, RobloxNotFound # pylint: disable=import-error
from resources.constants import ARROW # pylint: disable=import-error
from discord import Embed
import re

get_group = Bloxlink.get_module("roblox", attrs=["get_group"])
roblox_group_regex = re.compile(r"roblox.com/groups/(\d+)/")


TEMPLATES = \
	"{group-shout} \u2192 changes to the group shout\n" \
	"{group-name} \u2192 changes to the group name\n" \
	"{group-id} \u2192 changes to the group ID\n" \
	"{roblox-name} \u2192 changes to the shouter's roblox name\n" \
	"{roblox-id} \u2192 changes the shouter's roblox ID\n" \
	"{group-rank} \u2192 changes to the shouter's group rank\n" \
    "\nNote: the {} must be included in the template."

@Bloxlink.command
class ShoutProxyCommand(Bloxlink.Module):
    """relay Roblox group shouts to a Discord channel"""

    @staticmethod
    async def validate_group(message, content):
        if content.lower() in ("skip", "next"):
            return "skip"

        regex_search = roblox_group_regex.search(content)

        if regex_search:
            group_id = regex_search.group(1)
        else:
            group_id = content

        try:
            group = await get_group(group_id, rolesets=True)
        except RobloxNotFound:
            return None, "No group was found with this ID. Please try again."

        return group

    def __init__(self):
        self.permissions = Bloxlink.Permissions().build("BLOXLINK_MANAGER")
        self.arguments = [
            {
                "prompt": "This command will relay group shouts from a Roblox group to your Discord channel.\n"
                          "For this to work, the group shouts must be VISIBLE to guests.\n\nWhich channel would "
                          "you like to use for group shouts? Please either mention the channel or say the channel name.\n"
                          "Optionally, say ``clear`` to remove your proxied channel.",
                "name": "channel",
                "type": "channel",
                "exceptions": ["clear"]
            }
        ]
        self.category = "Premium"
        self.hidden = True


    async def __main__(self, CommandArgs):
        guild = CommandArgs.message.guild
        arg = CommandArgs.parsed_args["channel"]
        response = CommandArgs.response

        group_shout_data = None

        if arg == "clear":
            return await self.clear(CommandArgs)

        parsed_args_1 = await CommandArgs.prompt([
            {
                "prompt": "Please specify the Roblox Group to relay shouts from. You may paste the Group URL, "
                          "or paste the Group ID.",
                "name": "group",
                "validation": self.validate_group
            },
            {

                "prompt": "Would you like to **customize** how the shout post looks "
                          "like, or use an **embed** with general metadata already attached?",
                "name": "format",
                "type": "choice",
                "choices": ["customize", "embed"]
            },
        ])

        if parsed_args_1["format"] == "embed":
            prepend = (await CommandArgs.prompt([
                {
                    "prompt": "Would you like to prepend some text before the shout embed?\n"
                              "Possible use cases: ``@everyone`` before the shout embed to tag everyone.\n\n"
                              "Say the text to prepend, or say ``skip`` to not prepend any text.",
                    "name": "prepend"
                }
            ]))["prepend"]

            if prepend in ("next", "skip", "done"):
                prepend = None

            group_shout_data = {
                "default": True,
                "group": parsed_args_1["group"].group_id,
                "channel": str(arg.id),
                "prependContent": prepend,
            }
        else:
            parsed_args = await CommandArgs.prompt([
                {
                    "prompt": "How would you like to format your group shouts? Please format your message "
                             f"using these templates: ```{TEMPLATES}```",
                    "name": "format",
                    "formatting": False
                },
                {
                    "prompt": "Would you like Bloxlink to automatically strip mentions (pings) "
                              "from the shout so they don't ping anyone?",
                    "name": "clean_content",
                    "type": "choice",
                    "choices": ["yes", "no"]
                }
            ])

            group_shout_data = {
                "format": parsed_args["format"],
                "group": parsed_args_1["group"].group_id,
                "cleanContent": parsed_args["clean_content"] == "yes",
                "channel": str(arg.id),
                "default": False,
            }

        await self.r.db("canary").table("guilds").insert({
            "id": str(guild.id),
            "groupShoutChannel": str(arg.id)
        }, conflict="update").run()

        await self.r.db("canary").table("groupShouts").insert({
            "id": str(guild.id),
            **group_shout_data
        }, conflict="update").run()

        await response.success("Enabled group shout relaying! Note: for this to work, your group shouts __MUST BE PUBLIC.__")


    @Bloxlink.subcommand()
    async def clear(self, CommandArgs):
        guild_data = CommandArgs.guild_data
        response = CommandArgs.response
        guild = CommandArgs.message.guild
        guild_id = str(guild.id)

        shout_channel = guild_data.get("groupShoutChannel")

        if shout_channel:
            await self.r.db("canary").table("groupShouts").get(guild_id).delete().run()

            guild_data.pop("groupShoutChannel")

            await self.r.db("canary").table("guilds").get(guild_id).replace(guild_data).run()

            await response.success("Successfully cleared your Shout Channel!")
        else:
            await response.silly("You have no saved Group Channel!")
