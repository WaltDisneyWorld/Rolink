from resources.structures.Bloxlink import Bloxlink # pylint: disable=import-error
from resources.exceptions import Error, Message # pylint: disable=import-error
from resources.constants import ARROW # pylint: disable=import-error
from discord import PermissionOverwrite, Embed, AllowedMentions
from discord.utils import find
from discord.errors import Forbidden, NotFound


class CaseCommand(Bloxlink.Module):
    """manage your cases"""

    def __init__(self):
        self.permissions = Bloxlink.Permissions().build("BLOXLINK_MANAGER")
        self.category = "Court Addon"

    async def __main__(self, CommandArgs):
        subcommands = [getattr(self, x) for x in dir(self) if hasattr(getattr(self, x),"__issubcommand__")]
        subcommands_str = "\n".join(["**" + x.__func__.__name__ + "**" + f" {ARROW} " + x.__doc__ for x in subcommands])

        subcommand_name = (await CommandArgs.prompt([
            {
                "prompt": "Please choose a subcommand:\n\n"
                          f"{subcommands_str}",
                "name": "subcommand",
                "type": "choice",
                "choices": [x.__func__.__name__ for x in subcommands],
                "formatting": False
            }
        ]))["subcommand"]

        subcommand = getattr(self, subcommand_name)
        await subcommand(CommandArgs)


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

        if not (my_permissions.manage_channels and my_permissions.manage_roles):
            raise Error("I need both the ``Manage Channels`` and ``Manage Roles`` permissions.")

        if not court_data:
            raise Error(f"You must set-up this add-on before you can use it! Please use ``{prefix}courtsetup`` "
                        "to begin the set-up.")

        for judge_role_id in court_data.get("judgeRoles", []):
            if find(lambda r: r.id == int(judge_role_id), guild.roles):
                break
        else:
            raise Error("You must have a Judge role in order to create cases!")

        if len(court_data.get("cases", {})) >= 30:
            raise Error(f"You cannot have more than 30 active cases! Please complete the cases with ``{prefix}case end`` before creating more. "
                        f"If you have any lingering cases (cases manually deleted and not called with ``{prefix}case end``), then please run "
                        f"``{prefix}case cleanup`` to remove them from the database.")


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
            raise Error("I need both the ``Manage Channels`` and ``Manage Roles`` permissions.")
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

            embed = Embed(title="Additional Information", description= \
                                                                  f"- It's recommended to give your cases IDs! You'll be able to run ``{prefix}case lookup`` to find its information.\n"
                                                                  f"- You will need to add case members with ``{prefix}case add`` and assign them to a group. Remove them with ``{prefix}case remove``.\n"
                                                                  f"- Run ``{prefix}case end`` inside your case chat to archive the case.\n"
                                                                  f"- If you manually delete case channels, then you will need to run ``{prefix}case cleanup`` to free them from the database; otherwise, they will count against your case limit.\n"
                                                                  f"- Case members can be easily muted/unmuted with ``{prefix}case mute`` or ``{prefix}case unmute``.")

            log_channel_id = court_data.get("logChannel")

            if log_channel_id:
                log_channel = guild.get_channel(int(log_channel_id))

                if log_channel:
                    await response.send(f"Case **{case_name}** has been opened by {author.mention} and being served in {case_channel.mention}.", channel_override=log_channel, allowed_mentions=AllowedMentions(users=False))

            await response.send(embed=embed)


    @Bloxlink.subcommand()
    async def add(self, CommandArgs):
        """add members to court groups"""

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
        """remove members from court groups"""

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


    @Bloxlink.subcommand()
    async def end(self, CommandArgs):
        """end your trial"""

        response = CommandArgs.response
        prefix   = CommandArgs.prefix

        guild   = CommandArgs.message.guild
        channel = CommandArgs.message.channel
        author  = CommandArgs.message.author

        addon_data = await self.r.db("bloxlink").table("addonData").get(str(guild.id)).run() or {"id": str(guild.id)}
        court_data = addon_data.get("court") or {}
        cases = court_data.get("cases", {})

        archive_category = court_data.get("archiveCategory")

        current_case = cases.get(str(channel.id)) or {}
        case_name    = current_case.get("caseName")

        if not current_case:
            raise Error("You must run this command in a case channel!")

        elif int(current_case["presidingJudge"]) != author.id:
            raise Error("You must be the presiding judge in order to run this command!")

        if archive_category:
            category = find(lambda c: c.id == int(archive_category), guild.categories)

            if not category:
                raise Error(f"The archive category has been deleted! You must run ``{prefix}courtsetup`` to set another category.")

            overwrites = {
                guild.default_role: PermissionOverwrite(read_messages=False)
            }

            try:
                await channel.edit(category=category, overwrites=overwrites)
            except NotFound:
                raise Error(f"The archive category has been deleted! You must run ``{prefix}courtsetup`` to set another category.")
            except Forbidden:
                raise Error("I was unable to edit this case channel. Please make sure I have both the ``Manage Channels`` and "
                            "``Manage Roles`` permissions.")

            else:
                await response.success("Successfully **closed** this case channel.")
        else:
            try:
                await channel.delete()
            except Forbidden:
                raise Error("I was unable to delete this channel. Please make sure I have the ``Manage Channels`` permission.")

        cases.pop(str(channel.id), None)
        court_data["cases"] = cases
        addon_data["court"] = court_data

        await self.r.table("addonData").insert(addon_data, conflict="replace").run()

        log_channel_id = court_data.get("logChannel")

        if log_channel_id:
            log_channel = guild.get_channel(int(log_channel_id))

            if log_channel:
                await response.send(f"Case **{case_name}** has been closed by {author.mention}.", channel_override=log_channel, allowed_mentions=AllowedMentions(users=False))


    @Bloxlink.subcommand(arguments=[{
        "prompt": "Please provide a Case ID.",
        "name": "case_id"
    }])
    async def lookup(self, CommandArgs):
        """lookup a case by its ID"""

        case_id = CommandArgs.parsed_args["case_id"]

        response = CommandArgs.response
        prefix   = CommandArgs.prefix

        guild   = CommandArgs.message.guild

        addon_data = await self.r.db("bloxlink").table("addonData").get(str(guild.id)).run() or {"id": str(guild.id)}
        court_data = addon_data.get("court") or {}
        cases = court_data.get("cases", {})


        if not court_data:
            raise Error(f"You must set-up this add-on before you can use it! Please use ``{prefix}courtsetup`` "
                        "to begin the set-up.")
        elif not cases:
            raise Error(f"This server has no active cases! Cases may be created with ``{prefix}case create``.")


        for channel_id, case in cases.items():
            if case["caseID"] == case_id:
                break
        else:
            raise Error("I was unable to find the selected case! It may have already been closed.")

        group_members_ = case.get("groupMembers", {})
        group_members_str = "None"

        if group_members_:
            group_members_str = []

            for group, group_members in group_members_.items():
                group_members_str.append(f"**{group}** {ARROW} {', '.join([f'<@{m}>' for m in group_members])}")

            group_members_str = "\n".join(group_members_str)


        embed = Embed(title=f"Case {case['caseName']}")

        embed.add_field(name="Case ID", value=case_id)
        embed.add_field(name="Presiding Judge", value=f"<@{case['presidingJudge']}>")
        embed.add_field(name="Case Channel", value=f"<#{channel_id}>")
        embed.add_field(name="Group Members", value=group_members_str, inline=False)

        await response.send(embed=embed)


    @Bloxlink.subcommand()
    async def cleanup(self, CommandArgs):
        """free old cases from the database"""

        guild    = CommandArgs.message.guild
        prefix   = CommandArgs.prefix
        response = CommandArgs.response

        addon_data = await self.r.db("bloxlink").table("addonData").get(str(guild.id)).run() or {"id": str(guild.id)}
        court_data = addon_data.get("court")
        cases = court_data.get("cases", {})

        removed = 0

        my_permissions = guild.me.guild_permissions

        if not (my_permissions.manage_channels and my_permissions.manage_roles):
            raise Error("I need both the ``Manage Channels`` and ``Manage Roles`` permissions.")

        elif not court_data:
            raise Error(f"You must set-up this add-on before you can use it! Please use ``{prefix}courtsetup`` "
                        "to begin the set-up.")

        elif not cases:
            raise Message("Cannot clean cases: you have no cases saved to the database.", type="silly")


        for judge_role_id in court_data.get("judgeRoles", []):
            if find(lambda r: r.id == int(judge_role_id), guild.roles):
                break
        else:
            raise Error("You must have a Judge role in order to run this command!")

        for channel_id, case in dict(cases).items():
            case_channel = guild.get_channel(int(channel_id))

            if not case_channel or (case_channel and case_channel.category and case_channel.category.id != case["archiveCategory"]):
                cases.pop(channel_id)
                removed += 1


        court_data["cases"] = cases
        addon_data["court"] = court_data

        await self.r.table("addonData").insert(addon_data, conflict="replace").run()

        if removed:
            await response.success(f"Successfully removed **{removed}** old case(s) from the database.")
        else:
            await response.silly("No cases to clean: all case channels still exist in your server.")


    @Bloxlink.subcommand()
    async def mute(self, CommandArgs):
        """mute case members"""

        response = CommandArgs.response
        prefix   = CommandArgs.prefix

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
                "prompt": f"Which group should be muted? Available groups: ``{groups}``",
                "name": "group",
                "type": "choice",
                "choices": groups,
                "formatting": False
            }
        ])

        group = parsed_args["group"]
        group_members = current_case["groupMembers"].get(group) or []

        if not group_members:
            raise Error(f"This group has no members associated with it! Please add them with ``{prefix}case add``")

        if not guild.chunked:
            await guild.chunk()

        for member_id in group_members:
            member = guild.get_member(int(member_id))

            if member:
                await channel.set_permissions(member, send_messages=False)


        await response.success(f"Successfully **muted** the members from group ``{group}``!")


    @Bloxlink.subcommand()
    async def unmute(self, CommandArgs):
        """unmute case members"""

        response = CommandArgs.response
        prefix   = CommandArgs.prefix

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
                "prompt": f"Which group should be muted? Available groups: ``{groups}``",
                "name": "group",
                "type": "choice",
                "choices": groups,
                "formatting": False
            }
        ])

        group = parsed_args["group"]
        group_members = current_case["groupMembers"].get(group) or []

        if not group_members:
            raise Error(f"This group has no members associated with it! Please add them with ``{prefix}case add``")

        if not guild.chunked:
            await guild.chunk()

        for member_id in group_members:
            member = guild.get_member(int(member_id))

            if member:
                await channel.set_permissions(member, overwrite=None)


        await response.success(f"Successfully **unmuted** the members from group ``{group}``!")
