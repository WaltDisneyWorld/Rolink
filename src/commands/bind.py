import re
from resources.structures.Bloxlink import Bloxlink  # pylint: disable=import-error
from resources.exceptions import PermissionError, Error, RobloxNotFound, Message, CancelCommand  # pylint: disable=import-error
from resources.constants import NICKNAME_TEMPLATES, ARROW, LIMITS  # pylint: disable=import-error
from discord import Embed
from discord.errors import Forbidden, NotFound, HTTPException
from discord.utils import find
from aiotrello.exceptions import TrelloUnauthorized, TrelloNotFound, TrelloBadRequest

bind_num_range = re.compile(r"([0-9]+)\-([0-9]+)")
roblox_group_regex = re.compile(r"roblox.com/groups/(\d+)/")

get_group, parse_trello_binds, count_binds, get_binds = Bloxlink.get_module("roblox", attrs=["get_group", "parse_trello_binds", "count_binds", "get_binds"])
fetch, is_premium = Bloxlink.get_module("utils", attrs=["fetch", "is_premium"])

API_URL = "https://api.roblox.com"
FREE_BIND_COUNT, PREM_BIND_COUNT = LIMITS["BINDS"]["FREE"], LIMITS["BINDS"]["PREMIUM"]

@Bloxlink.command
class BindCommand(Bloxlink.Module):
    """bind a discord role to a roblox group rank"""

    def __init__(self):
        self.aliases = ["newbind"]
        self.permissions = Bloxlink.Permissions().build("BLOXLINK_MANAGER")
        self.category = "Binds"

    @staticmethod
    def find_range(tuple_set, ranges):
        for i, range_ in enumerate(ranges):
            if range_["low"] == tuple_set[0] and range_["high"] == tuple_set[1]:
                return range_, i

        return {}, 0

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

    async def __main__(self, CommandArgs):
        guild = CommandArgs.message.guild
        response = CommandArgs.response
        guild_data = CommandArgs.guild_data
        trello_board = CommandArgs.trello_board
        prefix = CommandArgs.prefix

        role_binds_trello, group_ids_trello, trello_binds_list = await get_binds(guild_data=guild_data, trello_board=trello_board)

        bind_count = count_binds(guild_data, role_binds=role_binds_trello, group_ids=group_ids_trello)

        if bind_count >= FREE_BIND_COUNT:
            profile, _ = await is_premium(guild.owner)

            if not profile.features.get("premium"):
                raise Error(f"You've exceeded the free bind limit of **{FREE_BIND_COUNT}.** Please delete some with "
                            f"``{prefix}delbind`` before adding any more.\nPremium users may bind up to **{PREM_BIND_COUNT}** binds! "
                            f"See ``{prefix}donate`` for instructions on receiving premium.")

            if bind_count >= PREM_BIND_COUNT:
                raise Error(f"You've exceeded the premium bind limit of **{PREM_BIND_COUNT}.** Please delete some with "
                            f"``{prefix}delbind`` before adding any more.")

        parsed_args = await CommandArgs.prompt([
            {
                "prompt": "A bind is a link between a Roblox group or asset and a Discord role. Please select a "
                          "bind type:\n"
                          f"``group`` {ARROW} bind a Roblox group rank to a Discord role\n"
                          f"``asset`` {ARROW} bind a Roblox catalog asset to a Discord role\n"
                          f"``badge`` {ARROW} bind a Roblox badge to a Discord role\n",
                          # f"``gamepass`` {ARROW} bind a Roblox badge to a Discord role",
                "name": "bind_choice",
                "choices": ["group", "asset", "badge"],
                "formatting": False
            },
            {
                "prompt": "Should these members be given a nickname different from the server-wide ``!nickname``? Please specify a nickname, or "
                          "say ``skip`` to skip this option and default to the server-wide nickname ``!nickname`` template.\n\nYou may use these templates:"
                         f"```{NICKNAME_TEMPLATES}```",
                "name": "nickname",
                "max": 100,
                "type": "string",
                "formatting": False
            }
        ])

        bind_choice = parsed_args["bind_choice"].lower()
        nickname = parsed_args["nickname"]

        if trello_board:
            trello_binds_list = await trello_board.get_list(lambda l: l.name.lower() == "bloxlink binds")

            if not trello_binds_list:
                try:
                    trello_binds_list = await trello_board.create_list(name="Bloxlink Binds")
                except TrelloUnauthorized:
                        await response.error("In order for me to create Trello binds, please add ``@bloxlink`` to your "
                                             "Trello board.")
                except (TrelloNotFound, TrelloBadRequest):
                    pass

            trello_card_binds, _ = await parse_trello_binds(trello_board=trello_board, trello_binds_list=trello_binds_list)
        else:
            trello_binds_list = None
            trello_group_bind = None
            trello_card_binds = {
                "groups": {
                    "entire group": {},
                    "binds": {}
                },
                "assets": {

                }
            }

        if nickname.lower() in ("skip", "done", "next"):
            nickname = None
            nickname_lower = None
        else:
            nickname_lower = nickname.lower()

        if bind_choice == "group":
            parsed_args_group = await CommandArgs.prompt([
                {
                    "prompt": "Please specify the **Group ID** to integrate with. The group ID is the rightmost numbers on your Group URL.",
                    "name": "group",
                    "validation": self.validate_group
                },
                {
                    "prompt": f"Would you like to integrate the entire group to receive roles (binds will be made for _all_ Rolesets), or only select a few ranks to receive a role?\n\n"
                            "Select one: ``entire group`` or ``select ranks``",
                    "name": "type",
                    "type": "choice",
                    "choices": ["entire group", "select ranks"]
                }
            ])


            group = parsed_args_group["group"]
            group_id = group.group_id

            group_ids = guild_data.get("groupIDs", {})
            found_group = trello_card_binds["groups"]["entire group"].get(group_id) or group_ids.get(group_id)

            trello_group_bind = trello_card_binds["groups"]["entire group"].get(group_id)

            if parsed_args_group["type"] == "entire group":
                if found_group:
                    if nickname and found_group["nickname"] != nickname:
                        group_ids[group_id] = {"nickname": nickname, "groupName": group.name}
                        guild_data["groupIDs"] = group_ids

                        await self.r.db("canary").table("guilds").insert(guild_data, conflict="update").run()

                        trello_group_bind = trello_card_binds["groups"]["entire group"].get(group_id)

                        make_trello_card = True

                        if trello_group_bind:
                            for card_data in trello_group_bind["trello"].get("cards", []):
                                card = card_data["card"]

                                try:
                                    await card.edit(desc=card.description.replace(trello_group_bind["nickname"], nickname))
                                except TrelloUnauthorized:
                                    await response.error("In order for me to edit your Trello binds, please add ``@bloxlink`` to your "
                                                         "Trello board.")
                                except (TrelloNotFound, TrelloBadRequest):
                                    pass

                                make_trello_card = False

                            if make_trello_card:
                                try:
                                    await trello_binds_list.create_card(name="Bloxlink Group Bind", desc=f"Group: {group_id}\nNickname: {nickname}")
                                except TrelloUnauthorized:
                                    await response.error("In order for me to edit your Trello binds, please add ``@bloxlink`` to your "
                                                         "Trello board.")
                                except (TrelloNotFound, TrelloBadRequest):
                                    pass

                            if trello_binds_list:
                                trello_binds_list.parsed_bind_data = None

                        raise Message("Since your group is already linked, the nickname was updated.", type="success")
                    else:
                        raise Message("This group is already linked.", type="silly")

                for roleset in group.rolesets:
                    roleset_name = roleset.get("Name") or roleset.get("name")
                    roleset_rank = roleset.get("Rank") or roleset.get("rank")

                    if roleset_rank:
                        discord_role = find(lambda r: r.name == roleset_name, guild.roles)

                        if not discord_role:
                            try:
                                discord_role = await guild.create_role(name=roleset_name)
                            except Forbidden:
                                raise PermissionError("I was unable to create the Discord role. Please ensure my role has the ``Manage Roles`` permission.")

                # add group to guild_data.groupIDs
                group_ids[group_id] = {"nickname": nickname not in ("skip", "next") and nickname, "groupName": group.name}
                guild_data["groupIDs"] = group_ids

                await self.r.db("canary").table("guilds").insert(guild_data, conflict="update").run()

                if trello_binds_list:
                    try:
                        await trello_binds_list.create_card(name="Bloxlink Group Bind", desc=f"Group: {group_id}\nNickname: {nickname}")
                    except TrelloUnauthorized:
                        await response.error("In order for me to edit your Trello binds, please add ``@bloxlink`` to your "
                                             "Trello board.")
                    except (TrelloNotFound, TrelloBadRequest):
                        pass

                raise Message("Success! Your group was successfully linked.", type="success")

            else:
                # select ranks from their group
                # ask if they want to auto-create the binds or select a specific role
                # shows confirmation embed with arrows from rank to discord role

                discord_role = await CommandArgs.prompt([
                    {
                        "prompt": "Please provide a **Discord role name** for this bind.",
                        "name": "role",
                        "type": "role"
                    }
                ])

                discord_role = discord_role["role"]
                role_id = str(discord_role.id)

                new_ranks = {"binds":[], "ranges": []}

                role_binds = guild_data.get("roleBinds") or {}

                if isinstance(role_binds, list):
                    role_binds = role_binds[0]

                role_binds["groups"] = role_binds.get("groups") or {} # {"groups": {"ranges": {}, "binds": {}}}
                role_binds["groups"][group_id] = role_binds["groups"].get(group_id) or {}
                role_binds["groups"][group_id]["binds"] = role_binds["groups"][group_id].get("binds") or {}
                role_binds["groups"][group_id]["ranges"] = role_binds["groups"][group_id].get("ranges") or {}
                role_binds["groups"][group_id]["groupName"] = group.name

                rolesets_embed = Embed(title=f"{group.name} Rolesets", description="\n".join(f"**{x.get('name') or x.get('Name')}** {ARROW} {x.get('Rank') or x.get('rank')}" for x in group.rolesets if x.get('Rank') or x.get('rank')))

                rolesets_embed = await CommandArgs.response.send(embed=rolesets_embed)

                response.delete(rolesets_embed)

                failures = 0

                while True:
                    if failures == 5:
                        raise Error("Too many failed attempts. Please run this command again.")

                    selected_ranks = await CommandArgs.prompt([
                        {
                            "prompt": f"Please select the rolesets that should receive the role **{discord_role}**. "
                                       "You may specify the roleset name or ID. You may provide them in a list, "
                                       "or as a range. You may also say ``everyone`` to capture everyone in the group; "
                                       "and you can negate the number to catch everyone with the rank _and above._\n"
                                       "You can also say ``guest`` to include **all non-group members**.\n"
                                       "Example 1: ``1,4,-6,VIP, 10, 50-100, Staff Members, 255``.\nExample 2: ``"
                                       "-100`` means everyone with rank 100 _and above._\nExample 3: ``everyone`` "
                                       "means everyone in the group.\n\n"
                                       "For your convenience, your Rolesets' names and IDs were sent above.",
                            "name": "ranks",
                            "formatting": False

                        }
                    ])

                    pending_roleset_names = []

                    for rank in selected_ranks["ranks"].replace(" ", "").split(","):
                        if rank.isdigit():
                            new_ranks["binds"].append(str(rank))
                        elif rank in ("all", "everyone"):
                            new_ranks["binds"].append("all")
                        elif rank in ("0", "guest"):
                            new_ranks["binds"].append("0")
                        elif rank[:1] == "-":
                            try:
                                int(rank)
                            except ValueError:
                                pass
                            else:
                                new_ranks["binds"].append(rank)
                        else:
                            range_search = bind_num_range.search(rank)

                            if range_search:
                                num1, num2 = range_search.group(1), range_search.group(2)
                                new_ranks["ranges"].append((num1, num2))
                            else:
                                # they specified a roleset name as a string
                                pending_roleset_names.append(rank)

                    if pending_roleset_names:
                        found = False

                        for roleset in group.rolesets:
                            roleset_name = roleset.get("Name") or roleset.get("name")
                            roleset_rank = roleset.get("Rank") or roleset.get("rank")

                            if roleset_name in pending_roleset_names and roleset_name not in new_ranks["binds"]:
                                new_ranks["binds"].append(str(roleset_rank))
                                found = True

                        if not found:
                            await response.error("Could not find a matching Roleset name. Please try again.")
                            failures += 1

                            continue

                    break

                if new_ranks["binds"]:
                    for x in new_ranks["binds"]:
                        rank = role_binds["groups"][group_id].get("binds", {}).get(x, {})

                        if not isinstance(rank, dict):
                            rank = {"nickname": nickname_lower, "roles": [str(rank)]}

                            if role_id not in rank["roles"]:
                                rank["roles"].append(role_id)
                        else:
                            if role_id not in rank.get("roles", []):
                                rank["roles"] = rank.get("roles") or []
                                rank["roles"].append(role_id)

                                if nickname_lower:
                                    rank["nickname"] = nickname
                                else:
                                    if not rank.get("nickname"):
                                        rank["nickname"] = None

                        role_binds["groups"][group_id]["binds"][x] = rank
                        # trello binds:
                            # rank is in list of ranks
                                # update nickname
                                # append role
                            # else: make new card

                        if trello_binds_list:
                            make_binds_card = True

                            if trello_card_binds:
                                trello_bind_group = trello_card_binds["groups"]["binds"].get(group_id, {}).get("binds")

                                if trello_bind_group:
                                    card_data_ = trello_bind_group.get(x)

                                    if card_data_:
                                        for card in card_data_.get("trello", {}).get("cards", []):
                                            trello_card = card["card"]
                                            trello_ranks = card.get("ranks") or []

                                            if (x in trello_ranks or x == "all") and len(trello_ranks) == 1:
                                                trello_bind_roles = card.get("roles", set())
                                                card_bind_data = [
                                                    f"Group: {group_id}",
                                                    f"Nickname: {(nickname != 'skip' and nickname) or rank.get('nickname') or card_data_.get('nickname') or 'None'}",
                                                ]

                                                trello_bind_roles.add(discord_role.name)
                                                card_bind_data.append(f"Roles: {', '.join(trello_bind_roles)}")

                                                card_bind_data.append(f"Ranks: {card['trello_str']['ranks']}")

                                                trello_card_desc = "\n".join(card_bind_data)

                                                if trello_card_desc != trello_card.description:
                                                    trello_card.description = trello_card_desc

                                                    try:
                                                        await trello_card.edit(desc=trello_card_desc)
                                                    except TrelloUnauthorized:
                                                        await response.error("In order for me to edit your Trello binds, please add ``@bloxlink`` to your "
                                                                             "Trello board.")
                                                    except (TrelloNotFound, TrelloBadRequest):
                                                        pass

                                                    trello_binds_list.parsed_bind_data = None
                                                    make_binds_card = False

                                                    break

                            if make_binds_card:
                                card_bind_data = [
                                    f"Group: {group_id}",
                                    f"Nickname: {nickname != 'skip' and nickname or 'None'}",
                                    f"Roles: {discord_role.name}",
                                ]

                                if x != "all":
                                    card_bind_data.append(f"Ranks: {x}")

                                trello_card_desc = "\n".join(card_bind_data)

                                try:
                                    card = await trello_binds_list.create_card(name="Bloxlink Bind", desc=trello_card_desc)
                                except TrelloUnauthorized:
                                    await response.error("In order for me to edit your Trello binds, please add ``@bloxlink`` to your "
                                                         "Trello board.")
                                except (TrelloNotFound, TrelloBadRequest):
                                    pass

                                trello_binds_list.parsed_bind_data = None

                if new_ranks["ranges"]:
                    role_binds["groups"][group_id]["ranges"] = role_binds["groups"][group_id].get("ranges") or []

                    for x in new_ranks["ranges"]: # list of dictionaries: [{"high": 10, "low": 1, "nickname": ""},...]
                        range_, num = self.find_range(x, role_binds["groups"][group_id]["ranges"])

                        if not role_id in range_.get("roles", []):
                            range_["roles"] = range_.get("roles") or []
                            range_["roles"].append(role_id)

                            if nickname_lower:
                                range_["nickname"] = nickname
                            else:
                                if not range_.get("nickname"):
                                    range_["nickname"] = None

                        if not num:
                            range_["low"] = int(x[0])
                            range_["high"] = int(x[1])
                            role_binds["groups"][group_id]["ranges"].append(range_)

                        if trello_binds_list:
                            make_binds_card = True

                            if trello_card_binds:
                                trello_range_group = trello_card_binds["groups"]["binds"].get(group_id, {}).get("ranges")

                                if trello_range_group:
                                    for trello_range in trello_range_group:
                                        trello_ranks = trello_range["trello"].get("ranks", [])

                                        if trello_range["low"] == range_["low"] and trello_range["high"] == range_["high"] and len(trello_ranks) == 1:
                                            trello_data = trello_range["trello"]
                                            trello_card = trello_data["card"]
                                            trello_bind_roles = trello_range.get("roles", set())
                                            card_bind_data = [
                                                f"Group: {group_id}",
                                                f"Nickname: {(nickname != 'skip' and nickname) or trello_range.get('nickname') or 'None'}",
                                            ]

                                            trello_bind_roles.add(discord_role.name)
                                            card_bind_data.append(f"Roles: {', '.join(trello_bind_roles)}")

                                            card_bind_data.append(f"Ranks: {trello_data['trello_str']['ranks']}")

                                            trello_card_desc = "\n".join(card_bind_data)

                                            if trello_card_desc != trello_card.description:
                                                trello_card.description = trello_card_desc

                                                try:
                                                    await trello_card.edit(desc=trello_card_desc)
                                                except TrelloUnauthorized:
                                                    await response.error("In order for me to edit your Trello binds, please add ``@bloxlink`` to your "
                                                                         "Trello board.")
                                                except (TrelloNotFound, TrelloBadRequest):
                                                    pass

                                                trello_binds_list.parsed_bind_data = None
                                                make_binds_card = False

                                                break

                            if make_binds_card:
                                card_bind_data = [
                                    f"Group: {group_id}",
                                    f"Nickname: {nickname != 'skip' and nickname or 'None'}",
                                    f"Roles: {discord_role.name}",
                                    f"Ranks: {range_['low']}-{range_['high']}"
                                ]

                                trello_card_desc = "\n".join(card_bind_data)

                                try:
                                    card = await trello_binds_list.create_card(name="Bloxlink Range Bind", desc=trello_card_desc)
                                except TrelloUnauthorized:
                                    await response.error("In order for me to edit your Trello binds, please add ``@bloxlink`` to your "
                                                         "Trello board.")
                                except (TrelloNotFound, TrelloBadRequest):
                                    pass

                                trello_binds_list.parsed_bind_data = None


            await self.r.db("canary").table("guilds").insert({
                "id": str(guild.id),
                "roleBinds": role_binds
            }, conflict="update").run()

            text = ["Successfully **bound** rank ID(s): ``"]
            if new_ranks["binds"]:
                text.append(", ".join(new_ranks["binds"]))

            if new_ranks["ranges"]:
                text2 = ""

                if new_ranks["binds"]:
                    text2 = "; "

                text.append(f"{text2}ranges: {', '.join([r[0] + ' - ' + r[1] for r in new_ranks['ranges']])}")

            text.append(f"`` with Discord role **{discord_role}**.")

            text = "".join(text)

            await response.success(text)

        elif bind_choice in ("asset", "badge"):
            bind_choice_title = bind_choice.title()
            bind_choice_plural = f"{bind_choice}s"

            vg_parsed_args = await CommandArgs.prompt([
                {
                   "prompt": f"Please provide the **{bind_choice_title} ID** to use for this bind.",
                   "name": "bind_id",
                   "type": "number",
                   "formatting": False
                },
                {
                   "prompt": "Please provide a **Discord role name** for this bind.",
                   "name": "role",
                   "type": "role"
                },
            ])

            discord_role = vg_parsed_args["role"]

            bind_id = str(vg_parsed_args["bind_id"])
            role_id = str(discord_role.id)

            if bind_choice == "asset":
                text, response_ = await fetch(f"{API_URL}/marketplace/productinfo?assetId={bind_id}")
                json_data = await response_.json()

                display_name = json_data.get("Name")

            elif bind_choice == "badge":
                text, response_ = await fetch(f"https://badges.roblox.com/v1/badges/{bind_id}")
                json_data = await response_.json()

                display_name = json_data.get("displayName")


            role_binds = guild_data.get("roleBinds") or {}

            if isinstance(role_binds, list):
                role_binds = role_binds[0]

            role_binds[bind_choice_plural] = role_binds.get(bind_choice_plural) or {}
            role_binds[bind_choice_plural][bind_id] = role_binds[bind_choice_plural].get(bind_id) or {}

            role_binds[bind_choice_plural][bind_id]["nickname"] = nickname
            role_binds[bind_choice_plural][bind_id]["displayName"] = display_name

            role_binds[bind_choice_plural][bind_id]["roles"] = role_binds[bind_choice_plural][bind_id].get("roles", [])

            roles = role_binds[bind_choice_plural][bind_id]["roles"]

            if not role_id in roles:
                roles.append(role_id)

            role_binds[bind_choice_plural][bind_id]["roles"] = roles

            if trello_binds_list:
                make_binds_card = True

                if trello_card_binds:
                    trello_bind_vg = trello_card_binds.get(bind_choice_plural, {}).get(bind_id)

                    if trello_bind_vg:
                        trello_bind_roles = set(trello_bind_vg.get("roles", set()))

                        for card in trello_bind_vg.get("trello", {})["cards"]:
                            trello_card = card["card"]

                            card_bind_data = [
                                f"{bind_choice_title} ID: {bind_id}",
                                f"Display Name: {display_name}",
                                f"Nickname: {(nickname != 'skip' and nickname) or rank.get('nickname') or card_data_.get('nickname') or 'None'}",
                            ]

                            trello_bind_roles.add(discord_role.name)
                            card_bind_data.append(f"Roles: {', '.join(trello_bind_roles)}")

                            trello_card_desc = "\n".join(card_bind_data)

                            if trello_card_desc != trello_card.description:
                                trello_card.description = trello_card_desc

                                try:
                                    await trello_card.edit(desc=trello_card_desc)
                                except TrelloUnauthorized:
                                    await response.error("In order for me to edit your Trello binds, please add ``@bloxlink`` to your "
                                                         "Trello board.")
                                except (TrelloNotFound, TrelloBadRequest):
                                    pass

                                trello_binds_list.parsed_bind_data = None
                                make_binds_card = False

                                break

                if make_binds_card:
                    card_bind_data = [
                        f"{bind_choice_title} ID: {bind_id}",
                        f"Display Name: {display_name}",
                        f"Nickname: {nickname != 'skip' and nickname or 'None'}",
                        f"Roles: {discord_role.name}",
                    ]

                    trello_card_desc = "\n".join(card_bind_data)

                    try:
                        card = await trello_binds_list.create_card(name=f"Bloxlink {bind_choice_title} Bind", desc=trello_card_desc)
                    except TrelloUnauthorized:
                        await response.error("In order for me to edit your Trello binds, please add ``@bloxlink`` to your "
                                             "Trello board.")
                    except (TrelloNotFound, TrelloBadRequest):
                        pass

                    trello_binds_list.parsed_bind_data = None

            await self.r.db("canary").table("guilds").insert({
                "id": str(guild.id),
                "roleBinds": role_binds
            }, conflict="update").run()

            await response.success(f"Successfully **bound** {bind_choice_title} ``{display_name}`` ({bind_id}) with Discord role **{discord_role}!**")
