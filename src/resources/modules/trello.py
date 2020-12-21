from aiotrello import Trello as TrelloClient
from aiotrello.exceptions import TrelloUnauthorized, TrelloNotFound
from ..structures.Bloxlink import Bloxlink # pylint: disable=import-error
from ..constants import OPTIONS # pylint: disable=import-error
from ..constants import TRELLO as TRELLO_ # pylint: disable=import-error
from ..secrets import TRELLO_KEY, TRELLO_TOKEN # pylint: disable=import-error
from time import time
from re import compile
import asyncio


OPTION_NAMES_MAP = {k.lower(): k for k in OPTIONS.keys()}

cache_get, cache_set, get_guild_value = Bloxlink.get_module("cache", attrs=["get", "set", "get_guild_value"])

@Bloxlink.module
class Trello(Bloxlink.Module):
    def __init__(self):
        self.trello_boards = {}

        self.trello = TrelloClient(
            key=TRELLO_KEY,
            token=TRELLO_TOKEN,
            cache_mode="none")
        self.option_regex = compile("(.+):(.+)")


    async def get_board(self, guild, guild_data=None):
        trello_board = None

        if guild_data:
            trello_id = guild_data.get("trelloID")
        else:
            trello_id = await get_guild_value(guild, "trelloID")

        if trello_id:
            trello_board = await cache_get(f"trello_boards:{guild.id}")

            try:
                if not trello_board:
                    trello_board = await self.trello.get_board(trello_id, card_limit=TRELLO_["CARD_LIMIT"], list_limit=TRELLO_["LIST_LIMIT"])
                    await cache_set(f"trello_boards:{guild.id}", trello_board)

                if trello_board:
                    t_now = time()

                    if hasattr(trello_board, "expiration"):
                        if t_now > trello_board.expiration:
                            await trello_board.sync(card_limit=TRELLO_["CARD_LIMIT"], list_limit=TRELLO_["LIST_LIMIT"])
                            trello_board.expiration = t_now + TRELLO_["TRELLO_BOARD_CACHE_EXPIRATION"]

                    else:
                        trello_board.expiration = t_now + TRELLO_["TRELLO_BOARD_CACHE_EXPIRATION"]

            except (TrelloUnauthorized, ConnectionResetError):
                pass

            except TrelloNotFound:
                guild_data = await self.r.db("bloxlink").table("guilds").get(str(guild.id)).run() or {}
                guild_data.pop("trelloID")

                await self.r.table("guilds").get(str(guild.id)).update(guild_data).run()

            except asyncio.TimeoutError:
                pass


        return trello_board

    async def get_options(self, trello_board, return_cards=False):
        List = await trello_board.get_list(lambda l: l.name == "Bloxlink Settings")

        if List:
            options = {}

            for card in await List.get_cards():
                match = self.option_regex.search(card.name)

                if match:
                    match_value = match.group(2)
                    match_value_lower = match_value.lower()
                    card_name = match.group(1)
                    card_name_lower = card_name.lower()

                    if match_value_lower in ("true", "enabled"):
                        match_value = True
                    elif match_value_lower in ("false", "disabled"):
                        match_value = False
                    elif match_value_lower == "none":
                        match_value = None

                    if return_cards:
                        options[OPTION_NAMES_MAP.get(card_name_lower, card_name_lower)] = (match_value, card)
                    else:
                        options[OPTION_NAMES_MAP.get(card_name_lower, card_name_lower)] = match_value
                else:
                    match_value = card.desc
                    match_value_lower = match_value.lower()

                    if match_value_lower in ("true", "enabled"):
                        match_value = True
                    elif match_value_lower in ("false", "disabled"):
                        match_value = False
                    elif match_value_lower == "none":
                        match_value = None

                    card_name_lower = card.name.lower()

                    if return_cards:
                        card_name_lower = card.name.lower()
                        options[OPTION_NAMES_MAP.get(card_name_lower, card_name_lower)] = (match_value, card)
                    else:
                        options[OPTION_NAMES_MAP.get(card_name_lower, card_name_lower)] = match_value

            return options, List

        return {}, None
