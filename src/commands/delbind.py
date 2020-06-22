from resources.structures.Bloxlink import Bloxlink
from discord import Embed
from resources.exceptions import Error, Message
from resources.constants import ARROW
from aiotrello.exceptions import TrelloException
import asyncio

get_binds, get_group, count_binds = Bloxlink.get_module("roblox", attrs=["get_binds", "get_group", "count_binds"])


async def delete_bind_from_cards(type="group", bind_id=None, trello_binds_list=None, bind_data_trello=None, rank=None, high=None, low=None):
    if not (trello_binds_list and bind_data_trello):
        return

    if type == "group":
        if rank in ("main", "everything"):
            for rank_id, rank_data in bind_data_trello.get("binds", {}).items():
                cards = rank_data.get("trello", {}).get("cards")

                if cards:
                    for card_data in cards:
                        try:
                            await card_data["card"].archive()
                        except TrelloException:
                            break
                        else:
                            trello_binds_list.parsed_bind_data = None
            return

        cards = bind_data_trello.get("trello", {}).get("cards")

        if cards:
            if low and high:
                for card_data in cards:
                    ranks = list(card_data.get("ranks") or [])
                    card = card_data["card"]

                    if (not ranks) or (ranks and len(ranks) == 1):
                        try:
                            await card.archive()
                        except TrelloException:
                            break
                        else:
                            if trello_binds_list:
                                trello_binds_list.parsed_bind_data = None
                    else:
                        rank_find = f"{low}-{high}"

                        if rank_find in ranks:
                            ranks.remove(rank_find)

                            new_card_data = [
                                f"Group: {bind_id}",
                            ]

                            nickname = bind_data_trello.get("nickname")
                            roles = bind_data_trello.get("roles")

                            if nickname:
                                new_card_data.append(f"Nickname: {nickname}")

                            if roles:
                                new_card_data.append(f"Roles: {', '.join(card_data['roles'])}")

                            if ranks:
                                new_card_data.append(f"Ranks: {', '.join(ranks)}")

                            try:
                                await card.edit(desc="\n".join(new_card_data))
                            except TrelloException:
                                break
                            else:
                                trello_binds_list.parsed_bind_data = None

            else:
                # archive card if there's only 1 rank, else, remove the rank
                for card_data in cards:
                    ranks = list(card_data.get("ranks") or [])
                    card = card_data["card"]

                    if (not ranks) or (ranks and len(ranks) == 1):
                        try:
                            await card.archive()
                        except TrelloException:
                            break
                        else:
                            if trello_binds_list:
                                trello_binds_list.parsed_bind_data = None
                    else:
                        if rank in ranks:
                            ranks.remove(rank)

                            new_card_data = [
                                f"Group: {bind_id}",
                            ]

                            nickname = bind_data_trello.get("nickname")
                            roles = bind_data_trello.get("roles")

                            if nickname:
                                new_card_data.append(f"Nickname: {nickname}")

                            if roles:
                                new_card_data.append(f"Roles: {', '.join(card_data['roles'])}")

                            if ranks:
                                new_card_data.append(f"Ranks: {', '.join(ranks)}")

                            try:
                                await card.edit(desc="\n".join(new_card_data))
                            except TrelloException:
                                break
                            else:
                                trello_binds_list.parsed_bind_data = None


    elif type == "asset":
        cards = bind_data_trello.get("trello", {}).get("cards", [])

        for card in cards:
            try:
                await card["card"].archive()
            except TrelloException:
                break
            else:
                trello_binds_list.parsed_bind_data = None





@Bloxlink.command
class UnBindCommand(Bloxlink.Module):
    """delete a role bind from your server"""

    def __init__(self):
        self.arguments = [{
            "prompt": "Please specify the group ID that this bind resides in. If this is not a group, " \
			          "specify the bind type found on ``{prefix}viewbinds``(e.g. \"assets\").",
            "name": "bind_id"
        }]

        self.permissions = Bloxlink.Permissions().build("BLOXLINK_MANAGER")
        self.category = "Binds"
        self.aliases = ["delbind", "delbinds"]


    async def __main__(self, CommandArgs):
        guild_data = CommandArgs.guild_data
        trello_board = CommandArgs.trello_board
        prefix = CommandArgs.prefix

        role_binds = guild_data.get("roleBinds", {"groups": {}, "assets": {}})
        role_binds_trello, group_ids_trello, trello_binds_list = await get_binds(guild_data=guild_data, trello_board=trello_board)

        group_ids = guild_data.get("groupIDs", {})

        removed_main_group = False

        if count_binds(guild_data, role_binds=role_binds_trello, group_ids=group_ids_trello) == 0:
            additional = (not trello_binds_list and "\nAdditionally, you may use "
                         f"``{prefix}setup`` to link a Trello board for bind-to-card creation.") or ""
            raise Message(f"You have no bounded roles! Please use ``{prefix}bind`` "
                          f"to make a new role bind. {additional}", type="silly")

        bind_category = CommandArgs.parsed_args["bind_id"]

        role_binds_groups_trello = role_binds_trello["groups"]

        if bind_category.isdigit():
            bind_id = bind_category

            if not (role_binds_groups_trello.get(bind_id) or group_ids_trello.get(bind_id)):
                raise Message("There's no linked group with this ID!", type="silly")

            found_linked_group_trello = group_ids_trello.get(bind_id)
            found_linked_group = group_ids.get(bind_id)

            if found_linked_group_trello:
                parsed_args = await CommandArgs.prompt([{
                    "prompt": "This group is linked as a Main Group. This means anyone who joins from this group will get their role(s), "
                             f"and it lists the users' ranks in ``{prefix}getinfo``. Would you like to remove this entry? ``Y/N``",
                    "type": "choice",
                    "choices": ["yes", "no"],
                    "name": "main_group_choice"
                }])

                if parsed_args["main_group_choice"] == "yes":
                    found_trello = found_linked_group_trello.get("trello")

                    if found_trello:
                        await delete_bind_from_cards(rank="main", trello_binds_list=trello_binds_list, bind_id=bind_id, bind_data_trello=found_linked_group_trello) #delete_bind_from_cards(rank, group, bind_data)

                    if found_linked_group:
                        del group_ids[bind_id]

                        guild_data["groupIDs"] = group_ids
                        await self.r.db("canary").table("guilds").insert(guild_data, conflict="replace").run() # so they can delete this and still
                                                                                                               # cancel bind deletion below

                        removed_main_group = True

            found_group_trello = role_binds_trello.get("groups", {}).get(bind_id) or {}
            found_group = role_binds.get("groups", {}).get(bind_id) or {}

            if found_group_trello:
                parsed_args = await CommandArgs.prompt([
                    {
                        "prompt": f"Please specify the ``rank ID`` (found on {prefix}viewbinds), or say ``everything`` "
                                  f"to delete all binds for group **{bind_id}**. If this is a _range_, then say the low and high value as: ``low-high``. If this is a guest role, say ``guest``.",
                        "name": "rank_id"
                    }
                ])

                rank_id = parsed_args["rank_id"].lower()

                if rank_id == "everything":
                    if found_group:
                        binds = found_group.get("binds", {})
                        del role_binds["groups"][bind_id]

                    await delete_bind_from_cards(rank="everything", trello_binds_list=trello_binds_list, bind_id=bind_id, bind_data_trello=found_group_trello)

                elif "-" in rank_id and not rank_id.lstrip("-").isdigit():
                    rank_id = rank_id.split("-")

                    if len(rank_id) == 2:
                        low, high = rank_id[0].strip(), rank_id[1].strip()

                        if not all(x.isdigit() for x in (high, low)):
                            raise Error("Ranges must have valid integers! An example would be ``1-100``.")

                        ranges = found_group_trello.get("ranges", [])

                        for range_ in ranges:
                            low_, high_ = range_["low"], range_["high"]

                            if int(low) == range_["low"] and int(high) == range_["high"]:
                                await delete_bind_from_cards(low=low_, high=high_, trello_binds_list=trello_binds_list, bind_id=bind_id, bind_data_trello=range_)
                                ranges.remove(range_)

                                break
                        else:
                            raise Message("There's no range found with this ID!", type="silly")

                else:
                    found_group_trello["binds"] = found_group_trello.get("binds") or {}

                    if rank_id in ("guest", "guest."):
                        if found_group_trello["binds"].get("guest"):
                            rank_id = "guest"
                        elif found_group_trello["binds"].get("0"):
                            rank_id = "0"

                    binds_trello = found_group_trello["binds"].get(rank_id)
                    binds = found_group.get("binds", {})

                    if binds_trello:
                        await delete_bind_from_cards(bind_id=bind_id, trello_binds_list=trello_binds_list, bind_data_trello=binds_trello, rank=rank_id)

                        if binds.get(rank_id):
                            del binds[rank_id]

                        if not (found_group.get("binds", {}) or found_group.get("ranges", {})):
                            del role_binds["groups"][bind_id]

                    else:
                        raise Error(f"No matching bind found for group ``{bind_id}`` with rank ``{rank_id}``!")

            else:
                if not removed_main_group:
                    raise Error(f"No matching bind found for group ``{bind_id}``!")

            guild_data["roleBinds"] = role_binds
            guild_data["groupIDs"] = group_ids

            await self.r.db("canary").table("guilds").insert(guild_data, conflict="replace").run()

            raise Message("All bind removals were successful.", type="success")

        else:
            if bind_category in ("assets", "asset"):
                bind_id = str((await CommandArgs.prompt([
                    {
                        "prompt": "Please specify the **Asset ID** to delete from.",
                        "name": "bind_id",
                        "type": "number"
                    },
                ]))["bind_id"])

                all_assets = role_binds_trello.get("assets", {})
                asset_binds = role_binds.get("assets")

                if not all_assets.get(bind_id):
                    raise Error("This asset is not bounded!")

                if asset_binds:
                    asset_binds.pop(bind_id, None)

                    if not asset_binds:
                        role_binds.pop("assets", None)

                    guild_data["roleBinds"] = role_binds

                    await self.r.db("canary").table("guilds").insert(guild_data, conflict="replace").run()

                found_asset_trello = role_binds_trello.get("assets", {}).get(bind_id) or {}

                if found_asset_trello:
                    await delete_bind_from_cards(type="asset", bind_id=bind_id, trello_binds_list=trello_binds_list, bind_data_trello=found_asset_trello)


                raise Message("All bind removals were successful.", type="success")


            else:
                raise Error("Unsupported bind type.")

