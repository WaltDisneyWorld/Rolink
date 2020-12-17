from ..structures import Bloxlink, DonatorProfile # pylint: disable=import-error
from ..constants import TRANSFER_COOLDOWN, RELEASE # pylint: disable=import-error
from ..exceptions import Message # pylint: disable=import-error
from config import BLOXLINK_GUILD # pylint: disable=import-error, no-name-in-module
from discord import Object
from discord.utils import find
from time import time
from math import ceil

is_patron = Bloxlink.get_module("patreon", attrs="is_patron")
cache_set, cache_get, cache_pop = Bloxlink.get_module("cache", attrs=["set", "get", "pop"])

@Bloxlink.module
class Premium(Bloxlink.Module):
    def __init__(self):
        pass

    async def load_staff_members(self):
        if RELEASE == "CANARY":
            await Bloxlink.wait_until_ready()

            guild = Bloxlink.get_guild(BLOXLINK_GUILD)

            if not guild:
                guild = await Bloxlink.fetch_guild(BLOXLINK_GUILD)

            if guild.unavailable:
                return

            try:
                await guild.chunk()
            except KeyError: # FIXME: temporarily fix discord.py bug
                pass

            staff_role = find(lambda r: r.name == "Helpers", guild.roles)

            if staff_role:
                for member in staff_role.members:
                    await cache_set("bloxlink_staff", member.id, "true")


    async def is_staff(self, author):
        return await cache_get("bloxlink_staff", author.id, primitives=True)

    async def add_features(self, user, features, *, days=-1, code=None, premium_anywhere=None, guild=None,):
        user_data = await self.r.db("bloxlink").table("users").get(str(user.id)).run() or {"id": str(user.id)}
        user_data_premium = user_data.get("premium") or {}
        prem_expiry = user_data_premium.get("expiry", 1)

        if days != -1 and days != 0:
            t = time()

            if prem_expiry and prem_expiry > t:
                # premium is still active; add time to it
                days = (days * 86400) + prem_expiry
            else:
                # premium expired
                days = (days * 86400) + t
        elif days == -1:
            days = prem_expiry
        elif days == "-":
            days = 1

        if code:
            # delete_code()
            # add code to redeemed
            pass

        if "pro" in features:
            user_data_premium["pro"] = days # TODO: convert to -1

        if "premium" in features:
            user_data_premium["expiry"] = days # TODO: convert to -1

        """
        if premium_anywhere:
            user_data["flags"] = user_data.get("flags") or {}
            user_data["flags"]["premiumAnywhere"] = True
        """

        if "-" in features:
            if "premium" in features:
                user_data_premium["expiry"] = 1

            if "pro" in features:
                user_data_premium["pro"] = 1

            if len(features) == 1:
                user_data_premium["expiry"] = 1
                user_data_premium["pro"] = 1

        user_data["premium"] = user_data_premium

        await self.r.db("bloxlink").table("users").insert(user_data, conflict="update").run()

        await cache_pop("premium_cache", user.id)

        if guild:
            await cache_pop("premium_cache", guild.id)


    async def has_selly_premium(self, author, author_data):
        premium = author_data.get("premium") or {}
        expiry = premium.get("expiry", 1)
        pro_expiry = premium.get("pro", 1)

        t = time()
        is_p = expiry == 0 or expiry > t
        days_premium = expiry != 0 and expiry > t and ceil((expiry - t)/86400) or 0

        pro_access = pro_expiry == 0 or pro_expiry > t
        pro_days = pro_expiry != 0 and pro_expiry > t and ceil((pro_expiry - t)/86400) or 0

        return {
            "premium": is_p,
            "days": days_premium,
            "pro_access": pro_access,
            "pro_days": pro_days,
            "codes_redeemed": premium.get("redeemed", {})
        }


    async def has_patreon_premium(self, author, author_data):
        patron_data = await is_patron(author)

        return patron_data


    async def transfer_premium(self, transfer_from, transfer_to, guild=None, apply_cooldown=True):
        profile, _ = await self.get_features(transfer_to, cache=False, partner_check=False)

        if profile.features.get("premium"):
            raise Message("This user already has premium!", type="silly")

        if transfer_from == transfer_to:
            raise Message("You cannot transfer premium to yourself!")


        transfer_from_data = await self.r.db("bloxlink").table("users").get(str(transfer_from.id)).run() or {"id": str(transfer_from.id)}
        transfer_to_data   = await self.r.db("bloxlink").table("users").get(str(transfer_to.id)).run() or {"id": str(transfer_to.id)}

        transfer_from_data["premium"] = transfer_from_data.get("premium", {})
        transfer_to_data["premium"]   = transfer_to_data.get("premium", {})

        transfer_from_data["premium"]["transferTo"] = str(transfer_to.id)
        transfer_to_data["premium"]["transferFrom"] = str(transfer_from.id)

        if apply_cooldown:
            transfer_from_data["premium"]["transferCooldown"] = time() + (86400*TRANSFER_COOLDOWN)

        await self.r.db("bloxlink").table("users").insert(transfer_from_data, conflict="update").run()
        await self.r.db("bloxlink").table("users").insert(transfer_to_data,   conflict="update").run()

        await cache_pop("premium_cache", transfer_to.id)
        await cache_pop("premium_cache", transfer_from.id)

        if guild:
            await cache_pop("premium_cache", guild.id)


    async def get_features(self, author=None, guild=None, author_data=None, cache=True, cache_as_guild=True, rec=True, partner_check=True):
        author = author or guild.owner
        profile = DonatorProfile(author)

        if cache:
            if guild and cache_as_guild:
                guild_premium_cache = await cache_get("premium_cache", guild.id)

                if guild_premium_cache:
                    return guild_premium_cache[0], guild_premium_cache[1]
            else:
                premium_cache = await cache_get("premium_cache", author.id)

                if premium_cache:
                    return premium_cache[0], premium_cache[1]

        author_data = author_data or await self.r.db("bloxlink").table("users").get(str(author.id)).run() or {"id": str(author.id)}
        premium_data = author_data.get("premium") or {}

        if rec:
            if premium_data.get("transferTo"):
                if cache:
                    if guild and cache_as_guild:
                        await cache_set("premium_cache", guild.id, (profile, premium_data["transferTo"]))
                    else:
                        await cache_set("premium_cache", author.id, (profile, premium_data["transferTo"]))

                return profile, premium_data["transferTo"]

            elif premium_data.get("transferFrom"):
                transfer_from = premium_data["transferFrom"]
                transferee_data = await self.r.db("bloxlink").table("users").get(str(transfer_from)).run() or {}
                transferee_premium, _ = await self.get_features(Object(id=transfer_from), author_data=transferee_data, rec=False, cache=False, partner_check=False)

                if transferee_premium.features.get("premium"):
                    if cache:
                        if guild and cache_as_guild:
                            await cache_set("premium_cache", guild.id, (transferee_premium, _))
                        else:
                            await cache_set("premium_cache", author.id, (transferee_premium, _))

                    return transferee_premium, _
                else:
                    premium_data["transferFrom"] = None
                    premium_data["transferTo"] = None
                    premium_data["transferCooldown"] = None
                    transferee_data["transferTo"] = None
                    transferee_data["transferFrom"] = None
                    transferee_data["transferCooldown"] = None

                    author_data["premium"] = premium_data
                    transferee_data["premium"] = transferee_data

                    await self.r.db("bloxlink").table("users").insert(author_data, conflict="update").run()
                    await self.r.db("bloxlink").table("users").insert(transferee_data, conflict="update").run()

        """
        if author_data.get("flags", {}).get("premiumAnywhere"):
            profile.attributes["PREMIUM_ANYWHERE"] = True
            profile.add_note("This user can use premium in _any_ server.")
            profile.add_features("premium", "pro")
        """

        data_patreon = await self.has_patreon_premium(author, author_data)

        if data_patreon:
            profile.load_patreon(data_patreon)
            profile.add_features("premium", "pro")
        else:
            data_selly = await self.has_selly_premium(author, author_data)

            if data_selly["premium"]:
                profile.add_features("premium")
                profile.load_selly(days=data_selly["days"])

            if data_selly["pro_access"]:
                profile.add_features("pro")

            if not profile.features.get("pro"):
                if await self.is_staff(author):
                    profile.add_features("premium", "pro")
                    profile.days = 0
                    profile.add_note("This user is a Bloxlink Staff member.")
                    profile.add_note("This user can use premium in _any_ server.")
                    profile.attributes["PREMIUM_ANYWHERE"] = True

        if guild and partner_check:
            partners_cache = await cache_get("partners:guilds", guild.id)

            if partners_cache:
                profile.add_features("premium")
                profile.days = 0
                profile.add_note("This server has free premium from a partnership.")

        if cache:
            if guild and cache_as_guild:
                await cache_set("premium_cache", guild.id, (profile, None))
            else:
                await cache_set("premium_cache", author.id, (profile, None))

        return profile, None
