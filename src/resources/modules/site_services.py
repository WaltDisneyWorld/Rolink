from ..structures.Bloxlink import Bloxlink # pylint: disable=import-error
from ..constants import TOPGG_API, DBL_API, RELEASE, SHARD_RANGE, SHARD_COUNT # pylint: disable=import-error
from ..secrets import TOPGG_KEY, DBL_KEY # pylint: disable=import-error
import aiohttp



fetch = Bloxlink.get_module("utils", attrs="fetch")


@Bloxlink.module
class DBL(Bloxlink.Module):
    def __init__(self):
        pass

    async def post_topgg(self):
        url = f"{TOPGG_API}/bots/{Bloxlink.user.id}/stats"
        headers = {"Authorization": TOPGG_KEY}
        first = True

        for shard_id in SHARD_RANGE:
            payload = {
                "server_count": first and len(Bloxlink.guilds) or 0,
                "shard_count": SHARD_COUNT,
                "shard_id": shard_id
            }

            first = False

            async with aiohttp.ClientSession() as session:
                try:
                    await session.post(url, data=payload, headers=headers)
                except Exception:
                    Bloxlink.log("Failed to post TOP.GG stats")

    async def post_dbl(self):
        url = f"{DBL_API}/bots/{Bloxlink.user.id}/stats"
        headers = {"Authorization": DBL_KEY}
        first = True

        for shard_id in SHARD_RANGE:
            payload = {
                "guilds": first and len(Bloxlink.guilds) or 0,
                "shard_id": shard_id
            }

            first = False

            async with aiohttp.ClientSession() as session:
                try:
                    await session.post(url, data=payload, headers=headers)
                except Exception:
                    Bloxlink.log("Failed to post DBL stats")


    async def post_stats(self):
        if RELEASE == "MAIN":
            await self.post_topgg()
            await self.post_dbl()
