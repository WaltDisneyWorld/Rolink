from resources.structures.Bloxlink import Bloxlink
from discord import Embed
from resources.exceptions import Message, RobloxNotFound
from resources.constants import ARROW
import asyncio

get_binds, get_group = Bloxlink.get_module("roblox", attrs=["get_binds", "get_group"])


@Bloxlink.command
class ViewBindsCommand(Bloxlink.Module):
    """view your server bound roles"""

    def __init__(self):
        pass

    async def __main__(self, CommandArgs):
        guild = CommandArgs.message.guild

        guild_data = CommandArgs.guild_data
        trello_board = CommandArgs.trello_board
        prefix = CommandArgs.prefix

        role_binds, group_ids, _ = await get_binds(guild_data=guild_data, trello_board=trello_board)

        if not ((role_binds or {}).get("groups") or group_ids):
            raise Message(f"You have no bounded roles! Please use ``{CommandArgs.prefix}bind``"
                           "to make a new role bind.", type="silly")


        embed = Embed(title="Bloxlink Role Binds")

        if group_ids:
            text = []

            for group_id, group_data in group_ids.items():
              text.append(f"**Group:** {group_data['groupName']} {ARROW} **Nickname:** {group_data['nickname']}")

            text = "\n".join(text)

            embed.add_field(name="Linked Groups", value=text, inline=False)

        if role_binds:
            role_cache = {}

            for group_id, group_data in role_binds["groups"].items():
                text = []

                for rank_id, rank_data in group_data.get("binds", {}).items():
                    role_names = set()

                    if rank_data["roles"]:
                        for role_ in rank_data["roles"]:
                            role_cache_find = role_cache.get(role_)

                            if role_cache_find:
                                role_names.add(role_cache_find)
                            else:
                                for role in guild.roles:
                                    if role_ in (role.name, str(role.id)):
                                        role_names.add(role.name)
                                        role_cache[role_] = role.name

                                        break
                                else:
                                    try:
                                        int(role_)
                                    except ValueError:
                                        role_names.add(role_)
                                        role_cache[role_] = role_
                                    else:
                                        # deleted role
                                        # TODO: check if the role is saved in server settings, then delete it
                                        role_names.add("(Deleted Role(s))")
                                        role_cache[role_] = "(Deleted Role(s))"

                        if rank_id in ("guest", "0"):
                            text.append(f"**Rank:** (Guest Role) {ARROW} **Roles:** {', '.join(role_names)} {ARROW} **Nickname:** {rank_data['nickname']}")
                        else:
                            text.append(f"**Rank:** {rank_id} {ARROW} **Roles:** {', '.join(role_names)} {ARROW} **Nickname:** {rank_data['nickname']}")
                    else:
                        text.append(f"**Rank:** {rank_id} {ARROW} **Roles:** (Dynamic Roles) {ARROW} **Nickname:** {rank_data['nickname']}")


                for range_data in group_data.get("ranges", []):
                    role_names = set()

                    if range_data["roles"]:
                        for role_ in range_data["roles"]:
                            role_cache_find = role_cache.get(role_)

                            if role_cache_find:
                                role_names.add(role_cache_find)
                            else:
                                for role in guild.roles:
                                    if role_ in (role.name, str(role.id)):
                                        role_names.add(role.name)
                                        role_cache[role_] = role.name

                                        break
                                else:
                                    try:
                                        int(role_)
                                    except ValueError:
                                        role_names.add(role_)
                                        role_cache[role_] = role_
                                    else:
                                        # deleted role
                                        # TODO: check if the role is saved in server settings, then delete it
                                        role_names.add("(Deleted Role(s))")
                                        role_cache[role_] = "(Deleted Role(s))"

                        text.append(f"**Rank Range:** {range_data['low']} - {range_data['high']} {ARROW} **Roles:** {', '.join(role_names)} {ARROW} **Nickname:** {range_data['nickname']}")
                    else:
                        text.append(f"**Rank Range:** {range_data['low']} - {range_data['high']} {ARROW} **Roles:** (Dynamic Roles) {ARROW} **Nickname:** {range_data['nickname']}")

                if text:
                    text = "\n".join(text)

                    try:
                        group_name = group_data.get("groupName") or (await get_group(group_id)).name
                    except RobloxNotFound:
                        group_name = f"Invalid Group: {group_id}"

                    embed.add_field(name=f"{group_name} ({group_id})", value=text, inline=False)


        embed.set_author(name="Powered by Bloxlink", icon_url=Bloxlink.user.avatar_url)
        embed.set_footer(text=f"Use {prefix}bind to make a new bind, or {prefix}delbind to delete a bind")

        await CommandArgs.response.send(embed=embed)
