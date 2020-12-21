from ..structures.Bloxlink import Bloxlink # pylint: disable=import-error
from ..exceptions import UserNotVerified # pylint: disable=import-error
from ..constants import DEFAULTS, RED_COLOR # pylint: disable=import-error
from discord.errors import NotFound, Forbidden
from discord import Object

get_guild_value = Bloxlink.get_module("cache", attrs=["get_guild_value"])
get_features = Bloxlink.get_module("premium", attrs=["get_features"])
get_user = Bloxlink.get_module("roblox", attrs=["get_user"])
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

                ban_related_accounts = await get_guild_value(guild, ["banRelatedAccounts", DEFAULTS.get("banRelatedAccounts")])

                if donator_profile.features.get("premium"):
                    if ban_related_accounts:
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
                                                await post_event(guild, None, "moderation", f"{user_find.mention} is an alt of {user.mention} and has been ``banned``.", RED_COLOR)
