from ..structures.Bloxlink import Bloxlink
from ..exceptions import (BadUsage, RobloxAPIError, CancelledPrompt, Message, Error,
                          CancelCommand, UserNotVerified, RobloxNotFound, PermissionError, BloxlinkBypass)
from typing import Tuple
from discord.errors import Forbidden, NotFound
from discord.utils import find
from discord import Embed, Member
from datetime import datetime
from config import WORDS # pylint: disable=no-name-in-module
from os import environ as env
from ..constants import RELEASE, DEFAULTS, STAFF_COLOR, DEV_COLOR, COMMUNITY_MANAGER_COLOR, VIP_MEMBER_COLOR
import json
import random
import re
import asyncio
import dateutil.parser as parser
import math

try:
    from config import TRELLO
except ImportError:
    TRELLO = {
        "KEY": env.get("TRELLO_KEY"),
        "TOKEN": env.get("TRELLO_TOKEN"),
	    "TRELLO_BOARD_CACHE_EXPIRATION": 5 * 60,
	    "GLOBAL_CARD_LIMIT": 500
    }


nickname_template_regex = re.compile("\{(.*?)\}")
trello_card_bind_regex = re.compile("(.*?): ?(.*)")
any_group_nickname = re.compile(r"\{group-rank-(.*?)\}")


loop = asyncio.get_event_loop()

fetch = Bloxlink.get_module("utils", attrs="fetch")
get_options = Bloxlink.get_module("trello", attrs="get_options")

API_URL = "https://api.roblox.com"
BASE_URL = "https://www.roblox.com"
GROUP_API = "https://groups.roblox.com"



@Bloxlink.module
class Roblox(Bloxlink.Module):
    cache = {"usernames_to_ids": {}, "roblox_users": {}, "discord_profiles": {}, "groups": {}}

    def __init__(self):
        pass

    @staticmethod
    async def get_roblox_id(username) -> Tuple[str, str]:
        username_lower = username.lower()
        roblox_cached_data = Roblox.cache["usernames_to_ids"].get(username_lower)

        if roblox_cached_data:
            return roblox_cached_data

        _, response = await fetch(f"{API_URL}/users/get-by-username/?username={username}", raise_on_failure=True)

        json_data = await response.json()

        if json_data.get("success") is False:
            raise RobloxNotFound

        correct_username, roblox_id = json_data.get("Username"), str(json_data.get("Id"))

        data = (roblox_id, correct_username)

        if correct_username:
            Roblox.cache["usernames_to_ids"][username_lower] = data

        return data

    @staticmethod
    async def get_roblox_username(roblox_id) -> Tuple[str, str]:
        roblox_user = Roblox.cache["roblox_users"].get(roblox_id)

        if roblox_user and roblox_user.verified:
            return roblox_user.id, roblox_user.username

        _, response = await fetch(f"{API_URL}/users/{roblox_id}", raise_on_failure=True)

        json_data = await response.json()

        if json_data.get("success") is False:
            raise RobloxNotFound

        correct_username, roblox_id = json_data.get("Username"), str(json_data.get("Id"))

        data = (roblox_id, correct_username)

        return data

    @staticmethod
    def generate_code():
        words = []

        for _ in range(4):
            x = random.randint(1, 2)

            words.append(f"{random.choice(WORDS)} {x == 1 and 'and' or 'or'}")

        words.append(random.choice(WORDS))

        return " ".join(words)


    @staticmethod
    async def validate_code(roblox_id, code):
        if RELEASE == "LOCAL":
            return True

        html_text, _ = await fetch(f"https://www.roblox.com/users/{roblox_id}/profile", raise_on_failure=True)

        return code in html_text

    @staticmethod
    async def parse_accounts(accounts):
        parsed_accounts = {}

        for account in accounts:
            roblox_user = RobloxUser(roblox_id=account)
            await roblox_user.sync()

            parsed_accounts[roblox_user.username] = roblox_user

        return parsed_accounts

    async def verify_member(self, author, roblox, guild=None, author_data=None, primary_account=False, allow_reverify=True):
        # TODO: make this insert a new DiscordProfile or append the account to it
        author_id = str(author.id)
        guild = guild or getattr(author, "guild", None)
        guild_id = guild and str(guild.id)

        if isinstance(roblox, RobloxUser):
            roblox_id = str(roblox.id)
        else:
            roblox_id = str(roblox)

        author_data = author_data or await self.r.table("users").get(author_id).run() or {}
        roblox_accounts = author_data.get("robloxAccounts", {})
        roblox_list = roblox_accounts.get("accounts", [])

        if guild:
            guild_list = roblox_accounts.get("guilds", {})
            guild_find = guild_list.get(guild_id)

            if guild_find and not allow_reverify and guild_find != roblox:
                raise Error("You already selected your account for this server! ``allowReVerify`` must be enabled for you to change your account.")

            guild_list[guild_id] = roblox_id
            roblox_accounts["guilds"] = guild_list


        if not roblox_id in roblox_list:
            roblox_list.append(roblox_id)
            roblox_accounts["accounts"] = roblox_list

        await self.r.table("users").insert(
            {
                "id": author_id,
                "robloxID": primary_account and roblox_id or author_data.get("robloxID"),
                "robloxAccounts": roblox_accounts
            },
            conflict="update"
        ).run()

        if author_id in Roblox.cache["discord_profiles"]:
            del Roblox.cache["discord_profiles"][author_id]


    async def unverify_member(self, author, roblox):
        author_id = str(author.id)
        success = False

        if isinstance(roblox, RobloxUser):
            roblox_id = str(roblox.id)
        else:
            roblox_id = str(roblox)

        user_data = await self.r.table("users").get(author_id).run()
        roblox_accounts = user_data.get("robloxAccounts", {})
        roblox_list = roblox_accounts.get("accounts", [])
        guilds = roblox_accounts.get("guilds", {})

        if roblox_id in roblox_list:
            roblox_list.remove(roblox_id)
            roblox_accounts["accounts"] = roblox_list
            success = True

        for i,v in guilds.items():
            if v == roblox_id:
                guilds[i] = None
                roblox_accounts["guilds"] = guilds
                success = True

        await self.r.table("users").insert(
            {
                "id": author_id,
                "robloxAccounts": roblox_accounts
            },
            conflict="update"
        ).run()

        return success


    async def get_nickname(self, author, template=None, group=None, *, guild=None, skip_roblox_check=False, is_nickname=True, guild_data=None, roblox_user=None):
        template = template or ""

        if template == "{disable-nicknaming}":
            return

        guild = guild or author.guild
        roblox_user = roblox_user or (not skip_roblox_check and await self.get_user(author=author, everything=True))

        if isinstance(roblox_user, tuple):
            roblox_user = roblox_user[0]

        guild_data = guild_data or await self.r.db("canary").table("guilds").get(str(guild.id)).run() or {}

        if roblox_user:
            if not roblox_user.complete:
                await roblox_user.sync(everything=True)

            if not group and guild_data:
                groups = list(guild_data.get("groupIDs", {}).keys())
                group_id = groups and groups[0]

                if group_id:
                    group = roblox_user.groups.get(group_id)


            group_role = group and group.user_rank_name or "Guest"

            template = template or DEFAULTS.get("nicknameTemplate") or ""

            if template == "{disable-nicknaming}":
                return

            for group_id in any_group_nickname.findall(template):
                group = roblox_user.groups.get(group_id)
                group_role = group and group.user_rank_name or "Guest"
                template = template.replace("{group-rank-"+group_id+"}", group_role)

            template = template.replace(
                "roblox-name", roblox_user.username
            ).replace(
                "roblox-id", str(roblox_user.id)
            ).replace(
                "roblox-age", str(roblox_user.age)
            ).replace(
                "roblox-join-date", roblox_user.join_date
            ).replace(
                "group-rank", group_role
            ).replace(
                "clan-tag", "" # TODO
            )

        else:
            if not template:
                template = guild_data.get("unverifiedNickname") or DEFAULTS.get("unverifiedNickname") or ""

                if template == "{disable-nicknaming}":
                    return

        template = template.replace(
            "discord-name", author.name
        ).replace(
            "discord-nick", author.display_name
        ).replace(
            "server-name", guild.name
        )

        for outer_nick in nickname_template_regex.findall(template):
            nick_data = outer_nick.split(":")
            nick_fn = None
            nick_value = None

            if len(nick_data) > 1:
                nick_fn = nick_data[0]
                nick_value = nick_data[1]
            else:
                nick_value = nick_data[0]

            # nick_fn = capA
            # nick_value = roblox-name

            if nick_fn == "allC":
                nick_value = nick_value.upper()
            elif nick_fn == "allL":
                nick_value = nick_value.lower()

            # TODO: add more nickname functions

            template = template.replace("{{{0}}}".format(outer_nick), nick_value)

        if is_nickname:
            return template[0:31]
        else:
            return template


    async def parse_trello_binds(self, trello_board=None, trello_binds_list=None):
        card_binds = {
            "binds": {},
            "entire group": {}
        }

        if trello_board or trello_binds_list:
            trello_binds_list = trello_binds_list or await trello_board.get_list(lambda l: l.name.lower() == "bloxlink binds")

            if trello_binds_list:
                if hasattr(trello_binds_list, "parsed_bind_data") and trello_binds_list.parsed_bind_data:
                    card_binds = trello_binds_list.parsed_bind_data
                else:
                    await trello_binds_list.sync(card_limit=TRELLO["GLOBAL_CARD_LIMIT"])

                    for card in await trello_binds_list.get_cards():
                        is_bind = False
                        is_main_group = False
                        treat_as_bind = False
                        new_bind = {"trello_str": {}, "nickname": None}

                        for card_bind_data in card.description.split("\n"):
                            card_bind_data_search = trello_card_bind_regex.search(card_bind_data)

                            if card_bind_data_search:
                                card_attr, card_value = card_bind_data_search.groups()

                                if card_attr and card_value:
                                    card_attr = card_attr.lower()

                                    if card_attr in ("group", "groupid", "group id"):
                                        new_bind["group"] = card_value
                                        new_bind["trello_str"]["group"] = card_value

                                    elif card_attr == "nickname":
                                        if card_value.lower() not in ("none", "false", "n/a"):
                                            new_bind["nickname"] = card_value
                                        else:
                                            new_bind["nickname"] = None

                                        new_bind["trello_str"]["nickname"] = card_value

                                    elif card_attr == "ranks":
                                        is_bind = True
                                        new_bind["ranks"] = [x.replace(" ", "") for x in card_value.split(",")]

                                        new_bind["trello_str"]["ranks"] = card_value

                                    elif card_attr == "roles":
                                        roles = set()

                                        for role in card_value.split(","):
                                            role = role.strip()
                                            roles.add(role)

                                        new_bind["roles"] = roles
                                        new_bind["trello_str"]["roles"] = card_value

                        bind_nickname = new_bind.get("nickname")
                        bound_roles = new_bind.get("roles", set())

                        if new_bind.get("group"):
                            if not (new_bind.get("roles") or is_bind):
                                is_main_group = True

                            else:
                                treat_as_bind = True
                        else:
                            continue

                        if treat_as_bind:
                            if new_bind.get("ranks"):
                                ranges = []

                                for rank in new_bind["ranks"]:
                                    is_range = False
                                    new_range = None

                                    if rank == "everyone":
                                        rank = "all"
                                    elif "-" in rank and not rank.lstrip("-").isdigit():
                                        range_data = rank.split("-")

                                        if len(range_data) == 2:
                                            if not range_data[0].isdigit() and range_data[0] != "0":
                                                raise Error(f"Mess up on Trello configuration for range: ``{range_data[0]}`` is not an integer.")
                                            elif not range_data[1].isdigit() and range_data[1] != "0":
                                                raise Error(f"Mess up on Trello configuration for range: ``{range_data[1]}`` is not an integer.")

                                            is_range = True
                                            new_range = {
                                                "low": int(range_data[0].strip()),
                                                "high": int(range_data[1].strip()),
                                                "nickname": bind_nickname,
                                                "roles": bound_roles,
                                                "trello": {
                                                    "cards": [{
                                                        "card": card,
                                                        "trello_str": new_bind["trello_str"],
                                                        "ranks": new_bind.get("ranks"),
                                                        "roles": bound_roles
                                                    }]
                                                }
                                            }
                                            #ranges.append(new_range)

                                    card_binds["binds"][new_bind["group"]] = card_binds["binds"].get(new_bind["group"]) or {}
                                    card_binds["binds"][new_bind["group"]]["binds"] = card_binds["binds"][new_bind["group"]].get("binds") or {}
                                    card_binds["binds"][new_bind["group"]]["ranges"] = card_binds["binds"][new_bind["group"]].get("ranges") or []
                                    card_binds["binds"][new_bind["group"]]["ranges"] += ranges

                                    new_rank = {"nickname": bind_nickname, "roles": bound_roles, "trello": {"cards": [{"roles": set(bound_roles), "card": card, "trello_str": new_bind["trello_str"], "ranks": new_bind.get("ranks") }]}}

                                    if not is_range:
                                        old_rank = card_binds["binds"][new_bind["group"]]["binds"].get(rank)

                                        if old_rank:
                                            new_rank["roles"].update(old_rank["roles"])
                                            new_rank["trello"]["cards"] += old_rank["trello"]["cards"]

                                        card_binds["binds"][new_bind["group"]]["binds"][rank] = new_rank
                                    else:
                                        new_range.update({
                                            "high": new_range["high"],
                                            "low": new_range["low"]
                                        })

                                        for range_ in card_binds["binds"][new_bind["group"]]["ranges"]:
                                            if range_["high"] == new_range["high"] and range_["low"] == new_range["low"]:
                                                old_range = range_

                                                new_range["roles"].update(old_range["roles"])
                                                new_range["trello"]["cards"] += old_range["trello"]["cards"]

                                                break

                                        card_binds["binds"][new_bind["group"]]["ranges"].append(new_range)

                            else:
                                new_rank = {
                                    "nickname": bind_nickname,
                                    "roles": bound_roles,
                                    "trello": {
                                        "cards": [{
                                            "card": card,
                                            "trello_str": new_bind["trello_str"],
                                            "ranks": new_bind.get("ranks"),
                                            "roles": bound_roles
                                        }]
                                    }
                                }

                                card_binds["binds"][new_bind["group"]] = card_binds["binds"].get(new_bind["group"]) or {}
                                card_binds["binds"][new_bind["group"]]["binds"] = card_binds["binds"][new_bind["group"]].get("binds") or {}

                                old_rank = card_binds["binds"][new_bind["group"]]["binds"].get("all")

                                if old_rank:
                                    new_rank["roles"].union(old_rank["roles"])
                                    new_rank["trello"]["cards"] += old_rank["trello"]["cards"]

                                card_binds["binds"][new_bind["group"]]["binds"]["all"] = new_rank

                        elif is_main_group:
                            try:
                                group = await self.get_group(new_bind["group"])
                            except RobloxNotFound:
                                group_name = f"Invalid Group: {new_bind['group']}"
                            else:
                                group_name = group.name

                            new_rank = {
                                "nickname": bind_nickname,
                                "groupName": group_name,
                                "roles": set(),
                                "trello": {
                                    "cards": [{
                                        "card": card,
                                        "trello_str": new_bind["trello_str"],
                                        "ranks": new_bind.get("ranks")
                                    }]
                                }
                            }

                            old_rank = card_binds["entire group"].get(new_bind["group"])

                            if old_rank:
                                new_rank["roles"].union(old_rank["roles"])
                                new_rank["trello"]["cards"] += old_rank["trello"]["cards"]

                            card_binds["entire group"][new_bind["group"]] = new_rank

                    trello_binds_list.parsed_bind_data = card_binds

        return card_binds, trello_binds_list


    async def get_binds(self, guild=None, guild_data=None, trello_board=None, trello_binds_list=None):
        card_binds, trello_binds_list = await self.parse_trello_binds(trello_board=trello_board, trello_binds_list=trello_binds_list)
        guild_data = guild_data or await self.r.db("canary").table("guilds").get(str(guild.id)).run() or {}

        role_binds = dict(guild_data.get("roleBinds") or {})
        group_ids = dict(guild_data.get("groupIDs") or {})

        role_binds["groups"] = dict(role_binds.get("groups", {}))

        if card_binds:
            role_binds["groups"].update(card_binds["binds"])
            group_ids.update(card_binds["entire group"])


        return role_binds, group_ids, trello_binds_list


    async def update_member(self, author, guild, *, nickname=True, roles=True, group_roles=True, roblox_user=None, author_data=None, guild_data=None, trello_board=None, trello_binds_list=None, given_trello_options=False):
        me = getattr(guild, "me", None)
        my_permissions = me and me.guild_permissions

        if my_permissions:
            if roles and not my_permissions.manage_roles:
                raise PermissionError("Sorry, I do not have the proper permissions."
                                      "Please ensure I have the ``Manage Roles`` permission.")

            if nickname and not my_permissions.manage_nicknames:
                raise PermissionError("Sorry, I do not have the proper permissions."
                                      "Please ensure I have the ``Manage Nicknames`` permission.")

        add_roles, remove_roles = set(), set()
        possible_nicknames = []
        errors = []
        unverified = False
        top_role_nickname = None
        trello_options = {}

        if not isinstance(author, Member):
            author = await guild.fetch_member(author.id)

            if not author:
                raise CancelCommand

        if not guild:
            guild = guild or getattr(author, "guild", None)

            if not guild:
                raise Error("Unable to resolve a guild from author.")

        if find(lambda r: r.name == "Bloxlink Bypass", author.roles):
            raise BloxlinkBypass


        if trello_board and not given_trello_options:
            trello_options, _ = await get_options(trello_board)


        guild_data = guild_data or await self.r.db("canary").table("guilds").get(str(guild.id)).run() or {}

        if trello_options:
            guild_data.update(trello_options)

        verify_role = guild_data.get("verifiedRoleEnabled", DEFAULTS.get("verifiedRoleEnabled"))
        unverify_role = guild_data.get("unverifiedRoleEnabled", DEFAULTS.get("unverifiedRoleEnabled"))

        unverified_role_name = guild_data.get("unverifiedRoleName", DEFAULTS.get("unverifiedRoleName"))
        verified_role_name = guild_data.get("verifiedRoleName", DEFAULTS.get("verifiedRoleName"))

        if unverify_role:
            unverified_role = find(lambda r: r.name == unverified_role_name, guild.roles)

        if verify_role:
            verified_role = find(lambda r: r.name == verified_role_name, guild.roles)

        try:
            if not roblox_user:
                roblox_user, _ = await self.get_user(author=author, guild=guild, author_data=author_data, everything=True)

                if not roblox_user:
                    raise UserNotVerified

        except UserNotVerified:
            if roles and unverify_role:
                if not unverified_role:
                    try:
                        unverified_role = await guild.create_role(name=unverified_role_name)
                    except Forbidden:
                        raise PermissionError("I was unable to create the Unverified Role. Please "
                                              "ensure I have the ``Manage Roles`` permission.")

                add_roles.add(unverified_role)

            if nickname:
                nickname = await self.get_nickname(author=author, skip_roblox_check=True, guild=guild, guild_data=guild_data)

            unverified = True

        else:
            if roles:
                if unverify_role:
                    if unverified_role and unverified_role in author.roles:
                        remove_roles.add(unverified_role)

                if verify_role:
                    verified_role = find(lambda r: r.name == verified_role_name, guild.roles)

                    if not verified_role:
                        try:
                            verified_role = await guild.create_role(
                                name   = verified_role_name,
                                reason = "Creating missing Verified role"
                            )
                        except Forbidden:
                            raise PermissionError("Sorry, I wasn't able to create the Verified role. "
                                                  "Please ensure I have the ``Manage Roles`` permission.")

                    if not verified_role in author.roles:
                        add_roles.add(verified_role)

        if not unverified:
            if group_roles and roblox_user:
                role_binds, group_ids, _ = await self.get_binds(guild_data=guild_data, guild=guild, trello_board=trello_board)

                if role_binds:
                    if isinstance(role_binds, list):
                        role_binds = role_binds[0]

                    for group_id, data in role_binds.get("groups", {}).items():
                        group = roblox_user.groups.get(group_id)

                        for bind_id, bind_data in data.get("binds", {}).items():
                            rank = None
                            bind_nickname = bind_data.get("nickname")
                            bound_roles = bind_data.get("roles")

                            try:
                                rank = int(bind_id)
                            except ValueError:
                                pass

                            if group:
                                user_rank = group.user_rank_id

                                if bind_id == "0":
                                    if bound_roles:
                                        for role_id in bound_roles:
                                            int_role_id = role_id.isdigit() and int(role_id)
                                            role = find(lambda r: (int_role_id and r.id == int_role_id) or r.name == role_id, author.roles)

                                            if role:
                                                remove_roles.add(role)

                                elif (bind_id == "all" or rank == user_rank) or (rank and (rank < 0 and user_rank >= abs(rank))):
                                    if not bound_roles:
                                        bound_roles = {group.user_rank_name}

                                    for role_id in bound_roles:
                                        int_role_id = role_id.isdigit() and int(role_id)
                                        role = find(lambda r: (int_role_id and r.id == int_role_id) or r.name == role_id, guild.roles)

                                        if not role:
                                            if bind_data.get("trello"):
                                                try:
                                                    role = await guild.create_role(name=role_id)
                                                except Forbidden:
                                                    raise PermissionError(f"Sorry, I wasn't able to create the role {role_id}."
                                                                        "Please ensure I have the ``Manage Roles`` permission.")
                                                else:
                                                    add_roles.add(role)

                                        else:
                                            add_roles.add(role)

                                    if nickname and bind_nickname and bind_nickname != "skip":
                                        if author.top_role == role:
                                            top_role_nickname = await self.get_nickname(author=author, group=group, template=bind_nickname, roblox_user=roblox_user)

                                        resolved_nickname = await self.get_nickname(author=author, group=group, template=bind_nickname, roblox_user=roblox_user)

                                        if resolved_nickname and not resolved_nickname in possible_nicknames:
                                            possible_nicknames.append([role, resolved_nickname])
                                else:
                                    for role_id in bound_roles:
                                        int_role_id = role_id.isdigit() and int(role_id)
                                        role = find(lambda r: (int_role_id and r.id == int_role_id) or r.name == role_id, guild.roles)

                                        if role and role in author.roles:
                                            remove_roles.add(role)

                            else:
                                if bind_id == "0":
                                    if bound_roles:
                                        for role_id in bound_roles:
                                            int_role_id = role_id.isdigit() and int(role_id)
                                            role = find(lambda r: (int_role_id and r.id == int_role_id) or r.name == role_id, guild.roles)

                                            if not role:
                                                if bind_data.get("trello"):
                                                    try:
                                                        role = await guild.create_role(name=role_id)
                                                    except Forbidden:
                                                        raise PermissionError(f"Sorry, I wasn't able to create the role {role_id}."
                                                                                "Please ensure I have the ``Manage Roles`` permission.")
                                                    else:
                                                        add_roles.add(role)

                                            else:
                                                add_roles.add(role)


                                        if nickname and bind_nickname and bind_nickname != "skip":
                                            if author.top_role == role:
                                                top_role_nickname = await self.get_nickname(author=author, group=group, template=bind_nickname, roblox_user=roblox_user)

                                            resolved_nickname = await self.get_nickname(author=author, group=group, template=bind_nickname, roblox_user=roblox_user)

                                            if resolved_nickname and not resolved_nickname in possible_nicknames:
                                                possible_nicknames.append([role, resolved_nickname])

                        if group:
                            user_rank = group.user_rank_id

                            for bind_range in data.get("ranges", []):
                                bind_nickname = bind_range.get("nickname")
                                bound_roles = bind_range.get("roles", set())

                                if bind_range["low"] <= user_rank <= bind_range["high"]:
                                    if not bound_roles:
                                        bound_roles = {group.user_rank_name}

                                    for role_id in bound_roles:
                                        int_role_id = role_id.isdigit() and int(role_id)
                                        role = find(lambda r: (int_role_id and r.id == int_role_id) or r.name == role_id, guild.roles)

                                        if not role:
                                            if bind_range.get("trello"):
                                                try:
                                                    role = await guild.create_role(name=role_id)
                                                except Forbidden:
                                                    raise PermissionError(f"Sorry, I wasn't able to create the role {role_id}."
                                                                        "Please ensure I have the ``Manage Roles`` permission.")

                                        if roles and role:
                                            add_roles.add(role)

                                            if nickname and author.top_role == role and bind_nickname:
                                                top_role_nickname = await self.get_nickname(author=author, group=group, template=bind_nickname, roblox_user=roblox_user)

                                        if nickname and bind_nickname and bind_nickname != "skip":
                                            resolved_nickname = await self.get_nickname(author=author, group=group, template=bind_nickname, roblox_user=roblox_user)

                                            if resolved_nickname and not resolved_nickname in possible_nicknames:
                                                possible_nicknames.append([role, resolved_nickname])
                                else:
                                    for role_id in bound_roles:
                                        int_role_id = role_id.isdigit() and int(role_id)
                                        role = find(lambda r: (int_role_id and r.id == int_role_id) or r.name == role_id, guild.roles)

                                        if role and role in author.roles:
                                            remove_roles.add(role)

                if group_roles and group_ids:
                    author_groups = author_data and author_data.get("groups", {})
                    updated_info = False

                    for group_id, group_data in group_ids.items():
                        if group_id != "0":
                            group = roblox_user.groups.get(str(group_id))

                            if group:
                                group_role = find(lambda r: r.name == group.user_rank_name, guild.roles)

                                if not group_role:
                                    if guild_data.get("dynamicRoles", DEFAULTS.get("dynamicRoles")):
                                        try:
                                            group_role = await guild.create_role(name=group.user_rank_name)
                                        except Forbidden:
                                            raise PermissionError(f"Sorry, I wasn't able to create the role {group.user_rank_name}."
                                                                "Please ensure I have the ``Manage Roles`` permission.")

                                """
                                for roleset in group.rolesets:
                                    has_role = find(lambda r: r.name == roleset["name"], author.roles)

                                    if has_role:
                                        if group.user_role != roleset["name"]:
                                            remove_roles.add(has_role)
                                """

                                if author_data:
                                    if author_groups:
                                        author_groups[roblox_user.id] = author_groups.get(roblox_user.id) or {}
                                        roblox_user_groups = author_groups[roblox_user.id]
                                        matching_group = roblox_user_groups.get(group_id)

                                        if matching_group:
                                            rank_name = matching_group["rankName"]

                                            if rank_name != group.user_rank_name:
                                                has_role = find(lambda r: r.name == rank_name, author.roles)

                                                if has_role:
                                                    remove_roles.add(has_role)

                                                matching_group["rankName"] = group.user_rank_name
                                                matching_group["rankID"] = group.user_rank_id

                                                author_groups[roblox_user.id][group_id] = matching_group
                                                author_data["groups"] = author_groups
                                                updated_info = True
                                        else:
                                            author_groups[roblox_user.id] = author_groups.get(roblox_user.id) or {}
                                            author_groups[roblox_user.id][group_id] = {"rankName": group.user_rank_name, "rankID": group.user_rank_id}
                                            author_data["groups"] = author_groups
                                            updated_info = True
                                    else:
                                        author_data["groups"] = author_data.get("groups", {})
                                        author_data["groups"][roblox_user.id] = author_data["groups"].get(roblox_user.id) or {}
                                        author_data["groups"][roblox_user.id][group_id] = {"rankName": group.user_rank_name, "rankID": group.user_rank_id}
                                        author_groups = author_data["groups"]
                                        author_data["groups"] = author_groups
                                        updated_info = True

                                if group_role:
                                    add_roles.add(group_role)

                                group_nickname = group_data.get("nickname")

                                if nickname and group_nickname:
                                    if author.top_role == group_role and group_nickname:
                                        top_role_nickname = await self.get_nickname(author=author, group=group, template=group_nickname, roblox_user=roblox_user)

                                    if group_nickname and group_nickname != "skip":
                                        resolved_nickname = await self.get_nickname(author=author, group=group, template=group_nickname, roblox_user=roblox_user)

                                        if resolved_nickname and not resolved_nickname in possible_nicknames:
                                            possible_nicknames.append([group_role, resolved_nickname])
                            else:
                                # remove old group role
                                if author_data and author_groups:
                                    author_groups[roblox_user.id] = author_groups.get(roblox_user.id) or {}
                                    roblox_user_groups = author_groups[roblox_user.id]
                                    matching_group = roblox_user_groups.get(group_id)

                                    if matching_group:
                                        rank_name = matching_group["rankName"]
                                        has_role = find(lambda r: r.name == rank_name, author.roles)

                                        if has_role:
                                            remove_roles.add(has_role)

                                        matching_group["rankName"] = "Guest"
                                        matching_group["rankID"] = 0
                                        author_groups[roblox_user.id].pop(group_id, None)

                                        author_groups[roblox_user.id][group_id] = matching_group
                                        author_data["groups"] = author_groups
                                        updated_info = True


                    if updated_info:
                        await self.r.table("users").get(str(author.id)).replace(author_data).run()

        if roles:
            add_roles = add_roles.difference(author.roles).difference(remove_roles)

            try:
                if add_roles:
                    await author.add_roles(*add_roles, reason="Adding group roles")

                if guild_data.get("allowOldRoles", DEFAULTS.get("allowOldRoles")):
                    remove_roles = set()

                if remove_roles:
                    await author.remove_roles(*remove_roles, reason="Removing old roles")

            except Forbidden:
                raise PermissionError("I was unable to sufficiently add roles to the user. Please ensure that "
                                      "I have the ``Manage Roles`` permission.")

        if nickname:
            if not unverified:
                if possible_nicknames:
                    if len(possible_nicknames) == 1:
                        nickname = possible_nicknames[0][1]
                    else:
                        # get highest role with a nickname
                        highest_role = sorted(possible_nicknames, key=lambda e: e[0].position, reverse=True)

                        if highest_role:
                            nickname = highest_role[0][1]

                else:
                    nickname = top_role_nickname or await self.get_nickname(template=guild_data.get("nicknameTemplate", DEFAULTS.get("nicknameTemplate")), author=author, roblox_user=roblox_user)

                if isinstance(nickname, bool):
                    nickname = self.get_nickname(template=guild_data.get("nicknameTemplate", DEFAULTS.get("nicknameTemplate")), roblox_user=roblox_user, author=author)

            if nickname and nickname != author.display_name:
                try:
                    await author.edit(nick=nickname)
                except Forbidden:
                    if guild.owner == author:
                        errors.append("Since you're the Server Owner, I cannot edit your nickname. You may ignore this message; verification will work for normal users.")
                    else:
                        errors.append("I was unable to edit your nickname. Please ensure I have the ``Manage Roles`` permission, and drag my roles above the other roles.")

        if unverified:
            raise UserNotVerified

        if not roblox_user:
            roblox_user, _ = await self.get_user(author=author, guild=guild, author_data=author_data)

        return [r.name for r in add_roles], [r.name for r in remove_roles], nickname, errors, roblox_user


    async def get_group(self, group_id, rolesets=False):
        group_id = str(group_id)
        group = self.cache["groups"].get(group_id)

        if group and group.rolesets:
            return group

        #text, _ = await fetch(f"{API_URL}/groups/{group_id}", raise_on_failure=False)

        text, _ = await fetch(f"{API_URL}/groups/{group_id}", raise_on_failure=False)

        try:
            json_data = json.loads(text)
        except json.decoder.JSONDecodeError:
            raise RobloxAPIError
        else:
            if json_data.get("Id"):
                rolesets = json_data.get("Roles")

                if not group:
                    group = Group(group_id=group_id, group_data=json_data, version="old", rolesets=rolesets)
                else:
                    group.load_json(json_data, version="old")

                self.cache["groups"][group_id] = group

                return group

        """
        text, _ = await fetch(f"{GROUP_API}/v1/groups/{group_id}", raise_on_failure=False)

        try:
            json_data = json.loads(text)
        except json.decoder.JSONDecodeError:
            raise RobloxAPIError
        else:
            if json_data.get("id"):
                if rolesets:
                    text_rolesets, _ = await fetch(f"{GROUP_API}/v1/groups/{group_id}/roles", raise_on_failure=False)

                    try:
                        json_data_rolesets = json.loads(text_rolesets)
                    except json.decoder.JSONDecodeError:
                        raise RobloxAPIError

                    rolesets = json_data_rolesets.get("roles")

                if not group:
                    group = Group(group_id=group_id, group_data=json_data, version=1, rolesets=rolesets)
                else:
                    group.load_json(json_data, version=1)

                self.cache["groups"][group_id] = group

                return group
        """

        # text, _ = await fetch(f"https://api.roblox.com/groups/{group_id}", raise_on_failure=False)

        raise RobloxNotFound

    async def get_user(self, *args, author=None, guild=None, username=None, roblox_id=None, author_data=None, everything=False, basic_details=True, send_embed=False, response=None) -> Tuple:
        guild = guild or getattr(author, "guild", False)
        guild_id = guild and str(guild.id)

        roblox_account = accounts = discord_profile = None
        embed = None

        if send_embed:
            if not response:
                raise BadUsage("Must supply response object for embed sending")

            embed = [Embed(title="Loading..."), response]

        if author:
            author_id = str(author.id)
            author_data = author_data or await self.r.table("users").get(author_id).run() or {}

            discord_profile = self.cache["discord_profiles"].get(author_id)

            if discord_profile:
                if guild:
                    roblox_account = discord_profile.guilds.get(guild_id)
                else:
                    roblox_account = discord_profile.primary_account

                if roblox_account:
                    await roblox_account.sync(*args, author=author, embed=embed, everything=everything, basic_details=basic_details)

                    return roblox_account, discord_profile.accounts


            roblox_accounts = author_data.get("robloxAccounts", {})
            accounts = roblox_accounts.get("accounts", [])
            guilds = roblox_accounts.get("guilds", {})

            roblox_account = guild and guilds.get(guild_id) or author_data.get("robloxID")
            primary_account = author_data.get("robloxID")

            if roblox_account:
                if not discord_profile:
                    discord_profile = DiscordProfile(author_id)

                    if primary_account:
                        discord_profile.primary_account = RobloxUser(roblox_id=primary_account)
                        await discord_profile.primary_account.sync()

                    discord_profile.accounts = accounts


                roblox_user = self.cache["roblox_users"].get(roblox_account) or RobloxUser(roblox_id=roblox_account)

                await roblox_user.sync(*args, author=author, embed=embed, everything=everything, basic_details=basic_details)

                if guild:
                    discord_profile.guilds[guild_id] = roblox_user

                self.cache["discord_profiles"][author_id] = discord_profile
                return roblox_user, accounts

            else:
                if accounts:
                    return None, accounts
                else:
                    raise UserNotVerified

            raise UserNotVerified

        else:
            if not (roblox_id or username):
                raise BadUsage("Must supply a username or ID")

            if not roblox_id:
                roblox_id, username = await self.get_roblox_id(username)

            if roblox_id:
                roblox_user = self.cache["roblox_users"].get(roblox_id) or RobloxUser(roblox_id=roblox_id)

                if not roblox_user:
                    raise UserNotVerified

                await roblox_user.sync(*args, author=author, embed=embed, everything=everything, basic_details=basic_details)
                return roblox_user, None

            raise BadUsage("Unable to resolve a user")


        raise UserNotVerified


    async def verify_as(self, author, guild=None, *, author_data=None, primary=False, trello_options=None, update_user=True, trello_board=None, response=None, guild_data=None, username=None, roblox_id=None) -> bool:
        if not (username or roblox_id):
            raise BadUsage("Must supply either a username or roblox_id to verify_as.")

        guild_data = guild_data or {}
        trello_options = trello_options or {}

        if not trello_options and trello_board:
            trello_options, _ = await get_options(trello_board)

        if trello_options:
            guild_data.update(trello_options)

        allow_reverify = guild_data.get("allowReVerify", DEFAULTS.get("allowReVerify"))

        guild = guild or author.guild
        author_data = author_data or await self.r.table("users").get(str(author.id)).run() or {}

        invalid_roblox_names = 0

        while not roblox_id:
            try:
                roblox_id, username = await self.get_roblox_id(username)
            except RobloxNotFound:
                if response:
                    message = await response.error("There was no Roblox account found with your query.\n"
                                                   "Please try again.")

                    username = (await response.prompt([{
                        "prompt": "Please specify your Roblox username.",
                        "name": "username"
                    }], dm=True, no_dm_post=True))["username"]

                    response.delete(message)

                invalid_roblox_names += 1

            if invalid_roblox_names == 5:
                raise Error("Too many invalid attempts. Please try again later.")

        if not username:
            roblox_id, username = await self.get_roblox_username(roblox_id)

        if roblox_id in author_data.get("robloxAccounts", {}).get("accounts", []) or author_data.get("robloxID") == roblox_id:
            # TODO: clear cache
            await self.verify_member(author, roblox_id, guild=guild, author_data=author_data, allow_reverify=allow_reverify, primary_account=primary)

            if update_user:
                try:
                    await self.update_member(
                        author,
                        guild       = guild,
                        roles       = True,
                        nickname    = True,
                        author_data = author_data)

                except BloxlinkBypass:
                    pass

            return username

        else:
            # prompts
            if response:
                args = await response.prompt([
                    {
                        "prompt": f"Welcome, **{username}!** Please select a method of verification: ``code`` or ``game``",
                        "type": "choice",
                        "choices": ["code", "game"],
                        "name": "verification_choice"
                    }
                ], dm=True, no_dm_post=True)

                if args["verification_choice"] == "code":
                    code = self.generate_code()

                    msg1 = await response.send(f"To confirm that you own this Roblox account, please put this code in your description or status:", dm=True, no_dm_post=True)
                    msg2 = await response.send(f"```{code}```", dm=True, no_dm_post=True)

                    response.delete(msg1, msg2)

                    _ = await response.prompt([{
                        "prompt": "Then, say ``done`` to continue.",
                        "name": "verification_next",
                        "type": "choice",
                        "choices": ["done"]
                    }], embed=False, dm=True, no_dm_post=True)

                    if await self.validate_code(roblox_id, code):
                        # user is now validated; add their roles
                        await self.verify_member(author, roblox_id, allow_reverify=allow_reverify, guild=guild, author_data=author_data, primary_account=primary)

                        return username

                    failures = 0
                    failed = False

                    while not await self.validate_code(roblox_id, code):
                        if failures == 5:
                            failed = True
                            break

                        failures += 1

                        _ = await response.prompt([
                            {
                                "prompt": "Unable to find the code on your profile. Please say ``done`` to search again or ``cancel`` to cancel.",
                                "type": "choice",
                                "choices": ["done"],
                                "name": "retry"
                            }
                        ], error=True, dm=True, no_dm_post=True)

                        attempt = await self.validate_code(roblox_id, code)

                        if attempt:
                            await self.verify_member(author, roblox_id, allow_reverify=allow_reverify, author_data=author_data, guild=guild, primary_account=primary)
                            return username

                    if failed:
                        raise Error(f"{author.mention}, too many failed attempts. Please run this command again and retry.")

                elif args["verification_choice"] == "game":
                    raise NotImplementedError

            # except CancelledPrompt:
            #	pass

    @staticmethod
    async def apply_perks(roblox_user, embed):
        if roblox_user:
            bloxlink_group = roblox_user.groups.get("3587262")
            user_tags = []

            if bloxlink_group:
                bloxlink_user_rank = bloxlink_group.user_rank_name

                if bloxlink_user_rank in ("Developer", "Bloxlink"):
                    user_tags.append("Bloxlink Developer")
                    user_tags.append("Bloxlink Staff")
                    embed.colour = DEV_COLOR
                elif bloxlink_user_rank in ("Helpers", "Mods"):
                    user_tags.append("Bloxlink Staff")
                    embed.colour = STAFF_COLOR
                elif bloxlink_user_rank == "Community Manager":
                    user_tags.append("Bloxlink Community Manager")
                    user_tags.append("Bloxlink Staff")
                    embed.colour = COMMUNITY_MANAGER_COLOR
                elif bloxlink_user_rank == "VIP Members":
                    user_tags.append("Bloxlink VIP Member")
                    embed.colour = VIP_MEMBER_COLOR

            if user_tags:
                embed.add_field(name="User Tags", value="\n".join(user_tags))



    async def __setup__(self):
        while True:
            Roblox.cache = {"usernames_to_ids": {}, "roblox_users": {}, "discord_profiles": {}, "groups": {}}
            await asyncio.sleep(60 * 10)



class DiscordProfile:
    __slots__ = "id", "primary_account", "accounts", "guilds"

    def __init__(self, author_id, **kwargs):
        self.id = author_id

        self.primary_account = kwargs.get("primary_account")
        self.accounts = kwargs.get("accounts", [])
        self.guilds = kwargs.get("guilds", {})

    def __eq__(self, other):
        return self.id == getattr(other, "id", None)

class Group(Bloxlink.Module):
    __slots__ = ("name", "group_id", "description", "rolesets", "owner", "member_count",
                 "embed_url", "url", "user_rank_name", "user_rank_id")

    def __init__(self, group_id, group_data, version=1, my_roles=None, rolesets=None):
        self.group_id = str(group_id)

        self.name = None
        self.description = None
        self.owner = None
        self.member_count = None
        self.rolesets = []
        self.version = version
        self.url = f"https://www.roblox.com/My/Groups.aspx?gid={self.group_id}"

        self.user_rank_name = None
        self.user_rank_id = None

        self.load_json(group_data, version=version, my_roles=my_roles, rolesets=rolesets)

    def load_json(self, group_data, version, my_roles=None, rolesets=None):

        if version == 1 or version == 2:
            self.name = self.name or group_data.get("name", "N/A")
            self.member_count = self.member_count or group_data.get("memberCount", 0)
            self.description = self.description or group_data.get("description", "")

            self.user_rank_name = self.user_rank_name or (my_roles and my_roles.get("name", "").strip())
            self.user_rank_id = self.user_rank_id or (my_roles and my_roles.get("rank"))

            self.version = version

            self.rolesets = self.rolesets or rolesets or []
        elif version == "old":
            self.name = self.name = group_data.get("Name", "N/A")
            self.owner = self.owner or group_data.get("Owner")
            self.description = self.description or group_data.get("Description", "")
            self.rolesets = self.rolesets or group_data.get("Roles", [])

            self.version = "old"


    def __str__(self):
        return f"Group ({self.name or self.group_id})"

    def __repr__(self):
        return self.__str__()

class RobloxUser(Bloxlink.Module):
    __slots__ = ("username", "id", "discord_id", "verified", "complete", "more_details", "groups",
                 "avatar", "premium", "presence", "badges", "description", "banned", "age", "created",
                 "join_date", "profile_link", "session", "embed")

    def __init__(self, *, username=None, roblox_id=None, discord_id=None, **kwargs):
        self.username = username
        self.id = roblox_id
        self.discord_id = discord_id

        self.verified = False
        self.complete = False
        self.more_details = False
        self.partial = False

        self.groups = kwargs.get("groups", {})
        self.avatar = kwargs.get("avatar")
        self.premium = kwargs.get("premium", False)
        self.presence = kwargs.get("presence")
        self.badges = kwargs.get("badges", [])
        self.description = kwargs.get("description", "")
        self.banned = kwargs.get("banned", False)
        self.created =  kwargs.get("created", None)

        self.embed = None

        self.age = 0
        self.join_date = None
        self.profile_link = roblox_id and f"https://www.roblox.com/users/{roblox_id}/profile"

    @staticmethod
    async def get_details(*args, author=None, username=None, roblox_id=None, everything=False, basic_details=False, roblox_user=None, embed=None):
        if everything:
            basic_details = True

        roblox_data = {
            "username": username,
            "id": roblox_id,
            "groups": {},
            "presence": None,
            "premium": False,
            "badges": [],
            "avatar": None,
            "profile_link": roblox_id and f"https://www.roblox.com/users/{roblox_id}/profile",
            "banned": False,
            "description": "",
            "age": 0,
            "join_data": None
        }


        roblox_user_from_cache = None

        if username:
            cache_find = Roblox.cache["usernames_to_ids"].get(username)

            if cache_find:
                roblox_id, username = cache_find

            if roblox_id:
                roblox_user_from_cache = Roblox.cache["roblox_users"].get(roblox_id)

        if roblox_user_from_cache and roblox_user_from_cache.verified:
            roblox_data["id"] = roblox_id or roblox_user_from_cache.id
            roblox_data["username"] = username or roblox_user_from_cache.username
            roblox_data["groups"] = roblox_user_from_cache.groups
            roblox_data["avatar"] = roblox_user_from_cache.avatar
            roblox_data["premium"] = roblox_user_from_cache.premium
            roblox_data["presence"] = roblox_user_from_cache.presence
            roblox_data["badges"] = roblox_user_from_cache.badges
            roblox_data["banned"] = roblox_user_from_cache.banned
            roblox_data["join_date"] = roblox_user_from_cache.join_date
            roblox_data["description"] = roblox_user_from_cache.description
            roblox_data["age"] = roblox_user_from_cache.age

        if roblox_id and not username:
            roblox_id, username = await Roblox.get_roblox_username(roblox_id)
            roblox_data["username"] = username
            roblox_data["id"] = roblox_id
        elif not roblox_id and username:
            roblox_id, username = await Roblox.get_roblox_id(username)
            roblox_data["username"] = username
            roblox_data["id"] = roblox_id

        if not (username and roblox_id):
            return None

        if embed:
            sent_embed = await embed[1].send(embed=embed[0])

            if not sent_embed:
                embed = None
            else:
                embed.append(sent_embed)

                if basic_details or "username" in args:
                    embed[0].add_field(name="Username", value=username)

                if basic_details or "id" in args:
                    embed[0].add_field(name="ID", value=roblox_id)


        if roblox_user:
            roblox_user.username = username
            roblox_user.id = roblox_id


        async def avatar():
            if roblox_data.get("avatar"):
                avatar_url = roblox_data["avatar"]
            else:
                avatar_url, _ = await fetch(f"{BASE_URL}/bust-thumbnail/json?userId={roblox_data['id']}&height=180&width=180")

                try:
                    avatar_url = json.loads(avatar_url)
                except json.decoder.JSONDecodeError:
                    raise RobloxAPIError
                else:
                    avatar_url = avatar_url.get("Url")

                    if roblox_user:
                        roblox_user.avatar = avatar_url

                    roblox_data["avatar"] = avatar_url

            if embed:
                embed[0].set_thumbnail(url=avatar_url)
                embed[0].set_author(name=author and str(author) or roblox_data["username"], icon_url=author and author.avatar_url or avatar_url, url=roblox_data.get("profile_link")) # unsure what this does with icon_url if there's no author

        async def presence():
            if roblox_data.get("presence"):
                presence = roblox_data["presence"]
            else:
                presence, _ = await fetch(f"{API_URL}/users/{roblox_data['id']}/onlinestatus")

                try:
                    presence = json.loads(presence)
                except json.decoder.JSONDecodeError:
                    raise RobloxAPIError
                else:
                    presence_type = presence.get("UserPresenceType")

                    if presence_type == 0:
                        presence = "offline"
                    elif presence_type == 1:
                        presence = "browsing the website"
                    elif presence_type == 2:
                        if presence.get("PlaceID") is not None:
                            presence = f"playing [{presence.get('LastLocation')}](https://www.roblox.com/games/{presence.get('PlaceId')}/-"
                        else:
                            presence = "in game"
                    elif presence_type == 3:
                        presence = "creating"

                if roblox_user:
                    roblox_user.presence = presence

                roblox_data["presence"] = presence

            if embed:
                embed[0].add_field(name="Presence", value=presence)

        async def membership_and_badges():
            badges = roblox_data["badges"]

            if roblox_data["premium"]:
                premium = roblox_data["premium"]
            else:
                data, _ = await fetch(f"{BASE_URL}/badges/roblox?userId={roblox_data['id']}")

                premium = None

                try:
                    data = json.loads(data)
                except json.decoder.JSONDecodeError:
                    raise RobloxAPIError

                for badge in data.get("RobloxBadges", []):
                    if "Builders Club" in badge["Name"]:
                        premium = True
                    else:
                        badges.append(badge["Name"])

                #roblox_data["badges"] = badges
                roblox_data["premium"] = premium

                if roblox_user:
                    roblox_user.badges = badges
                    roblox_user.premium = premium

            if embed:
                if premium:
                    #embed[0].add_field(name="Membership", value=membership)
                    #embed[0].title = f"<:robloxpremium:614583826538299394> {embed[0].title}"
                    # TODO
                    pass

                if (everything or "badges" in args) and badges:
                    embed[0].add_field(name="Badges", value=", ".join(badges))

        async def groups():
            groups = roblox_data["groups"]

            if roblox_data.get("groups"):
                groups = roblox_data["groups"]
            else:
                #group_json, _ = await fetch(f"{API_URL}/users/{roblox_data['id']}/groups")
                group_json, _ = await fetch(f"{GROUP_API}/v2/users/{roblox_data['id']}/groups/roles")
                # https://groups.roblox.com/v2/users/1/groups/roles

                try:
                    group_json = json.loads(group_json)
                except json.decoder.JSONDecodeError:
                    raise RobloxAPIError
                else:
                    for group_data in group_json.get("data", []):
                        group_data, my_roles = group_data.get("group"), group_data.get("role")
                        group_id = str(group_data["id"])
                        groups[group_id] = Group(group_id, group_data=group_data, my_roles=my_roles, version=2)

                    if roblox_user:
                        roblox_user.groups = groups

            #if embed:
            #   if groups and (everything or "groups" in args):
            #        embed[0].add_field(name="Groups", value=(", ".join(x.name for x in groups.values()))[:1000])


        async def profile():
            if roblox_data.get("description") or roblox_data.get("age"):
                description = roblox_data.get("description")
                age = roblox_data.get("age")
                join_date = roblox_data.get("join_date")
                banned = roblox_data.get("banned") # <:ban:476838302092230672>
                created = roblox_data.get("created")
            else:
                banned = description = age = join_date = created = None

                data, _ = await fetch(f"https://users.roblox.com/v1/users/{roblox_data['id']}")

                try:
                    profile = json.loads(data)
                except json.decoder.JSONDecodeError:
                    raise RobloxAPIError
                else:
                    description = profile.get("description")
                    created = profile.get("created")
                    banned = profile.get("isBanned")

                    roblox_data["description"] = description
                    roblox_data["created"] = created
                    roblox_data["banned"] = banned

            if not age:
                today = datetime.today()
                roblox_user_age = parser.parse(created).replace(tzinfo=None)
                age = (today - roblox_user_age).days

                join_date = f"{roblox_user_age.month}/{roblox_user_age.day}/{roblox_user_age.year}"

                roblox_data["age"] = age
                roblox_data["join_date"] = join_date

            if embed:
                if everything or "age" in args:
                    text = ""

                    if age >= 365:
                        years = math.floor(age/365)
                        ending = f"year{((years > 1 or years == 0) and 's') or ''}"
                        text = f"{years} {ending} old"
                    else:
                        ending = f"day{((age > 1 or age == 0) and 's') or ''}"
                        text = f"{age} {ending} old"

                    embed[0].add_field(name="Account Age", value=f"{text} ({join_date})")

                if (everything or "banned" in args) and banned:
                    embed[0].description = "<:ban:476838302092230672> This user is _banned._"

                    for i, field in enumerate(embed[0].fields):
                        if field.name == "Username":
                           embed[0].set_field_at(i, name="Username", value=f"~~{field.value}~~")

                if description and (everything or "description" in args):
                    embed[0].add_field(name="Description", value=description[0:1000], inline=False)


            if roblox_user:
                roblox_user.description = description
                roblox_user.age = age
                roblox_user.join_date = join_date
                roblox_user.created = created
                roblox_user.banned = banned


        # fast operations
        if basic_details or "avatar" in args:
            await avatar()

        #if basic_details or "presence" in args:
        #    await presence()

        if everything or "premium" in args or "badges" in args:
            await membership_and_badges()

        if basic_details or "groups" in args:
            await groups()

        if everything or "description" in args or "blurb" in args or "age" in args or "banned" in args:
            await profile()

        if embed:
            embed[0].title = None
            await Roblox.apply_perks(roblox_user, embed=embed[0])
            await embed[2].edit(embed=embed[0])


        return roblox_data

    async def sync(self, *args, author=None, basic_details=True, embed=None, everything=False):
        try:
            await self.get_details(
                *args,
                username = self.username,
                roblox_id = self.id,
                everything = everything,
                basic_details = basic_details,
                embed = embed,
                roblox_user = self,
                author=author
            )

        except RobloxAPIError:
            self.complete = False

            if self.discord_id and self.id:
                # TODO: set username from database
                self.partial = True # only set if there is a db entry for the user with the username
            else:
                raise RobloxAPIError
        else:
            self.complete = self.complete or everything
            self.verified = True
            self.partial = not everything
            self.profile_link = self.profile_link or f"https://www.roblox.com/users/{self.id}/profile"

    def __eq__(self, other):
        return self.id == getattr(other, "id", None) or self.username == getattr(other, "username", None)

    def __str__(self):
        return self.id
