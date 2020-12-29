from os import listdir
from re import compile
from ..structures import Bloxlink # pylint: disable=import-error, no-name-in-module
from ..exceptions import RobloxAPIError, RobloxDown, RobloxNotFound, CancelCommand # pylint: disable=import-error, no-name-in-module
from config import PREFIX # pylint: disable=import-error, no-name-in-module
from ..constants import RELEASE, HTTP_RETRY_LIMIT # pylint: disable=import-error, no-name-in-module
from discord.errors import NotFound, Forbidden
from discord import Embed
from aiohttp.client_exceptions import ClientOSError, ServerDisconnectedError
import asyncio
import aiohttp

is_patron = Bloxlink.get_module("patreon", attrs="is_patron")
cache_pop, get_guild_value = Bloxlink.get_module("cache", attrs=["pop", "get_guild_value"])

@Bloxlink.module
class Utils(Bloxlink.Module):
    def __init__(self):
        self.option_regex = compile("(.+):(.+)")
        self.timeout = aiohttp.ClientTimeout(total=20)


    @staticmethod
    def get_files(directory):
        return [name for name in listdir(directory) if name[:1] != "." and name[:2] != "__" and name != "_DS_Store"]


    @staticmethod
    def coro_async(corofn, *args):
        # https://stackoverflow.com/questions/46074841/why-coroutines-cannot-be-used-with-run-in-executor
        loop = asyncio.new_event_loop()

        try:
            coro = corofn(*args)
            asyncio.set_event_loop(loop)

            return loop.run_until_complete(coro)

        finally:
            loop.close()


    async def post_event(self, guild, guild_data, event_name, text, color=None):
        if guild_data:
            log_channels = guild_data.get("logChannels")
        else:
            log_channels = await get_guild_value(guild, "logChannels")

        log_channels = log_channels or {}
        log_channel  = log_channels.get(event_name) or log_channels.get("all")

        if log_channel:
            text_channel = guild.get_channel(int(log_channel))

            if text_channel:
                embed = Embed(title=f"{event_name.title()} Event", description=text)
                embed.colour = color

                try:
                    await text_channel.send(embed=embed)
                except (Forbidden, NotFound):
                    pass


    async def fetch(self, url, method="GET", params=None, headers=None, raise_on_failure=True, retry=HTTP_RETRY_LIMIT):
        params = params or {}
        headers = headers or {}

        if RELEASE == "LOCAL":
            Bloxlink.log(f"Making HTTP request: {url}")

        for k, v in params.items():
            if isinstance(v, bool):
                params[k] = "true" if v else "false"

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.request(method, url, params=params, headers=headers) as response:
                    text = await response.text()

                    if text == "The service is unavailable." or response.status == 503:
                        raise RobloxDown

                    if raise_on_failure:
                        if response.status >= 500:
                            if retry != 0:
                                retry -= 1
                                await asyncio.sleep(1.0)

                                return await self.fetch(url, raise_on_failure=raise_on_failure, retry=retry)

                            raise RobloxAPIError

                        elif response.status == 400:
                            raise RobloxAPIError
                        elif response.status == 404:
                            raise RobloxNotFound

                    return text, response

        except ServerDisconnectedError:
            if retry != 0:
                return await self.fetch(url, raise_on_failure=raise_on_failure, retry=retry-1)
            else:
                raise ServerDisconnectedError

        except ClientOSError:
            # TODO: raise HttpError with non-roblox URLs
            raise RobloxAPIError

        except asyncio.TimeoutError:
            raise CancelCommand


    async def get_prefix(self, guild=None, trello_board=None):
        if RELEASE == "PRO" and guild:
            prefix = await get_guild_value(guild, "proPrefix")

            if prefix:
                return prefix, None

        if trello_board:
            try:
                List = await trello_board.get_list(lambda L: L.name == "Bloxlink Settings")

                if List:
                    card = await List.get_card(lambda c: c.name[:6] == "prefix")

                    if card:
                        if card.name == "prefix":
                            if card.desc:
                                return card.desc.strip(), card

                        else:
                            match = self.option_regex.search(card.name)

                            if match:
                                return match.group(2), card

            except asyncio.TimeoutError:
                pass

        prefix = guild and await get_guild_value(guild, ["prefix", PREFIX])

        return prefix or PREFIX, None
