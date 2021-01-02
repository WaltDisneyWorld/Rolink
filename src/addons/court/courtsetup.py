from resources.structures.Bloxlink import Bloxlink # pylint: disable=import-error
from resources.exceptions import Error # pylint: disable=import-error
from discord.utils import find
from discord.errors import Forbidden
from discord import Embed


class CourtSetupCommand(Bloxlink.Module):
    """set-up your judicial system"""

    def __init__(self):
        self.developer = True
        self.permissions = Bloxlink.Permissions().build("BLOXLINK_MANAGER")
        self.category = "Court Addon"

    async def __main__(self, CommandArgs):
        prefix   = CommandArgs.prefix
        guild    = CommandArgs.message.guild
        response = CommandArgs.response

        my_permissions = guild.me.guild_permissions

        if not my_permissions.manage_channels:
            raise Error("I need permission to create channels!")

        setup_args = await CommandArgs.prompt([
            {
                "prompt": "**Thank you for choosing Bloxlink!** In a few simple prompts, **we'll configure this add-on "
                          "for your server.**\n\n**The Court Add-on**\nThis add-on allows you to assign judges which have "
                          "the power create cases within your Discord server. Created cases reside in Discord channels where "
                          "the messages are all saved and can be exported later.",
                "name": "_",
                "footer": "Say **next** to continue.",
                "type": "choice",
                "choices": ["next"],
                "embed_title": "Setup Prompt"
            },
            {
                "prompt": "Which **role(s)** are considered the ``Judge`` roles? Members with these roles will be able to "
                          "create new cases and use certain judicial administrative commands.",
                "name": "judge_roles",
                "type": "role",
                "multiple": True,
                "embed_title": "Setup Prompt"
            },
            {
                "prompt": "Which ``channel`` would you like to use for logging case events?",
                "name": "log_channel",
                "footer": "Say **skip** to skip this step.",
                "exceptions": ("skip",),
                "type": "channel",
            },
            {
                "prompt": "Please specify the **groups** to use with your set-up.\n\nA group holds members for each trial. For example, typical groups "
                          "for a USA style court room include the ``prosecution``, ``defence``, ``jurors``, and ``witnesses``. Please **give a list separated by "
                          "commas** of your group names.\n\nFor example, you may write: ``prosecution, defense, jurors``\n\nJudges will be able to add people into these groups to fit their trial.\n\n__It's fine if you include groups "
                          "which aren't used__, groups __can be__ blank. ",
                "name": "groups",
                "type": "list",
            }
        ]) # TODO: ask for Trello information

        addon_data = await self.r.db("bloxlink").table("addonData").get(str(guild.id)).run() or {}
        court_data = addon_data.get("court") or {}

        category = None

        if not court_data.get("category"):
            try:
                category = find(lambda c: c.name == "Cases", guild.categories) or \
                           await guild.create_category("Cases")
            except Forbidden:
                raise Error("I need permission to create channels!")

        judge_roles = setup_args["judge_roles"]
        log_channel = setup_args["log_channel"]
        groups      = setup_args["groups"]

        addon_data["court"] = {
            "judgeRoles": [str(x.id) for x in judge_roles],
            "logChannel": log_channel != "skip" and str(log_channel.id),
            "category": category and str(category.id) or addon_data.get("court", {}).get("category"),
            "groups": groups
        }

        await self.r.table("addonData").insert({
            "id": str(guild.id),
            **addon_data
        }, conflict="update").run()


        #embed = Embed(title="Additional Information") TODO: post info with all the available commands


        await response.success(f"Successfully saved your **Court add-on!** Now, judges (people with the {', '.join([r.mention for r in judge_roles])} role(s)) will be "
                               f"able to run ``{prefix}case create`` to create a new case chat.") # TODO: set AllowedMentions so the bot doesn't role ping anyone

