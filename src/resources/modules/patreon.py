from ..structures.Bloxlink import Bloxlink
import asyncio



@Bloxlink.module
class Patreon(Bloxlink.Module):
    def __init__(self):
        self.patrons = {}

    async def __setup__(self):
        while True:
            await self.load_patrons()
            await asyncio.sleep(60 * 5)


    async def is_patron(self, author):
        return self.patrons.get(author.id)

    async def load_patrons(self):
        feed = await self.r.db("patreon").table("patrons").run()

        pledges = {}

        while await feed.fetch_next():
            patron = await feed.next()

            if patron["discord_id"] and patron["active"]:
                pledges[int(patron["discord_id"])] = patron

        if pledges:
            self.patrons = pledges
