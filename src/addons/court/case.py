from resources.structures.Bloxlink import Bloxlink # pylint: disable=import-error
from resources.exceptions import Error, Message # pylint: disable=import-error
from discord import PermissionOverwrite
from discord.utils import find
from discord.errors import Forbidden


class CaseCommand(Bloxlink.Module):
    """manage your cases"""

    def __init__(self):
        self.developer = True
        self.permissions = Bloxlink.Permissions().build("BLOXLINK_MANAGER")
        self.category = "Court Addon"

    async def __main__(self, CommandArgs):
        prefix   = CommandArgs.prefix
        guild    = CommandArgs.message.guild
        response = CommandArgs.response


    @Bloxlink.subcommand()
    async def create(self, CommandArgs):
        """create a new court case"""

        guild    = CommandArgs.message.guild
        author   = CommandArgs.message.author
        prefix   = CommandArgs.prefix
        response = CommandArgs.response

        addon_data = await self.r.db("bloxlink").table("addonData").get(str(guild.id)).run() or {"id": str(guild.id)}
        court_data = addon_data.get("court")

        my_permissions = guild.me.guild_permissions

        if not my_permissions.manage_channels:
            raise Error("I need permission to create channels!")

        if not court_data:
            raise Error(f"You must set-up this add-on before you can use it! Please use ``{prefix}courtsetup`` "
                        "to begin the set-up.")

        for judge_role_id in court_data.get("judgeRoles", []):
            if find(lambda r: r.id == int(judge_role_id), guild.roles):
                break
        else:
            raise Error("You must have a Judge role in order to create cases!") # TODO: post role mentions with AllowedMentions set


        case_args = await CommandArgs.prompt([
            {
                "prompt": "Please give this case a title, e.g. _Bloxlink v. Roblox Corp._",
                "name": "case_title",
                "embed_title": "New Case"
            },
            {
                "prompt": "Does this case have an external **Case ID**? Case IDs are managed by you "
                          "to make organization easier.\n\n**This is optional.**",
                "name": "case_id",
                "footer": "Say **skip** to skip this step.",
                "embed_title": "New Case"
            }
        ])

        case_id   = case_args["case_id"] if case_args["case_id"].lower() != "skip" else None
        case_name = case_args["case_title"]
        judge_roles_ = [int(r) for r in court_data.get("judgeRoles")]
        judge_roles = []

        for judge_role_id in judge_roles_:
            judge_role = find(lambda r: r.id == judge_role_id, guild.roles)

            if judge_role:
                judge_roles.append(judge_role)

        category_id = int(court_data.get("category", 0))
        category = category_id and find(lambda c: c.id == category_id, guild.categories)

        overwrites = {
            guild.default_role: PermissionOverwrite(read_messages=False),
            guild.me: PermissionOverwrite(read_messages=True),
            author: PermissionOverwrite(read_messages=True, mention_everyone=True, manage_messages=True)
        }

        try:
            case_channel = await guild.create_text_channel(case_name.replace("_", "").replace(" ", "-"), overwrites=overwrites, category=category)
        except Forbidden:
            pass
        else:
            court_data["cases"] = court_data.get("cases", {})
            court_data["cases"][str(case_channel.id)] = court_data["cases"].get(str(case_channel.id)) or {}
            court_data["cases"][str(case_channel.id)] = {
                "presidingJudge": str(author.id),
                "caseName": case_name,
                "caseID": case_id,
                "groupMembers": {},
            }

            addon_data["court"] = court_data

            await self.r.table("addonData").insert(addon_data, conflict="update").run()

            await response.send(f"Welcome to the case of **{case_name}** which is being presided over by {author.mention}.", channel_override=case_channel)

            await response.success(f"Your case chat was successfully created! You'll find it in {case_channel.mention}. If your DMs are enabled, then I'll send you "
                                    "additional instructions over DMs; otherwise, I'll post it in this channel.")

            await response.send(f"Judge: run ``{prefix}case end`` to end this case and export the chat logs. Run ``{prefix}case add @person1 @person2`` "
                                f"to add additional people to the case. Run ``{prefix}jurors <integer>`` to randomly pick <int> jurors. Finally, run "
                                f"``{prefix}case mute <plaintiff|defense>`` to mute those people, and ``{prefix}case unmute <plaintiff|defense>`` to unmute them.", dm=True) # TODO: make sure this is up-to-date

    @Bloxlink.subcommand()
    async def add(self, CommandArgs):
        response = CommandArgs.response

        guild   = CommandArgs.message.guild
        channel = CommandArgs.message.channel
        author  = CommandArgs.message.author

        addon_data = await self.r.db("bloxlink").table("addonData").get(str(guild.id)).run() or {"id": str(guild.id)}
        court_data = addon_data.get("court") or {}
        groups     = court_data.get("groups", [])

        current_case = court_data.get("cases", {}).get(str(channel.id))

        if not current_case:
            raise Error("You must run this command in a case channel!")

        elif int(current_case["presidingJudge"]) != author.id:
            raise Error("You must be the presiding judge in order to run this command!")

        elif not groups:
            raise Error("You need at least one group in order to run this command!") # TODO: add instructions on creating groups

        parsed_args = await CommandArgs.prompt([
            {
                "prompt": "Please mention all of the users who should be added to this trial. These members should all belong to the "
                          "same group.",
                "name": "users",
                "type": "user",
                "multiple": True
            },
            {
                "prompt": f"Which group should these members be added to? Available groups: ``{groups}``",
                "name": "group",
                "type": "choice",
                "choices": groups,
                "formatting": False
            }
        ])

        group_members     = parsed_args["users"]
        group_members_ids = [str(m.id) for m in parsed_args["users"]]
        group             = parsed_args["group"]

        current_case["groupMembers"][group] = current_case["groupMembers"].get(group) or []
        current_case["groupMembers"][group] = list(set(current_case["groupMembers"][group] + group_members_ids))

        court_data["cases"][str(channel.id)] = current_case
        addon_data["court"] = court_data

        await self.r.table("addonData").insert(addon_data, conflict="replace").run()

        try:
            for group_member in group_members:
                await channel.set_permissions(group_member, read_messages=True)
        except Forbidden:
            raise Error("I've saved your group members, but I was unable to set their permissions for this "
                        "channel. Please add the group members to this channel, or give me the ``Manage Channel`` "
                        "and ``Manage Roles`` permissions, then re-run this command.")

        await response.success(f"Successfully **added** these members to the group ``{group}``!")

    @Bloxlink.subcommand()
    async def remove(self, CommandArgs):
        response = CommandArgs.response
        prefix   = CommandArgs.prefix

        guild   = CommandArgs.message.guild
        channel = CommandArgs.message.channel
        author  = CommandArgs.message.author

        addon_data = await self.r.db("bloxlink").table("addonData").get(str(guild.id)).run() or {"id": str(guild.id)}
        court_data = addon_data.get("court") or {}
        groups     = court_data.get("groups", [])

        current_case = court_data.get("cases", {}).get(str(channel.id)) or {}
        group_members = current_case.get("groupMembers")

        if not current_case:
            raise Error("You must run this command in a case channel!")

        elif int(current_case["presidingJudge"]) != author.id:
            raise Error("You must be the presiding judge in order to run this command!")

        elif not group_members:
            raise Message(f"Your case has no group members! You may add them with ``{prefix}case add``", type="silly")

        parsed_args = await CommandArgs.prompt([
            {
                "prompt": "Please mention the people who should be removed from the group.",
                "name": "users",
                "type": "user",
                "multiple": True
            },
            {
                "prompt": f"Which group should these members be removed from? Available groups: ``{groups}``",
                "name": "group",
                "type": "choice",
                "choices": groups,
                "formatting": False
            }
        ])

        group_members     = parsed_args["users"]
        group_members_ids = [str(m.id) for m in parsed_args["users"]]
        group             = parsed_args["group"]

        current_case["groupMembers"][group] = current_case["groupMembers"].get(group) or []
        current_case["groupMembers"][group] = list(set(current_case["groupMembers"][group]).difference(group_members_ids))

        court_data["cases"][str(channel.id)] = current_case
        addon_data["court"] = court_data

        await self.r.table("addonData").insert(addon_data, conflict="replace").run()

        try:
            for group_member in group_members:
                await channel.set_permissions(group_member, overwrite=None)
        except Forbidden:
            raise Error("I've saved your group members, but I was unable to set their permissions for this "
                        "channel. Please add the group members to this channel, or give me the ``Manage Channel`` "
                        "and ``Manage Roles`` permissions, then re-run this command.")

        await response.success(f"Successfully **removed** these members from the group ``{group}``!")
