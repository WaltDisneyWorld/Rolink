from ..structures.Bloxlink import Bloxlink
import asyncio
import json



@Bloxlink.module
class Patreon(Bloxlink.Module):
    def __init__(self):
        self.patrons = {}

    async def __setup__(self):
        while True:
            await self.load_patrons()
            await asyncio.sleep(60 * 5)


    async def is_patron(self, author):
        #print(await self.redis.get("patrons"), flush=True)
        #return (await self.redis.get("patrons") or {}).get(author.id)
        return self.patrons.get(str(author.id))

    async def load_patrons(self):
        feed = await self.r.db("patreon").table("patrons").run()

        pledges = {}

        while await feed.fetch_next():
            patron = await feed.next()

            pledges[patron["id"]] = patron["payment"]

        self.patrons = pledges
