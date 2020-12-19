from resources.structures.Bloxlink import Bloxlink # pylint: disable=import-error
from resources.exceptions import Message, Error, PermissionError, CancelledPrompt # pylint: disable=import-error
from resources.constants import LIMITS, ARROW, DEFAULTS, ORANGE_COLOR, OWNER, PROMPT # pylint: disable=import-error
from discord import Embed
from discord.errors import Forbidden
from time import time
from asyncio import TimeoutError
import datetime
import json


count_binds = Bloxlink.get_module("roblox", attrs=["count_binds"])
get_board, get_options = Bloxlink.get_module("trello", attrs=["get_board", "get_options"])
get_prefix = Bloxlink.get_module("utils", attrs=["get_prefix"])
cache_pop = Bloxlink.get_module("cache", attrs=["pop"])

INT_REACTIONS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]

@Bloxlink.command
class DataCommand(Bloxlink.Module):
    """backup or restore your stored Server Data"""

    async def _backup(self, guild, backup_name):
        guild_data = await self.r.table("guilds").get(str(guild.id)).run() or {}

        if guild_data:
            return {
                "data": guild_data,
                "timestamp": time(),
                "guildId": str(guild.id),
                "backupName": backup_name
            }

    async def _restore(self, guild, chosen_backup):
        chosen_backup["data"]["id"] = str(guild.id)

        await self.r.table("guilds").insert(chosen_backup["data"], conflict="replace").run()

        await cache_pop("trello_boards", guild.id)

    def _reaction_check(self, author):
        def wrapper(reaction, user):
            return str(reaction) in INT_REACTIONS and user == author

        return wrapper

    def __init__(self):
        self.permissions = Bloxlink.Permissions().build("BLOXLINK_MANAGER")
        self.category = "Premium"
        self.arguments = [
            {
                "prompt": "Would you like to **backup** your Server Data, or "
                          "**restore** your Data from a backup?",
                "name": "subcommand_choice",
                "type": "choice",
                "choices": ("backup", "restore")
            }
        ]

    async def __main__(self, CommandArgs):
        choice = CommandArgs.parsed_args["subcommand_choice"]

        if choice == "backup":
            await self.backup(CommandArgs)
        elif choice == "restore":
            await self.restore(CommandArgs)

    @Bloxlink.subcommand()
    async def backup(self, CommandArgs):
        """backup your Server Data"""

        author = CommandArgs.message.author
        guild = CommandArgs.message.guild
        response = CommandArgs.response

        author_id = str(author.id)

        user_data = await self.r.db("bloxlink").table("users").get(author_id).run() or {"id": author_id}
        user_backups = user_data.get("backups", [])

        if len(user_backups) >= LIMITS["BACKUPS"]:
            response.delete(await response.info("You've exceeded the amount of backups you're able to create! Your next "
                                "backup will replace your oldest backup."))
            user_backups.pop(0)

        parsed_args = await CommandArgs.prompt([
            {
                "prompt": "**Warning!** This will backup **all** of your Server Data, including "
                          "Linked Groups, Role Binds, prefixes, etc to restore to a different server.\n"
                          f"You are allowed to create **{LIMITS['BACKUPS']}** total backups for **all of your servers.**",
                "name": "_",
                "embed_title": "Warning!",
                "embed_color": ORANGE_COLOR,
                "footer": "Say anything to continue."
            },
            {
                "prompt": "What would you like to name this backup? You may use up to 30 characters.",
                "name": "backup_name",
                "max": 30
            }
        ])

        backup_name = parsed_args["backup_name"]

        new_backup = await self._backup(guild, backup_name)

        if new_backup:
            user_backups.append(new_backup)
        else:
            raise Message("There's nothing to save - your server has no saved data!", type="silly")

        user_data["backups"] = user_backups

        await self.r.db("bloxlink").table("users").insert(user_data, conflict="update").run()

        await response.success("Successfully saved your new backup!")

    @Bloxlink.subcommand()
    async def restore(self, CommandArgs):
        """restore your Server Data"""

        message = CommandArgs.message
        author = CommandArgs.message.author
        guild = CommandArgs.message.guild
        response = CommandArgs.response
        prefix = CommandArgs.prefix

        if author.id == OWNER:
            if message.attachments:
                attachment = message.attachments[0]

                if not attachment.height:
                    file_data = await attachment.read()
                    json_data = file_data.decode("utf8").replace("'", '"')
                    json_data = json.loads(json_data)
                    json_data["id"] = str(guild.id)

                    if json_data.get("roleBinds"):
                        role_map = {}

                        for bind_type, bind_data in json_data.get("roleBinds", {}).items():
                            if bind_type == "groups":
                                for group_id, group_data in bind_data.items():
                                    for rank, rank_data in group_data.get("binds", {}).items():
                                        for role_id in rank_data.get("roles", []):
                                            if not guild.get_role(int(role_id)):
                                                role_map_find = role_map.get(role_id)

                                                if not role_map_find:
                                                    role = await guild.create_role(name=rank*6)
                                                    role_map[role_id] = str(role.id)
                                                    role_map_find = str(role.id)

                                                json_data["roleBinds"]["groups"][group_id]["binds"][rank]["roles"].remove(role_id)
                                                json_data["roleBinds"]["groups"][group_id]["binds"][rank]["roles"].append(role_map_find)

                    await self.r.table("guilds").insert(json_data, conflict="replace").run()

                    return await response.success("Successfully **restored** this server's data.")
                else:
                    raise Error("You must supply a non-image file for data restore.")


        user_data = await self.r.db("bloxlink").table("users").get(str(author.id)).run() or {}
        user_backups = user_data.get("backups", [])

        if not user_backups:
            raise Message(f"You don't have any backups created! You may create them with ``{prefix}data backup``.", type="silly")

        embed = Embed(title="Bloxlink Data Restore", description="Please select the backup you could like to restore with the reactions.")

        for i, backup in enumerate(user_backups):
            guild_data = backup["data"]
            backup_name = backup["backupName"]
            timestamp = datetime.datetime.fromtimestamp(backup["timestamp"])

            trello_board = await get_board(guild_data=guild_data, guild=guild)
            prefix, _ = await get_prefix(guild=guild, trello_board=trello_board)

            backup["prefix"] = prefix
            backup["trello_board"] = trello_board,
            backup["timestamp"] = timestamp
            backup["nickname_template"] = guild_data.get("nicknameTemplate", DEFAULTS.get("nicknameTemplate"))

            if trello_board:
                trello_options, _ = await get_options(trello_board)
                guild_data.update(trello_options)

            len_role_binds = count_binds(guild_data)
            backup["len_role_binds"] = len_role_binds

            embed.add_field(name=f"{INT_REACTIONS[i]} {ARROW} {backup_name}", value="\n".join([
                f"**Role Binds** {ARROW} {len_role_binds}",
                f"**Prefix** {ARROW} {prefix}",
                f"**Nickname Template** {ARROW} {backup['nickname_template']}",
                f"**Created on ** {timestamp.strftime('%b. %d, %Y (%A)')}"
            ]))

        message = await response.send(embed=embed)

        if message:
            response.delete(message)

            for i, _ in enumerate(user_backups):
                emote_string = INT_REACTIONS[i]

                try:
                    await message.add_reaction(emote_string)
                except Forbidden:
                    raise PermissionError("I'm missing permission to add reactions to your message!")

            try:
                reaction, _ = await Bloxlink.wait_for("reaction_add", timeout=PROMPT["PROMPT_TIMEOUT"], check=self._reaction_check(author))
            except TimeoutError:
                raise CancelledPrompt(f"timeout ({PROMPT['PROMPT_TIMEOUT']}s)")
            else:
                chosen_backup = None
                str_reaction = str(reaction)

                for i, reaction_string in enumerate(INT_REACTIONS):
                    if str_reaction == reaction_string:
                        chosen_backup = user_backups[i]

                if chosen_backup:
                    parsed_args = await CommandArgs.prompt([
                        {
                            "prompt": "**Warning!** This will **__restore__ ALL OF YOUR SETTINGS** including:\n"
                                      f"**{chosen_backup['len_role_binds']}** Role Binds\n"
                                      f"**{chosen_backup['prefix']}** prefix\n"
                                      f"**{chosen_backup['nickname_template']}** Nickname Template\n"
                                      "Continue? ``Y/N``",
                            "name": "confirm",
                            "type": "choice",
                            "formatting": False,
                            "choices": ("yes", "no"),
                            "embed_title": "Warning!",
                            "embed_color": ORANGE_COLOR,
                            "footer": "Say **yes** to continue, or **no** to cancel."
                        }
                    ])

                    if parsed_args["confirm"] == "yes":
                        await self._restore(guild, chosen_backup)
                        await response.success("Successfully **restored** your backup!")
                    else:
                        raise CancelledPrompt("cancelled restore")
