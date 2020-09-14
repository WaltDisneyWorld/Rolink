from discord.utils import find
from discord.errors import Forbidden, NotFound
from re import compile

from ..structures.Bloxlink import Bloxlink
from ..exceptions import PermissionError

@Bloxlink.module
class Resolver(Bloxlink.Module):
    def __init__(self):
        self.user_pattern = compile(r"<@!?([0-9]+)>")

    async def string_resolver(self, message, arg, content=None):
        if not content:
            content = message.content

        min = arg.get("min", 1)
        max = arg.get("max", 100)

        if message and message.role_mentions:
            return message.role_mentions[0].name[:max], None

        if arg.get("min") or arg.get("max"):
            if min <= len(content) <= max:
                return str(content), None
            else:
                return False, f"String character count not in range: {min}-{max}"

        return str(content), None

    async def number_resolver(self, message, arg, content=None):
        if not content:
            content = message.content

        if content.isdigit():
            min = arg.get("min", -100)
            max = arg.get("max", 100)

            if arg.get("min") or arg.get("max"):
                if min <= len(content) <= max:
                    return int(content), None
                else:
                    return False, f'Number character count not in range: {min}-{max}'
            else:
                return int(content), None

            return int(content), None

        return False, "You must pass a number"

    async def choice_resolver(self, message, arg, content=None):
        if not content:
            content = message.content

        content = content.lower()

        for choice in arg["choices"]:
            choice_lower = choice.lower()

            if choice_lower == content or content == choice_lower[0:len(content)]:
                return choice, None

        return False, f"Choice must be of either: {str(arg['choices'])}"


    async def user_resolver(self, message, arg, content=None):
        if not content:
            content = message.content

        guild = message.guild

        if not arg.get("multiple"):
            if message.mentions:
                for mention in message.mentions:
                    if mention.id != self.client.user.id:
                        return mention, None

            if message.raw_mentions:
                user_id = self.user_pattern.search(content)

                if user_id:
                    user_id = int(user_id.group(1))

                    if user_id != self.client.user.id:
                        try:
                            user = await self.client.fetch_user(user_id)
                            return user, None
                        except NotFound:
                            return False, "A user with this discord ID does not exist"


            is_int, is_id = None, None

            try:
                is_int = int(content)
                is_id = is_int > 15
            except ValueError:
                pass

            if is_id:
                user = guild.get_member(is_int)

                if user:
                    return user, None
                else:
                    try:
                        user = await self.client.fetch_user(int(is_int))
                        return user, None
                    except NotFound:
                        return False, "A user with this discord ID does not exist"
            else:
                return None, "Please search for a member via ID or a ping. See ``[this article](https://support.discord.com/hc/en-us/articles/206346498-Where-can-I-find-my-User-Server-Message-ID-) ``for instructions on getting someone's ID."

            return False, "Invalid user"
        else:
            users = []
            max = arg.get("max")
            count = 0

            lookup_strings = content.split(" ")

            if max:
                lookup_strings = lookup_strings[:max]

            for user in message.mentions:
                if max:
                    if count >= max:
                        break
                    else:
                        count += 1

                users.append(user)

            for lookup_string in lookup_strings:
                if max:
                    if count >= max:
                        break

                if lookup_string.isdigit():
                    try:
                        member = await guild.fetch_member(int(lookup_string))
                    except NotFound:
                        pass
                    else:
                        users.append(member)

                    count += 1


            return users, None

    async def channel_resolver(self, message, arg, content=None):
        if not content:
            content = message.content

        guild = message.guild

        if message and message.channel_mentions:
            return message.channel_mentions[0], None
        else:
            is_int, is_id = None, None

            try:
                is_int = int(content)
                is_id = is_int > 15
            except ValueError:
                pass

            if is_id:
                channel = guild.get_channel(is_int)

                if channel:
                    return channel, None
            else:
                channel = find(lambda c: c.name == content, guild.text_channels)

                if channel:
                    return channel, None

        return False, "Invalid channel"

    async def role_resolver(self, message, arg, content=None):
        if not content:
            content = message.content

        guild = message.guild

        if message and message.role_mentions:
            return message.role_mentions[0], None
        else:
            is_int, is_id = None, None
            role = None

            try:
                is_int = int(content)
                is_id = is_int > 15
            except ValueError:
                pass

            if is_id:
                role = find(lambda r: r.id == is_int, guild.roles)
            else:
                role = find(lambda r: r.name == content, guild.roles)

            if role:
                return role, None
            else:
                try:
                    role = await guild.create_role(name=content, reason="Creating missing role")
                except Forbidden:
                    raise PermissionError(f"Failed to create role {content}, please ensure I have the ``Manage Roles`` permission.")
                else:
                    return role, None

        return False, "Invalid role"

    async def image_resolver(self, message, arg, content=None):
        if not content:
            content = message.content

        if message and message.attachments:
            for attachment in message.attachments:
                if attachment.height and attachment.width:
                    # is an image
                    return attachment.proxy_url or attachment.url, None

        if "https://" in content:
            return content, None
        else:
            return False, "This doesn't appear to be a valid https URL."


    def get_resolver(self, name):
        for method_name in dir(self):
            if method_name.endswith("resolver") and name in method_name:
                if callable(getattr(self, method_name)):
                    return getattr(self, method_name)

