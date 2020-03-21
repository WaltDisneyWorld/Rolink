from resources.structures.Bloxlink import Bloxlink
from discord import Embed
from resources.exceptions import Error, Message
from resources.constants import ARROW
from aiotrello.exceptions import TrelloException
import asyncio

get_binds, get_group = Bloxlink.get_module("roblox", attrs=["get_binds", "get_group"])


async def delete_bind_from_cards(group, trello_binds_list=None, bind_data_trello=None, rank=None, high=None, low=None):
    cards = bind_data_trello.get("trello", {}).get("cards")

    if cards:
        if rank in ("main", "everything"):
            for card_data in cards:
                try:
                    await card_data["card"].archive()
                except TrelloException:
                    break
                else:
                    if trello_binds_list:
                        trello_binds_list.parsed_bind_data = None

        elif low and high:
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
                            f"Group: {group}",
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
                            if trello_binds_list:
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
                            f"Group: {group}",
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
                            if trello_binds_list:
                                trello_binds_list.parsed_bind_data = None



@Bloxlink.command
class DelBindCommand(Bloxlink.Module):
    """delete a role bind from your server"""

    def __init__(self):
        self.arguments = [{
            "prompt": "Please specify the group ID that this bind resides in. If this is not a group, " \
			          "specify the bind type (e.g. \"assetBind\").",
            "name": "bind_id"
        }]

        self.permissions = Bloxlink.Permissions().build("BLOXLINK_MANAGER")


    async def __main__(self, CommandArgs):
        guild_data = CommandArgs.guild_data
        trello_board = CommandArgs.trello_board
        prefix = CommandArgs.prefix

        role_binds = guild_data.get("roleBinds", {"groups": {}, "virtualGroups": {}})
        role_binds_trello, group_ids_trello, trello_binds_list = await get_binds(guild_data=guild_data, trello_board=trello_board)

        role_binds = guild_data.get("roleBinds", {"groups": {}, "virtualGroups": {}})
        group_ids = guild_data.get("groupIDs", {})

        if not ((role_binds_trello or {}).get("groups") or group_ids_trello):
            additional = (not trello_binds_list and "\nAdditionally, you may use "
                         f"``{prefix}setup`` to link a Trello board for bind-to-card creation.") or ""
            raise Message(f"You have no bounded roles! Please use ``{prefix}bind``"
                          f"to make a new role bind. {additional}", type="silly")

        bind_id = CommandArgs.parsed_args["bind_id"]

        role_binds_groups_trello = role_binds_trello["groups"]

        if bind_id.isdigit():
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
                        await delete_bind_from_cards(rank="main", trello_binds_list=trello_binds_list, group=bind_id, bind_data_trello=found_linked_group_trello) #delete_bind_from_cards(rank, group, bind_data)

                    if found_linked_group:
                        del group_ids[bind_id]

                        guild_data["groupIDs"] = group_ids
                        await self.r.table("guilds").insert(guild_data, conflict="replace").run() # so they can delete this and still
                                                                                                  # cancel bind deletion below

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

                if rank_id in ("everything", "everything."):
                    if found_group:
                        del role_binds[bind_id]

                    await delete_bind_from_cards(rank="everything", trello_binds_list=trello_binds_list, group=bind_id, bind_data_trello=found_group_trello)

                elif "-" in rank_id:
                    rank_id = rank_id.split("-")

                    if len(rank_id) == 2:
                        low, high = rank_id[0].strip(), rank_id[1].strip()

                        if not all(x.isdigit() for x in (high, low)):
                            raise Error("Ranges must have valid integers! An example would be ``1-100``.")

                        ranges = found_group_trello.get("ranges", [])

                        for range_ in ranges:
                            low_, high_ = range_["low"], range_["high"]

                            if int(low) == range_["low"] and int(high) == range_["high"]:
                                await delete_bind_from_cards(low=low_, high=high_, trello_binds_list=trello_binds_list, group=bind_id, bind_data_trello=range_)
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
                        await delete_bind_from_cards(group=bind_id, trello_binds_list=trello_binds_list, bind_data_trello=binds_trello, rank=rank_id)

                        if binds.get(rank_id):
                            del binds[rank_id]
                    else:
                        raise Error(f"No matching bind found for group ``{bind_id}`` with rank ``{rank_id}``!")

            guild_data["roleBinds"] = role_binds
            guild_data["groupIDs"] = group_ids

            await self.r.table("guilds").insert(guild_data, conflict="replace").run()

            raise Message("All bind removals were successful.", type="success")

        else:
            raise NotImplementedError # TODO: virtual groups
