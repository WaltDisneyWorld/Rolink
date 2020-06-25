from discord import Embed
from resources.structures.Bloxlink import Bloxlink # pylint: disable=import-error
from resources.exceptions import Message, UserNotVerified, BloxlinkBypass # pylint: disable=import-error
from resources.constants import DEFAULTS
from os import environ as env

update_member, count_binds, get_binds = Bloxlink.get_module("roblox", attrs=["update_member", "count_binds", "get_binds"])
parse_message = Bloxlink.get_module("commands", attrs="parse_message")
get_options = Bloxlink.get_module("trello", attrs=["get_options"])

try:
    from config import TRELLO
except ImportError:
    TRELLO = {
        "KEY": env.get("TRELLO_KEY"),
        "TOKEN": env.get("TRELLO_TOKEN"),
	    "TRELLO_BOARD_CACHE_EXPIRATION": 5 * 60,
	    "GLOBAL_CARD_LIMIT": 100
    }


@Bloxlink.command
class GetRoleCommand(Bloxlink.Module):
    """retrieve your bound roles"""

    def __init__(self):
        self.aliases = ["getroles", "give me roles please"]


    @Bloxlink.flags
    async def __main__(self, CommandArgs):
        author = CommandArgs.message.author
        guild_data = CommandArgs.guild_data
        trello_board = CommandArgs.trello_board
        prefix = CommandArgs.prefix

        if trello_board:
            trello_options, _ = await get_options(trello_board)
            guild_data.update(trello_options)

        role_binds, group_ids, trello_binds_list = await get_binds(guild_data=guild_data, trello_board=trello_board)

        group_required = guild_data.get("groupRequired", DEFAULTS.get("groupRequired"))

        if group_required and count_binds(guild_data, role_binds=role_binds, group_ids=group_ids) == 0:
            raise Message(f"This server has no bind configuration! Please run ``{prefix}bind`` to make a new bind. If "
                          f"binds aren't needed, then this message may be disabled by using ``{prefix}settings`` and "
                           "disabling ``groupRequired``.",
                            type="silly")

        async with CommandArgs.response.loading():
            try:
                added, removed, nickname, errors, roblox_user = await update_member(
                    CommandArgs.message.author,
                    guild                = CommandArgs.message.guild,
                    guild_data           = CommandArgs.guild_data,
                    trello_board         = trello_board,
                    trello_binds_list    = trello_binds_list,
                    roles                = True,
                    nickname             = True,
                    author_data          = await self.r.table("users").get(str(author.id)).run(),
                    given_trello_options = True)

                embed = Embed(title=f"Discord Profile for {roblox_user.username}", description="Changed someone’s group rank? Please wait 10 minutes for Bloxlink to catch up!")
                embed.set_author(name=str(author), icon_url=author.avatar_url, url=roblox_user.profile_link)

                if not (added or removed):
                    raise Message("All caught up! There are no roles to add or remove.", type="success")

                if added:
                    embed.add_field(name="Added Roles", value=", ".join(added))
                if removed:
                    embed.add_field(name="Removed Roles", value=", ".join(removed))
                if nickname:
                    embed.description = f"**Nickname:** ``{nickname}``\nChanged someone’s group rank? Please wait 10 minutes for Bloxlink to catch up!"
                if errors:
                    embed.add_field(name="Errors", value=", ".join(errors))

                embed.set_footer(text="Powered by Bloxlink", icon_url=Bloxlink.user.avatar_url)

                await CommandArgs.response.send(embed=embed)

            except BloxlinkBypass:
                raise Message("Since you have the ``Bloxlink Bypass`` role, I was unable to update your roles/nickname.", type="info")

            except UserNotVerified:
                message = CommandArgs.message
                message.content = f"{CommandArgs.prefix}verify"

                await parse_message(message)
