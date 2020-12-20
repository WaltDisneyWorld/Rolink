from ..structures.Bloxlink import Bloxlink
from ..exceptions import UserNotVerified
from ..constants import DEFAULTS, RED_COLOR
from discord.errors import NotFound, Forbidden
from discord import Object

cache_get, cache_set = Bloxlink.get_module("cache", attrs=["get", "set"])
get_features = Bloxlink.get_module("premium", attrs=["get_features"])
get_user = Bloxlink.get_module("roblox", attrs=["get_user"])
get_board, get_options = Bloxlink.get_module("trello", attrs=["get_board", "get_options"])
post_event = Bloxlink.get_module("utils", attrs=["post_event"])

@Bloxlink.module
class MemberBanEvent(Bloxlink.Module):
    def __init__(self):
        pass

    async def __setup__(self):

        @Bloxlink.event
        async def on_member_ban(guild, user):
            if self.redis:
                donator_profile, _ = await get_features(Object(id=guild.owner_id), guild=guild)

                guild_data = await cache_get("guild_data", guild.id)

                if not guild_data:
                    guild_data = await self.r.table("guilds").get(str(guild.id)).run() or {"id": str(guild.id)}

                    trello_board = await get_board(guild=guild, guild_data=guild_data)
                    trello_options = {}

                    if trello_board:
                        trello_options, _ = await get_options(trello_board)
                        guild_data.update(trello_options)

                if donator_profile.features.get("premium"):
                    if await cache_get("banRelatedAccounts", guild.id, primitives=True) is None:
                        await cache_set("guild_data", guild.id, guild_data)
                        await cache_set("banRelatedAccounts", guild.id, bool(guild_data.get("banRelatedAccounts", DEFAULTS.get("banRelatedAccounts"))))

                    if await cache_get("banRelatedAccounts", guild.id, primitives=True):
                        try:
                            account, accounts = await get_user(author=user, guild=guild)
                        except UserNotVerified:
                            pass
                        else:
                            accounts = set(accounts)

                            if account: #FIXME: temp until primary accounts are saved to the accounts array
                                accounts.add(account.id)

                            for roblox_id in accounts:
                                discord_ids = (await self.r.db("bloxlink").table("robloxAccounts").get(roblox_id).run() or {}).get("discordIDs") or []

                                for discord_id in discord_ids:
                                    discord_id = int(discord_id)

                                    if discord_id != user.id:
                                        try:
                                            user_find = await guild.fetch_member(discord_id)
                                        except NotFound:
                                            pass
                                        else:
                                            try:
                                                await user_find.ban(reason=f"banRelatedAccounts is enabled - alt of {user} ({user.id})")
                                            except Forbidden:
                                                pass
                                            else:
                                                await post_event(guild, guild_data, "moderation", f"{user_find.mention} is an alt of {user.mention} and has been ``banned``.", RED_COLOR)
