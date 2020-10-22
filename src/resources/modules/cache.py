from ..structures import Bloxlink
from ..constants import CACHE_CLEAR


@Bloxlink.module
class Cache(Bloxlink.Module):
    def __init__(self):
        self._cache = {}


    async def get(self, k_name, k=None, primitives=False):
        if primitives and self.cache and k:
            return await self.cache.get(f"{k_name}:{k}")

        if k_name not in self._cache:
            self._cache[k_name] = {}

        if not k:
            return self._cache.get(k_name, {})
        else:
            return self._cache.get(k_name, {}).get(k)


    async def set(self, k_name, k, v, expire=CACHE_CLEAR*60):
        if self.cache and isinstance(v, (str, int, bool)):
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

