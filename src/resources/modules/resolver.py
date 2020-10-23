from discord.utils import find
from discord.errors import Forbidden, NotFound
from re import compile

from ..structures.Bloxlink import Bloxlink
from ..exceptions import PermissionError

@Bloxlink.module
class Resolver(Bloxlink.Module):
    def __init__(self):
        self.user_pattern = compile(r"<@!?([0-9]+)>")
        self.role_pattern = compile(r"<@&([0-9]+)>")

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
                member = guild.get_member(content)

                if not member:
                    member = await guild.query_members(content, limit=1)

                    if member:
                        return member[0], None
                    else:
                        return False, "Could not find a matching member. Please search by their username or ID."

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
                if lookup_string:
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

                    else:
                        member = await guild.query_members(lookup_string, limit=1)

                        if member:
                            users.append(member[0])

                    count += 1

            if not users:
                return None, "Invalid user(s)"

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
        roles = []
        create_missing_role = arg.get("create_missing_role", True)
        max = arg.get("max")
        multiple = arg.get("multiple")

        if message.role_mentions:
            for role in message.role_mentions:
                roles.append(role)

                if not multiple:
                    break
        else:
            lookup_strings = content.split(",")

            for lookup_string in lookup_strings:
                if lookup_string:
                    lookup_string = lookup_string.strip()
                    role = None

                    if lookup_string.isdigit():
                        role = guild.get_role(int(lookup_string))
                    else:
                        role = find(lambda r: r.name == lookup_string, guild.roles)

                    if not role:
                        if create_missing_role:
                            try:
                                role = await guild.create_role(name=lookup_string)
                            except Forbidden:
                                return None, "I was unable to create the role. Please ensure I have the ``Manage Roles`` permission."
                            else:
                                roles.append(role)
                        else:
                            return None, "Invalid role(s)"
                    else:
                        if role != guild.default_role and role not in roles:
                            roles.append(role)

        if not roles:
            return None, "Invalid role(s)"

        if max:
            return roles[:max]
        else:
            if multiple:
                return roles, None
            else:
                return roles[0], None


    async def role_resolver2(self, message, arg, content=None):
        if not content:
            content = message.content

        guild = message.guild

        roles = []

        if message and message.role_mentions:
            for role in message.role_mentions:
                if role != guild.default_role:
                    roles.append(role)

                    if not arg.get("multiple"):
                        break
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

            if role and role != guild.default_role:
                return role, None

            if arg.get("create_missing_role", True):
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

