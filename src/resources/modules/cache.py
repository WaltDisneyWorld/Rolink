from discord.errors import NoMoreItems
from ..structures import Bloxlink, Blank # pylint: disable=import-error, no-name-in-module
from ..constants import CACHE_CLEAR # pylint: disable=import-error, no-name-in-module



@Bloxlink.module
class Cache(Bloxlink.Module):
    def __init__(self):
        self._cache = {}
        self.get_options = self.get_board = None

    async def __setup__(self):
        self.get_options, self.get_board = Bloxlink.get_module("trello", attrs=["get_options", "get_board"])

    async def get(self, k_name, k=None, primitives=False):
        if primitives and self.cache and k:
            return await self.cache.get(f"{k_name}:{k}")

        if k_name not in self._cache:
            self._cache[k_name] = {}

        if not k:
            return self._cache.get(k_name, {})
        else:
            return self._cache.get(k_name, {}).get(k)


    async def set(self, k_name, k, v, expire=CACHE_CLEAR*60, check_primitives=True):
        if check_primitives and self.cache and isinstance(v, (str, int, bool)):
            await self.cache.set(f"{k_name}:{k}", v, expire_time=expire)
        else:
            if k_name not in self._cache:
                self._cache[k_name] = {}

            self._cache[k_name][k] = v


    async def pop(self, k_name, k=None, primitives=False):
        if self.cache and primitives:
            if k:
                await self.cache.delete(f"{k_name}:{k}")
            else:
                await self.cache.delete_pattern(f"{k_name}*")
        else:
            if k:
                if k_name not in self._cache:
                    self._cache[k_name] = {}

                self._cache[k_name].pop(k, None)
            else:
                self._cache.pop(k_name, None)


    async def clear(self, *exceptions):
        if exceptions:
            cache = {}

            for exception in exceptions:
                cache_find = self._cache.get(exception)

                if cache_find:
                    cache[exception] = cache_find

            self._cache = cache
        else:
            self._cache = {}


    async def get_guild_value(self, guild, *items, return_guild_data=False):
        item_values = {}
        guild_data = await self.get("guild_data", guild.id)

        if guild_data is None:
            guild_data = await self.r.table("guilds").get(str(guild.id)).run() or {"id": str(guild.id)}

            trello_board = await self.get_board(guild=guild, guild_data=guild_data)
            trello_options = {}

            if trello_board:
                trello_options, _ = await self.get_options(trello_board)
                guild_data.update(trello_options)

            await self.set("guild_data", guild.id, guild_data, check_primitives=False)

        for item_name in items:
            item_default = None

            if isinstance(item_name, list):
                item_default = item_name[1]
                item_name = item_name[0]

            data = await self.get(f"guild_data:{guild.id}", item_name, primitives=False)

            if data is not None:
                if isinstance(data, Blank.Blank):
                    item_values[item_name] = None
                else:
                    item_values[item_name] = data

                continue

            item = guild_data.get(item_name, item_default)

            await self.set_guild_value(guild, item_name, item)

            item_values[item_name] = item

        if len(items) == 1:
            if return_guild_data:
                return item_values[item_name], guild_data
            else:
                return item_values[item_name]
        else:
            if return_guild_data:
                return item_values, guild_data
            else:
                return item_values


    async def set_guild_value(self, guild, item_name, value, guild_data=None):
        if value is None:
            value = Blank.Blank()

        await self.set(f"guild_data:{guild.id}", item_name, value, check_primitives=False)

        if guild_data:
            await self.set(f"guild_data", guild.id, guild_data, check_primitives=False)

    async def clear_guild_data(self, guild):
        await self.pop(f"guild_data:{guild.id}", primitives=False)
