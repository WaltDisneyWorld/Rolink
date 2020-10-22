from ..structures.Bloxlink import Bloxlink # pylint: disable=import-error
from ..constants import RELEASE # pylint: disable=import-error
from config import BLOXLINK_GUILD # pylint: disable=import-error, no-name-in-module
from discord.utils import find

cache_set, cache_get = Bloxlink.get_module("cache", attrs=["set", "get"])


@Bloxlink.module
class NitroBoosters(Bloxlink.Module):
    def __init__(self):
        pass

    async def is_booster(self, author):
        return await cache_get("nitro_boosters", author.id, primitives=True)

    async def load_boosters(self):
        if RELEASE == "CANARY":
            await Bloxlink.wait_until_ready()

            guild = Bloxlink.get_guild(BLOXLINK_GUILD)

            if not guild:
                guild = await Bloxlink.fetch_guild(BLOXLINK_GUILD)

            if guild.unavailable:
                return

            await guild.chunk()

            booster_role = find(lambda r: r.name == "Nitro Booster", guild.roles)

            if booster_role:
                for member in booster_role.members:
                    await cache_set("nitro_boosters", member.id, "true")
