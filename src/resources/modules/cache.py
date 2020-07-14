from ..structures import Bloxlink


# TODO: check if value is a string (or number?), then use redis for it


@Bloxlink.module
class Cache(Bloxlink.Module):
    def __init__(self):
        self.cache = {}
        self.empty_cache = {}


    def get(self, k_name, k):
        if k_name not in self.cache:
            self.empty_cache[k_name] = {}
            self.cache[k_name] = {}

        return self.cache.get(k_name, {}).get(k)


    def set(self, k_name, k, v):
        if k_name not in self.cache:
            self.empty_cache[k_name] = {}
            self.cache[k_name] = {}

        self.cache[k_name][k] = v


    def pop(self, k_name, k):
        if k_name not in self.cache:
            self.empty_cache[k_name] = {}
            self.cache[k_name] = {}

        self.cache[k_name].pop(k, None)


    async def clear(self):
        self.cache = dict(self.empty_cache)
