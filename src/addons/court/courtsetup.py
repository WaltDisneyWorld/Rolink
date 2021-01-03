from resources.structures.Bloxlink import Bloxlink # pylint: disable=import-error
from resources.exceptions import Error # pylint: disable=import-error
from discord.utils import find
from discord.errors import Forbidden
from discord import Embed, PermissionOverwrite, AllowedMentions


class CourtSetupCommand(Bloxlink.Module):
    """set-up your judicial system"""

    def __init__(self):
        self.permissions = Bloxlink.Permissions().build("BLOXLINK_MANAGER")
        self.category = "Court Addon"

    async def __main__(self, CommandArgs):
        prefix   = CommandArgs.prefix
        guild    = CommandArgs.message.guild
        response = CommandArgs.response

        my_permissions = guild.me.guild_permissions

        if not (my_permissions.manage_channels and my_permissions.manage_roles):
            raise Error("I need both the ``Manage Channels`` and ``Manage Roles`` permissions.")

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
                "prompt": "Which ``category`` would you like to use for archiving closed cases? If you skip this, then old cases "
                          "will simply be deleted.",
                "name": "archive_category",
                "footer": "Say **skip** to skip this step.",
                "exceptions": ("skip",),
                "type": "category",
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

        judge_roles     = setup_args["judge_roles"]
        log_channel     = setup_args["log_channel"]
        groups          = setup_args["groups"]
        archive_category = setup_args["archive_category"]

        addon_data = await self.r.db("bloxlink").table("addonData").get(str(guild.id)).run() or {}
        court_data = addon_data.get("court") or {}

        category = None
        create_category = False

        if archive_category != "skip":
            overwrites = {
                guild.default_role: PermissionOverwrite(read_messages=False),
                guild.me:           PermissionOverwrite(read_messages=True),
            }
            overwrites.update({k:PermissionOverwrite(read_messages=True) for k in judge_roles})

            try:
                await archive_category.edit(overwrites=overwrites)
            except Forbidden:
                raise Error("I need both the ``Manage Channels`` and ``Manage Roles`` permissions.")

        if court_data.get("category"):
            category = find(lambda c: c.id == int(court_data["category"]), guild.categories)

            if not category:
                create_category = True
        else:
            create_category = True

        if create_category:
            overwrites = {
                guild.default_role: PermissionOverwrite(read_messages=False),
                guild.me:           PermissionOverwrite(read_messages=True),
            }
            overwrites.update({k:PermissionOverwrite(read_messages=True) for k in judge_roles})

            try:
                category = find(lambda c: c.name == "Cases", guild.categories) or \
                           await guild.create_category("Cases", overwrites=overwrites)

            except Forbidden:
                raise Error("I need both the ``Manage Channels`` and ``Manage Roles`` permissions.")

        addon_data["court"] = {
            "judgeRoles": [str(x.id) for x in judge_roles],
            "logChannel": str(log_channel.id) if log_channel != "skip" else None,
            "archiveCategory": str(archive_category.id) if archive_category != "skip" else None,
            "category": str(category.id) if category else None,
            "groups": groups
        }

        await self.r.table("addonData").insert({
            "id": str(guild.id),
            **addon_data
        }, conflict="update").run()


        embed = Embed(title="Additional Information", description=f"- Use ``{prefix}case create`` to make a new case chat.\n"
                                                                  "- Need to change your groups? You will need to run this command again.\n"
                                                                  f"- It's recommended to give your cases IDs! You'll be able to run ``{prefix}case lookup`` to find its information.\n"
                                                                  f"- You will need to add case members with ``{prefix}case add`` and assign them to a group. Remove them with ``{prefix}case remove``.\n"
                                                                  f"- Run ``{prefix}case end`` inside your case chat to archive the case.\n"
                                                                  f"- If you manually delete case channels, then you will need to run ``{prefix}case cleanup`` to free them from the database; otherwise, they will count against your case limit.\n"
                                                                  f"- Case members can be easily muted/unmuted with ``{prefix}case mute`` or ``{prefix}case unmute``.")

        await response.send(embed=embed)

        await response.success(f"Successfully saved your **Court add-on!** Now, judges (people with the {', '.join([r.mention for r in judge_roles])} role(s)) will be "
                               f"able to run ``{prefix}case create`` to create a new case chat.", allowed_mentions=AllowedMentions(roles=False))
