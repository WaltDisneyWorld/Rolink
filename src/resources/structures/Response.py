from discord.errors import Forbidden, HTTPException, DiscordException, NotFound
from discord import Object
from ..exceptions import PermissionError, Message # pylint: disable=no-name-in-module, import-error
from ..structures import Bloxlink, Paginate # pylint: disable=no-name-in-module, import-error
from config import REACTIONS # pylint: disable=no-name-in-module
from ..constants import IS_DOCKER, EMBED_COLOR # pylint: disable=no-name-in-module, import-error
import asyncio

loop = asyncio.get_event_loop()

get_features = Bloxlink.get_module("premium", attrs=["get_features"])
cache_set, cache_get, cache_pop = Bloxlink.get_module("cache", attrs=["set", "get", "pop"])

class ResponseLoading:
    def __init__(self, response, backup_text):
        self.response = response
        self.original_message = response.message
        self.reaction = None
        self.channel = response.message.channel

        self.reaction_success = False
        self.from_reaction_fail_msg = None

        self.backup_text = backup_text

    @staticmethod
    def _check_reaction(message):
        def _wrapper(reaction, user):
            return reaction.me and str(reaction) == REACTIONS["LOADING"] and message.id == reaction.message.id

    async def _send_loading(self):
        try:
            future = Bloxlink.wait_for("reaction_add", check=self._check_reaction(self.original_message), timeout=60)

            try:
                await self.original_message.add_reaction(REACTIONS["LOADING"])
            except (Forbidden, HTTPException):
                try:
                    self.from_reaction_fail_msg = await self.channel.send(self.backup_text)
                except Forbidden:
                    raise PermissionError
            else:
                reaction, _ = await future
                self.reaction_success = True
                self.reaction = reaction

        except (NotFound, asyncio.TimeoutError):
            pass

    async def _remove_loading(self, success=True, error=False):
        try:
            if self.reaction_success:
                for reaction in self.original_message.reactions:
                    if reaction == self.reaction:
                        try:
                            async for user in reaction.users():
                                await self.original_message.remove_reaction(self.reaction, user)
                        except (NotFound, HTTPException):
                            pass

                if error:
                    await self.original_message.add_reaction(REACTIONS["ERROR"])
                elif success:
                    await self.original_message.add_reaction(REACTIONS["DONE"])

            elif self.from_reaction_fail_msg is not None:
                await self.from_reaction_fail_msg.delete()

        except (NotFound, HTTPException):
            pass

    def __enter__(self):
        loop.create_task(self._send_loading())
        return self

    def __exit__(self, tb_type, tb_value, traceback):
        if (tb_type is None) or (tb_type == Message):
            loop.create_task(self._remove_loading(error=False))
        else:
            loop.create_task(self._remove_loading(error=True))

    async def __aenter__(self):
        await self._send_loading()

    async def __aexit__(self, tb_type, tb_value, traceback):
        if tb_type is None:
            await self._remove_loading(success=True)
        elif tb_type == Message:
            await self._remove_loading(success=False, error=False)
        else:
            await self._remove_loading(error=True)



class Response(Bloxlink.Module):
    def __init__(self, CommandArgs):
        self.webhook_only = CommandArgs.guild_data.get("customBot", {})

        self.message = CommandArgs.message
        self.guild = CommandArgs.message.guild
        self.author = CommandArgs.message.author
        self.channel = CommandArgs.message.channel
        self.prompt = None # filled in on commands.py
        self.args = CommandArgs

        self.delete_message_queue = []

        if self.webhook_only:
            self.bot_name = self.args.guild_data["customBot"].get("name", "Bloxlink")
            self.bot_avatar = self.args.guild_data["customBot"].get("avatar", "")
        else:
            self.bot_name = self.bot_avatar = None

    def loading(self, text="Please wait until the operation completes."):
        return ResponseLoading(self, text)

    def delete(self, *messages):
        for message in messages:
            if message:
                self.delete_message_queue.append(message.id)

    async def send(self, content=None, embed=None, on_error=None, dm=False, no_dm_post=False, strict_post=False, files=None, ignore_http_check=False, paginate_field_limit=None, channel_override=None, allowed_mentions=None):
        if dm and not IS_DOCKER:
            dm = False

        actually_dm = not self.guild # used to send the "check your DMs!" messages
        channel = channel_override or (dm and self.author or self.channel)
        webhook = None

        if self.webhook_only and self.guild:
            my_permissions = self.guild.me.guild_permissions

            if my_permissions.manage_webhooks:
                profile, _ = await get_features(Object(id=self.guild.owner_id), guild=self.guild)

                if profile.features.get("premium"):
                    webhook = await cache_get(f"webhooks:{channel.id}")

                    if not webhook:
                        try:
                            for webhook in await self.channel.webhooks():
                                if webhook.token:
                                    await cache_set(f"webhooks:{channel.id}", webhook)
                                    break
                            else:
                                webhook = await self.channel.create_webhook(name="Bloxlink Webhooks")
                                await cache_set(f"webhooks:{channel.id}", webhook)

                        except (Forbidden, NotFound):
                            self.webhook_only = False

                            try:
                                await channel.send("Customized Bot is enabled, but I couldn't "
                                                   "create the webhook! Please give me the ``Manage Webhooks`` permission.")
                            except (Forbidden, NotFound):
                                pass
            else:
                self.webhook_only = False

                try:
                    await channel.send("Customized Bot is enabled, but I couldn't "
                                       "create the webhook! Please give me the ``Manage Webhooks`` permission.")
                except (Forbidden, NotFound):
                    pass


        paginate = False
        pages = None

        if paginate_field_limit:
            pages = Paginate.get_pages(embed, embed.fields, paginate_field_limit)

            if len(pages) > 1:
                paginate = True


        if embed and not dm and not embed.color:
            embed.color = EMBED_COLOR

        if not paginate:
            try:
                if webhook and not dm:
                    try:
                        msg = await webhook.send(embed=embed, content=content,
                                                 wait=True, username=self.bot_name,
                                                 avatar_url=self.bot_avatar)
                    except asyncio.TimeoutError:
                        return None

                    except NotFound:
                        await cache_pop(f"webhooks:{channel.id}")

                        return await self.send(content=content, embed=embed, on_error=on_error, dm=dm, no_dm_post=no_dm_post, strict_post=strict_post, files=files, allowed_mentions=allowed_mentions)
                else:
                    try:
                        msg = await channel.send(embed=embed, content=content, files=files)

                    except asyncio.TimeoutError:
                        return None

                if dm and not no_dm_post and not actually_dm:
                    if webhook:
                        try:
                            await webhook.send(content=self.author.mention + ", **check your DMs!**",
                                               username=self.bot_name, avatar_url=self.bot_avatar)
                        except asyncio.TimeoutError:
                            return None

                        except NotFound:
                            await cache_pop(f"webhooks:{channel.id}")

                            return await self.send(content=content, embed=embed, on_error=on_error, dm=dm, no_dm_post=no_dm_post, strict_post=strict_post, files=files, allowed_mentions=allowed_mentions)
                    else:
                        try:
                            await self.channel.send(self.author.mention + ", **check your DMs!**")
                        except asyncio.TimeoutError:
                            return None

                return msg

            except (Forbidden, NotFound):
                channel = not strict_post and (dm and self.channel or self.author) or channel # opposite channel

                try:
                    if webhook and not dm:
                        try:
                            msg = await webhook.send(content=on_error or content, embed=embed,
                                                     wait=True, username=self.bot_name, avatar_url=self.bot_avatar,
                                                     allowed_mentions=allowed_mentions)
                        except NotFound:
                            await cache_pop(f"webhooks:{channel.id}")

                            return await self.send(content=content, embed=embed, on_error=on_error, dm=dm, no_dm_post=no_dm_post, strict_post=strict_post, files=files, allowed_mentions=allowed_mentions)

                        else:
                            return msg

                    return await channel.send(content=on_error or content, embed=embed, files=files, allowed_mentions=allowed_mentions)

                except (Forbidden, NotFound):
                    try:
                        if dm:
                            if webhook:
                                try:
                                    await webhook.send(f"{self.author.mention}, I was unable to DM you. "
                                                        "Please check your privacy settings and try again.",
                                                        username=self.bot_name, avatar_url=self.bot_avatar)
                                except asyncio.TimeoutError:
                                    return None

                                except NotFound:
                                    await cache_pop(f"webhooks:{channel.id}")

                                    return await self.send(content=content, embed=embed, on_error=on_error, dm=dm, no_dm_post=no_dm_post, strict_post=strict_post, files=files, allowed_mentions=allowed_mentions)

                            else:
                                try:
                                    await self.channel.send(f"{self.author.mention}, I was unable to DM you. "
                                                            "Please check your privacy settings and try again.")
                                except asyncio.TimeoutError:
                                    return None
                        else:
                            try:
                                await self.author.send(f"You attempted to use command {self.args.command_name} in "
                                                       f"{self.channel.mention}, but I was unable to post there. "
                                                        "You may need to grant me the ``Embed Links`` permission.", files=files)
                            except asyncio.TimeoutError:
                                return None

                        return None

                    except (Forbidden, NotFound):
                        return None

            except HTTPException:
                if not ignore_http_check:
                    if self.webhook_only:
                        self.webhook_only = False
                        return await self.send(content=content, embed=embed, on_error=on_error, dm=dm, no_dm_post=no_dm_post, strict_post=strict_post, files=files, allowed_mentions=allowed_mentions)

                    else:
                        if embed:
                            paginate = True

                        else:
                            raise HTTPException
        if paginate:
            paginator = Paginate(self.message, channel, embed, self, field_limit=paginate_field_limit, original_channel=self.channel, pages=pages, dm=not actually_dm and dm)

            return await paginator()

        return None

    async def error(self, text, *, embed_color=0xE74C3C, embed=None, dm=False, **kwargs):
        emoji = self.webhook_only and ":cry:" or "<:BloxlinkError:506622933226225676>"

        if embed and not dm:
            embed.color = embed_color

        return await self.send(f"{emoji} {text}", **kwargs)

    async def success(self, success, embed=None, embed_color=0x36393E, dm=False, **kwargs):
        emoji = self.webhook_only and ":thumbsup:" or "<:BloxlinkSuccess:506622931791773696>"

        if embed and not dm:
            embed.color = embed_color

        return await self.send(f"{emoji} {success}", embed=embed, dm=dm, **kwargs)

    async def silly(self, text, embed=None, embed_color=0x36393E, dm=False, **kwargs):
        emoji = self.webhook_only and ":sweat_smile:" or "<:BloxlinkSweaty:506622933502918656>"

        if embed and not dm:
            embed.color = embed_color

        return await self.send(f"{emoji} {text}", embed=embed, dm=dm, **kwargs)

    async def info(self, text, embed=None, embed_color=0x36393E, dm=False, **kwargs):
        emoji = self.webhook_only and ":mag_right:" or "<:BloxlinkSearch:506622933012054028>"

        if embed and not dm:
            embed.color = embed_color

        return await self.send(f"{emoji} {text}", embed=embed, dm=dm, **kwargs)

    async def reply(self, text, embed=None, embed_color=0x36393E, dm=False, **kwargs):
        return await self.send(f"{self.author.mention}, {text}", embed=embed, dm=dm, **kwargs)
