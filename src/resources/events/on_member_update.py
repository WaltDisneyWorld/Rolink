from ..structures.Bloxlink import Bloxlink # pylint: disable=import-error
from ..exceptions import RobloxDown, CancelCommand # pylint: disable=import-error
from ..constants import DEFAULTS # pylint: disable=import-error

get_guild_value = Bloxlink.get_module("cache", attrs=["get_guild_value"])
guild_obligations = Bloxlink.get_module("roblox", attrs=["guild_obligations"])


@Bloxlink.module
class MemberUpdateEvent(Bloxlink.Module):
    def __init__(self):
        pass

    async def __setup__(self):

        @Bloxlink.event
        async def on_member_update(before, after):
            guild = before.guild

            if self.redis and not before.bot and (before.pending and not after.pending):
                options = await get_guild_value(guild, ["autoRoles", DEFAULTS.get("autoRoles")], ["autoVerification", DEFAULTS.get("autoVerification")])

                auto_roles = options.get("autoRoles")
                auto_verification = options.get("autoVerification")

                if auto_verification or auto_roles:
                    try:
                        await guild_obligations(after, guild, cache=False, dm=True, event=True)
                    except (RobloxDown, CancelCommand):
                        pass
