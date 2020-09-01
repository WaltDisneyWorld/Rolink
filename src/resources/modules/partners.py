from ..structures import Bloxlink
from aiotrello.exceptions import TrelloNotFound, TrelloUnauthorized
from aiohttp.client_exceptions import ClientOSError, ServerDisconnectedError
import re


trello = Bloxlink.get_module("trello", attrs="trello")
cache_set, cache_get, cache_pop = Bloxlink.get_module("cache", attrs=["set", "get", "pop"])


@Bloxlink.module
class Partners(Bloxlink.Module):
    def __init__(self):
        self.option_regex = re.compile("(.+):(.+)")

        self.trello_board = None

    async def __setup__(self):
        await self.load_data()

    async def parse_data(self, trello_list, directory):
        for card in await trello_list.get_cards():
            match = self.option_regex.search(card.name)

            if match:
                group_name = match.group(1)
                group_id = match.group(2)
                await cache_set("partners", card.desc.isdigit() and int(card.desc) or group_id, (directory, group_id, group_name, card.desc.isdigit() and int(card.desc)))


    async def load_data(self):
        try:
            self.trello_board = await trello.get_board("https://trello.com/b/o9PkeQYF/partners-and-notable-groups")
        except (TrelloNotFound, TrelloUnauthorized, ConnectionResetError, ClientOSError, ServerDisconnectedError):
            pass
        else:
            await cache_pop("partners")
            partners_list = await self.trello_board.get_list(lambda l: l.name == "Partners")
            notable_groups_list = await self.trello_board.get_list(lambda l: l.name == "Notable Groups")

            await self.parse_data(partners_list, "partner")
            await self.parse_data(notable_groups_list, "notable_group")
