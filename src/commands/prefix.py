from resources.structures.Bloxlink import Bloxlink # pylint: disable=import-error
from resources.exceptions import PermissionError # pylint: disable=import-error
from config import TRELLO # pylint: disable=no-name-in-module
from aiotrello.exceptions import TrelloUnauthorized, TrelloNotFound, TrelloBadRequest

get_prefix = Bloxlink.get_module("utils", attrs=["get_prefix"])

@Bloxlink.command
class PrefixCommand(Bloxlink.Module):
    """change your prefix, or view your prefix"""

    def __init__(self):
        self.arguments = [
            {
                "prompt": "Please specify a new prefix.",
                "name": "new_prefix",
                "max": 10,
                "optional": True
            }
        ]
        self.examples = ["?"]

        permission = Bloxlink.Permissions().build("BLOXLINK_MANAGER")
        permission.allow_bypass = True

        self.permissions = permission
        self.category = "Administration"

    async def __main__(self, CommandArgs):
        locale = CommandArgs.locale
        response = CommandArgs.response

        guild = CommandArgs.message.guild
        guild_data = CommandArgs.guild_data

        new_prefix = CommandArgs.parsed_args.get("new_prefix")

        if new_prefix:
            if not CommandArgs.has_permission:
                raise PermissionError("You do not meet the required permissions for this command.")

            await self.r.table("guilds").insert({
                "id": str(guild.id),
                "prefix": new_prefix
            }, conflict="update").run()

            trello_board = CommandArgs.trello_board

            if trello_board:
                _, card = await get_prefix(guild=guild, guild_data=guild_data, trello_board=trello_board)

                if card:
                    try:
                        if card.name == "prefix":
                            await card.edit(desc=new_prefix)
                        else:
                            await card.edit(name=f"prefix:{new_prefix}")
                    except TrelloUnauthorized:
                        await response.error("In order for me to edit your Trello settings, please add ``@bloxlink`` to your "
                                             "Trello board.")
                    except (TrelloNotFound, TrelloBadRequest):
                        pass
                    else:
                        await trello_board.sync(card_limit=TRELLO["GLOBAL_CARD_LIMIT"])


            await response.success("Your prefix was successfully changed!")

        else:
            old_prefix = CommandArgs.prefix

            await response.send(f"Your prefix used for Bloxlink: ``{old_prefix}``.\n"
                                 "Change it with ``@Bloxlink prefix <new prefix>``.")
