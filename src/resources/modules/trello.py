from aiotrello import Trello as TrelloClient
from aiotrello.exceptions import TrelloBadRequest, TrelloUnauthorized, TrelloNotFound, TrelloBadRequest
from ..structures.Bloxlink import Bloxlink
from ..exceptions import BadUsage
from time import time
from os import environ as env
from resources.constants import OPTIONS
from re import compile
import asyncio

try:
    from config import TRELLO as TRELLO_CONFIG
except ImportError:
    TRELLO_CONFIG = {
        "KEY": env.get("TRELLO_KEY"),
        "TOKEN": env.get("TRELLO_TOKEN"),
	    "TRELLO_BOARD_CACHE_EXPIRATION": 5 * 60,
	    "CARD_LIMIT": 100,
        "LIST_LIMIT": 10
    }



OPTION_NAMES_MAP = {k.lower(): k for k in OPTIONS.keys()}


@Bloxlink.module
class Trello(Bloxlink.Module):
    def __init__(self):
        self.trello_boards = {}
        self.trello = TrelloClient(
            key=TRELLO_CONFIG.get("KEY"),
            token=TRELLO_CONFIG.get("TOKEN"),
            cache_mode="none",
            session=None) # self.session)
        self.option_regex = compile("(.+):(.+)")

    async def get_board(self, guild_data, guild):
        trello_board = None

        if guild_data and guild:
            trello_id = guild_data.get("trelloID")

            if trello_id:
                trello_board = self.trello_boards.get(guild.id)

                try:
                    trello_board = trello_board or await self.trello.get_board(trello_id, card_limit=TRELLO_CONFIG["CARD_LIMIT"], list_limit=TRELLO_CONFIG["LIST_LIMIT"])

                    if trello_board:
                        if not self.trello_boards.get(guild.id):
                            self.trello_boards[guild.id] = trello_board

                        t_now = time()

                        if hasattr(trello_board, "expiration"):
                            if t_now > trello_board.expiration:
                                await trello_board.sync(card_limit=TRELLO_CONFIG["CARD_LIMIT"], list_limit=TRELLO_CONFIG["LIST_LIMIT"])
                                trello_board.expiration = t_now + TRELLO_CONFIG["TRELLO_BOARD_CACHE_EXPIRATION"]

                        else:
                            trello_board.expiration = t_now + TRELLO_CONFIG["TRELLO_BOARD_CACHE_EXPIRATION"]

                except TrelloBadRequest:
                    pass
                except TrelloUnauthorized:
                    pass
                except (TrelloNotFound, TrelloBadRequest):
                    guild_data.pop("trelloID")

                    await self.r.db("canary").table("guilds").get(str(guild.id)).update(guild_data).run()


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

                    card_name_lower = card.name.lower()

                    if return_cards:
                        card_name_lower = card.name.lower()
                        options[OPTION_NAMES_MAP.get(card_name_lower, card_name_lower)] = (match_value, card)
                    else:
                        options[OPTION_NAMES_MAP.get(card_name_lower, card_name_lower)] = match_value

            return options, List

        return {}, None

    async def __setup__(self):
        while True:
            self.trello_boards = {}
            await asyncio.sleep(60 * 10)
