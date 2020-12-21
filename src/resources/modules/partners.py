from ..structures import Bloxlink # pylint: disable=import-error
from config import BLOXLINK_GUILD # pylint: disable=import-error, no-name-in-module
from ..constants import RELEASE # pylint: disable=import-error
from discord.utils import find
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

    async def is_partner(self, author):
        return await cache_get(f"partners:users:{author.id}", primitives=True)

    async def parse_data(self, trello_list, directory):
        for card in await trello_list.get_cards():
            match = self.option_regex.search(card.name)

            if match:
                group_name = match.group(1)
                group_id = match.group(2)
                await cache_set(f"partners:guilds:{card.desc.isdigit() and int(card.desc) or group_id}", (directory, group_id, group_name, card.desc.isdigit() and int(card.desc)))


    async def load_data(self):
        try:
            self.trello_board = await trello.get_board("https://trello.com/b/o9PkeQYF/partners-and-notable-groups")
        except Exception:
            pass
        else:
            await cache_pop("partners")
            partners_list = await self.trello_board.get_list(lambda l: l.name == "Partners")
            notable_groups_list = await self.trello_board.get_list(lambda l: l.name == "Notable Groups")

            await self.parse_data(partners_list, "partner")
            await self.parse_data(notable_groups_list, "notable_group")


        if RELEASE in ("CANARY", "LOCAL"):
            await Bloxlink.wait_until_ready()

            guild = Bloxlink.get_guild(BLOXLINK_GUILD)

            if not guild:
                guild = await Bloxlink.fetch_guild(BLOXLINK_GUILD)

            if guild.unavailable:
                return

            try:
                await guild.chunk()
            except KeyError: # FIXME: temporarily fix discord.py bug
                pass

            partners_role = find(lambda r: r.name == "Partners", guild.roles)

            if partners_role:
                for member in partners_role.members:
                    await cache_set(f"partners:users:{member.id}", "true")
