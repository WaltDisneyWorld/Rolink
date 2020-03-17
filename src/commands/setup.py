from resources.structures.Bloxlink import Bloxlink
from resources.constants import ARROW, ORANGE_COLOR, NICKNAME_TEMPLATES
from resources.exceptions import Error, RobloxNotFound
from config import TRELLO # pylint: disable=no-name-in-module
from aiotrello.exceptions import TrelloNotFound, TrelloUnauthorized, TrelloBadRequest
from discord.errors import Forbidden, HTTPException
from discord import Embed
from discord.utils import find
import asyncio
import re

NICKNAME_DEFAULT = "{roblox-name}"
VERIFIED_DEFAULT = "Verified"

get_group, generate_code = Bloxlink.get_module("roblox", attrs=["get_group", "generate_code"])
trello = Bloxlink.get_module("trello", attrs=["trello"])

roblox_group_regex = re.compile("roblox.com/groups/(\d+)/")



@Bloxlink.command
class SetupCommand(Bloxlink.Module):
    """set-up your server with Bloxlink"""

    def __init__(self):
        self.permissions = Bloxlink.Permissions().build("BLOXLINK_MANAGER")

    @staticmethod
    async def validate_group(message, content):
        if content.lower() in ("skip", "next"):
            return "skip"

        regex_search = roblox_group_regex.search(content)

        if regex_search:
            group_id = regex_search.group(0)
        else:
            group_id = content

        try:
            group = await get_group(group_id)
        except RobloxNotFound:
            return None, "No group was found with this ID. Please try again."

        return group

    @staticmethod
    async def validate_trello_board(message, content):
        content_lower = content.lower()

        if content_lower in ("skip", "next"):
            return "skip"
        elif content_lower == "disable":
            return "disable"

        try:
            board = await trello.get_board(content, card_limit=TRELLO["GLOBAL_CARD_LIMIT"])
        except (TrelloNotFound, TrelloBadRequest) as e:
            return None, "No Trello board was found with this ID. Please try again."
        except TrelloUnauthorized:
            return None, "I don't have permission to view this Trello board; please make sure " \
                         "this Trello board is set to **PUBLIC**, or add ``@bloxlink`` to your Trello board."

        return board

    async def __main__(self, CommandArgs):
        guild = CommandArgs.message.guild
        response = CommandArgs.response

        guild_data = CommandArgs.guild_data
        group_ids = guild_data.get("groupIDs", {})

        settings_buffer = []

        parsed_args_1 = {}
        parsed_args_2 = {}
        parsed_args_3 = {}
        parsed_args_4 = {}

        nickname = None


        parsed_args_1 = await CommandArgs.prompt([
            {
                "prompt": "**Thank you for choosing Bloxlink!** In a few simple prompts, **we'll configure Bloxlink for your server.**\n\n"
                          "**Pre-configuration:**\nBefore continuing, please ensure that Bloxlink has all the proper permissions, "
                          "such as the ability to ``manage roles, nicknames, channels``, etc. If you do not set these "
                          "permissions, you may encounter issues with using certain commands.",
                "name": "_",
                "footer": "Say **next** to continue.",
                "type": "choice",
                "choices": ["next"],
                "embed_title": "Setup Prompt"
            },
            {
                "prompt": "Would you like to link a **Roblox group** to this Discord server? Please provide the **Group URL, or Group ID**.",
                "name": "group",
                "footer": "Say **skip** to leave as-is.",
                "embed_title": "Setup Prompt",
                "validation": self.validate_group
            },
            {
                "prompt": "Would you like to change the **Verified role** (the role people are given if they're linked to Bloxlink) name to something else?\n"
                          "Default: ``Verified``",
                "name": "verified_role",
                "footer": "Say **disable** to disable the Verified role.\nSay **skip** to leave as-is.",
                "embed_title": "Setup Prompt",
                "max": 50
            },
            {
                "prompt": "Would you like to link a **Trello.com board** to this server? You'll be able to change Bloxlink settings and binds from "
                          "the board. Please either provide the **Trello board ID, or the board URL.**",
                "name": "trello_board",
                "footer": "Say **disable** to disable/clear a saved board.\nSay **skip** to leave as-is.",
                "embed_title": "Setup Prompt",
                "validation": self.validate_trello_board
            }
        ], dm=True)

        for k, v in parsed_args_1.items():
            if k != "_":
                settings_buffer.append(f"**{k}** {ARROW} {v}")

        group = parsed_args_1["group"]
        verified = parsed_args_1["verified_role"]

        trello_board = parsed_args_1["trello_board"]

        if group not in ("next", "skip"):
            group_ids[group.group_id] = {"nickname": nickname, "groupName": group.name}

            parsed_args_2 = await CommandArgs.prompt([
                {
                    "prompt": "Should these members be given a nickname? Please create a nickname using these templates. You may "
                              f"combine templates. The templates MUST match exactly.\n\n**Templates:** ```{NICKNAME_TEMPLATES}```",
                    "name": "nickname",
                    "embed_title": "Setup Prompt",
                    "footer": "Say **disable** to not have a nickname.\nSay **skip** to leave this as the default.",
                    "formatting": False
                },
                {
                    "prompt": "Would you like to automatically transfer your Roblox group ranks to Discord roles?\nValid choices:\n"
                              "``merge`` — This will **NOT** remove any roles. Your group Rolesets will be **merged** with your current roles.\n"
                              "``replace`` — **This will REMOVE and REPLACE your CURRENT ROLES** with your Roblox group Rolesets. You'll "
                              "need to configure permissions and colors yourself.\n"
                              "``skip`` — nothing will be changed.\n\nValid choices: (merge/replace/skip)",
                    "name": "merge_replace",
                    "type": "choice",
                    "choices": ["merge", "replace", "skip", "next"],
                    "embed_title": "Setup Prompt"

                }
            ], dm=True)

            if parsed_args_2["merge_replace"]  == "next":
                parsed_args_2["merge_replace"] = "skip"

            nickname = parsed_args_2["nickname"]

            if nickname == "skip":
                if group.group_id in group_ids:
                    nickname = group_ids[group.group_id]["nickname"]
                else:
                    nickname = NICKNAME_DEFAULT

            elif nickname == "disable":
                nickname = None

            group_ids[group.group_id] = {"nickname": nickname, "groupName": group.name}

        for k, v in parsed_args_2.items():
            if k != "_":
                settings_buffer.append(f"**{k}** {ARROW} {v}")


        if trello_board not in ("skip", "disable"):
            trello_code = generate_code()

            parsed_args_3 = await CommandArgs.prompt([
                {
                    "prompt": "We'll now attempt to verify that you own this Trello board. To begin, please add ``trello@blox.link`` (@bloxlink) "
                              "to your Trello board. Then, say ``next`` to continue.",
                    "name": "trello_continue",
                    "type": "choice",
                    "choices": ["next"],
                    "embed_title": "Trello Verification"

                },
                {
                    "prompt": f"Now, please make a card _anywhere_ on your Trello board with this code as the card name:```{trello_code}```"
                               "Then, say ``next`` after the code is on your Trello board.",
                    "name": "trello_continue",
                    "type": "choice",
                    "choices": ["next"],
                    "embed_title": "Trello Verification"

                }
            ], dm=True)

            if True: # TODO: trello verification
                pass


        parsed_args_4 = await CommandArgs.prompt([
            {
                "prompt": "You have reached the end of the setup. Here are your current settings:\n"
                           + "\n".join(settings_buffer),
                "name": "setup_complete",
                "type": "choice",
                "footer": "Please say **done** to complete the setup.",
                "choices": ["done"],
                "embed_title": "Setup Prompt Confirmation",
                "embed_color": ORANGE_COLOR,
                "formatting": False
            }
        ], dm=True)

        if group and group != "skip":
            merge_replace = parsed_args_2.get("merge_replace")

            if merge_replace not in ("skip", "next"):
                if merge_replace == "replace":
                    for role in list(guild.roles):
                        if not (role in guild.me.roles or role.is_default()):
                            try:
                                await role.delete()
                            except Forbidden:
                                pass
                            except HTTPException:
                                pass

                sorted_rolesets = sorted(group.rolesets, key=lambda r: r["Rank"], reverse=True)

                for roleset in sorted_rolesets:
                    roleset_name = roleset["Name"]

                    if not find(lambda r: r.name == roleset_name, guild.roles):
                        try:
                            await guild.create_role(name=roleset_name)
                        except Forbidden:
                            raise Error("Please ensure I have the ``Manage Roles`` permission; setup aborted.")

        if verified:
            if verified == "disable":
                guild_data["verifiedRoleEnabled"] = False
            elif verified not in ("next", "skip"):
                guild_data["verifiedRoleName"] = verified
                guild_data["verifiedRoleEnabled"] = True

        if trello_board:
            update_trello = False

            if trello_board == "disable":
                trello_board = None
                update_trello = True
            elif trello_board in ("skip", "next"):
                trello_board = guild_data.get("trelloID")
            else:
                trello_board = trello_board.id
                update_trello = True

            if update_trello:
                guild_data["trelloID"] = trello_board

        if group_ids:
            guild_data["groupIDs"] = group_ids


        await self.r.table("guilds").insert(guild_data, conflict="replace").run()

        await response.success("Your server is now **configured** with Bloxlink!", dm=True, no_dm_post=True)
