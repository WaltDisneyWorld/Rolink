from resources.structures.Bloxlink import Bloxlink # pylint: disable=import-error
from resources.constants import RELEASE, RED_COLOR # pylint: disable=import-error
from resources.exceptions import Error, Message # pylint: disable=import-error
from io import StringIO
from discord.errors import Forbidden, NotFound
from discord import File
import asyncio
import math
import datetime

loop = asyncio.get_event_loop()


extract_accounts = Bloxlink.get_module("roblox", attrs=["extract_accounts"])
post_event = Bloxlink.get_module("utils", attrs=["post_event"])


@Bloxlink.command
class BanEvadersCommand(Bloxlink.Module):
    """scan your server for ban-evaders"""

    def __init__(self):
        self.permissions = Bloxlink.Permissions().build("BLOXLINK_MODERATOR")
        self.arguments = [
            {
                "prompt": "This command will scan your server members for members with Roblox accounts which correspond to banned members of your server.\n\n"
                          "Would you like to **ban** ban-evaders, **kick** them, or do **nothing**?\n\nI will provide a list of members if you choose the ``nothing`` option.",
                "type": "choice",
                "name": "action",
                "choices": ("kick", "ban", "nothing")
            }
        ]
        self.category = "Premium"
        self.REDIS_COOLDOWN_KEY = "guild_scan:{id}"
        self.aliases = ["bansearch"]

    async def process_guild(self, guild_data, guild, author, action, response, locale, prefix):
        if not guild.chunked:
            try:
                await guild.chunk()
            except:
                pass

        await response.send(locale("scans.starting"))

        if action in ("kick", "ban"):
            await post_event(guild, guild_data, "moderation", f"{author.mention} ({author.id}) has ran the ``{prefix}banevaders`` command and chose to **{action}** ban-evaders.", RED_COLOR)
        else:
            await post_event(guild, guild_data, "moderation", f"{author.mention} ({author.id}) has ran the ``{prefix}banevaders`` command.", RED_COLOR)

        try:
            redis_cooldown_key = self.REDIS_COOLDOWN_KEY.format(release=RELEASE, id=guild.id)
            await self.redis.set(redis_cooldown_key, 2, ex=86400)

            ban_evaders = {}

            try:
                bans = await guild.bans()
            except Forbidden:
                raise Error(locale("commands.banevaders.errors.noPermission"))

            for ban in bans:
                user = ban.user
                user_data = await self.r.db("bloxlink").table("users").get(str(user.id)).run() or {}
                roblox_data = await extract_accounts(user_data, resolve_to_users=False, reverse_search=True)

                for roblox_id, discord_accounts in roblox_data.items():
                    for discord_id in discord_accounts:
                        ban_evader = guild.get_member(int(discord_id))

                        if ban_evader:
                            ban_evaders[user] = ban_evaders.get(user) or []

                            if ban_evader not in ban_evaders[user]:
                                ban_evaders[user].append(ban_evader)

            if ban_evaders:
                now = datetime.datetime.now()
                ban_evaders_file = [locale("commands.banevaders.reportGenerated"), now.strftime("%d %B %Y, %H:%M:%S"), ""]
                successful, failed = [], []

                for original_account, new_accounts in ban_evaders.items():
                    accounts_str = [str(x) + " " + f'({x.id})' for x in new_accounts]

                    ban_evaders_file.append(locale("commands.banevaders.fileAppend", original_account_name=original_account.name,
                                            original_account_id=original_account.id, accounts_str=', '.join(accounts_str)))

                    if action in ("kick", "ban"):
                        for discord_account in new_accounts:
                            if action == "ban":
                                try:
                                    await guild.ban(discord_account, reason=locale("commands.banevaders.guildBanReason", user=author))
                                except (Forbidden, NotFound):
                                    failed.append(f"{str(discord_account)} ({discord_account.id})")
                                else:
                                    successful.append(f"{str(discord_account)} ({discord_account.id})")

                            elif action == "kick":
                                try:
                                    await guild.kick(discord_account, reason=locale("commands.banevaders.guildKickReason", user=author))
                                except (Forbidden, NotFound):
                                    failed.append(f"{str(discord_account)} ({discord_account.id})")
                                else:
                                    successful.append(f"{str(discord_account)} ({discord_account.id})")


                final_buffer = StringIO("\r\n\n".join(ban_evaders_file))

                await response.send(locale("commands.banevaders.match"), files=[
                    File(final_buffer, filename=now.strftime("ban-evaders_%d-%m-%Y")),
                ])

                if successful:
                    succeeded_buffer = StringIO("\r\n\n".join(successful))

                    await response.send(locale("commands.banevaders.success"), files=[
                        File(succeeded_buffer, filename=now.strftime(f"successful_{action}_%d-%m-%Y")),
                    ])

                    succeeded_buffer.close()

                if failed:
                    failed_buffer = StringIO("\r\n\n".join(failed))

                    await response.send(locale("commands.banevaders.failed"), files=[
                        File(failed_buffer, filename=now.strftime(f"failed_{action}_%d-%M-%Y")),
                    ])

                    failed_buffer.close()

                final_buffer.close()

            else:
                await response.send(f"{locale('commands.banevaders.noMatch')} :tada:")

        finally:
            cooldown = 120 * 60

            if self.redis:
                await self.redis.set(redis_cooldown_key, 3, ex=cooldown)


    async def __main__(self, CommandArgs):
        response   = CommandArgs.response
        action     = CommandArgs.parsed_args["action"]
        guild      = CommandArgs.message.guild
        author     = CommandArgs.message.author
        locale     = CommandArgs.locale
        guild_data = CommandArgs.guild_data
        prefix     = CommandArgs.prefix

        if self.redis:
            redis_cooldown_key = self.REDIS_COOLDOWN_KEY.format(release=RELEASE, id=guild.id)
            on_cooldown = await self.cache.get(redis_cooldown_key)

            if on_cooldown:
                cooldown_time = math.ceil(await self.redis.ttl(redis_cooldown_key)/60)

                if not cooldown_time or cooldown_time == -1:
                    await self.redis.delete(redis_cooldown_key)
                    on_cooldown = None

                if on_cooldown:
                    if on_cooldown == 1:
                        raise Message(locale("scans.queued"))
                    elif on_cooldown == 2:
                        raise Message(locale("scans.running"))
                    elif on_cooldown == 3:
                        cooldown_time = math.ceil(await self.redis.ttl(redis_cooldown_key)/60)

                        raise Message(locale("scans.cooldown", cooldown=cooldown_time))

            await self.redis.set(redis_cooldown_key, 1, ex=86400)
            await self.process_guild(guild_data, guild, author, action, response, locale, prefix)
