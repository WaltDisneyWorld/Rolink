from discord.errors import Forbidden, NotFound
from ..exceptions import CancelCommand, Error # pylint: disable=import-error
from ..structures import Bloxlink # pylint: disable=import-error
from ..constants import SERVER_INVITE # pylint: disable=import-error
from asyncio import TimeoutError

class Paginate:
    """Smart paginator for Discord embeds"""

    def __init__(self, message, channel, embed, response=None, original_channel=None, field_limit=25, pages=None, dm=False):
        self.message = message
        self.author = message.author
        self.embed = embed
        self.response = response
        self.original_channel = original_channel

        self.field_limit = field_limit
        self.channel = channel
        self._pages = pages
        self.dm = dm

        self.sent_message = None

    @staticmethod
    def get_pages(embed, fields, field_limit=25):
        pages = []
        i = 0

        len_fields = len(fields)

        while True:
            remaining = 5000
            field = fields[i]
            current_page = []

            while remaining > 0 and i != len(fields):
                # get first 1024 characters, append, remove from old field
                # if the old field is gone, increment i
                # if it's 6000, append to pages and clear current_page, and reset remaining

                # check to see if there's room on the current page
                len_field_name = len(field.name)
                if remaining > len_field_name + 1:
                    # get first 1024 characters with respect to remaining
                    chars = field.value[0:min(1000, remaining - len_field_name)]
                    len_chars = len(chars)
                    current_page.append({"name": field.name, "value": chars})
                    remaining -= len_chars
                    field.value = field.value[len_chars:] # remove characters

                    if not field.value:
                        # no more field, so get next one. there's still room for more, though
                        if i + 1 < len(fields):
                            i += 1
                            field = fields[i]
                        else:
                            break
                else:
                    # page is done
                    pages.append(current_page)
                    if not field.value:
                        i += 1

                    break

            if not field.value and len_fields <= i + 1:
                pages.append(current_page)

                break

        """
        current_page = []
        remaining = 5000
        skip_over = False

        for field in fields:
            while remaining:

                if remaining > len(field.name) + 1:
                    chars = field.value[0:min(1000, remaining - len(field.name))]
                    current_page.append({"name": field.name, "value": field.value})
                    field.value = field.value[len(chars):]
                    remaining -= len(chars)
                    if not field.value:
                        #skip_over = True

                        break

                else:
                    pages.append(current_page)
                    current_page = []
                    remaining = 5000
                    skip_over = True

                    break

                #chars = field.value[0:min(1000, remaining - len(field.name))]
                #current_page.append({"name": field.name, "value": field.value})

            if not skip_over:
                remaining = 5000
                pages.append(current_page)
                current_page = []
            else:
                skip_over = False


        """



        return pages

    async def turn_page(self, i, pages):
        self.embed.clear_fields()

        total = 0
        for field in pages[i]:
            self.embed.add_field(name=field["name"], value=field["value"], inline=False)

        if self.sent_message:
            try:
                await self.sent_message.edit(embed=self.embed)
            except (NotFound, Forbidden):
                raise CancelCommand
        else:
            self.sent_message = await self.response.send(embed=self.embed, channel_override=self.channel, ignore_http_check=True)

            if not self.sent_message:
                return False

        return True

    async def __call__(self):
        send_to = self.original_channel or self.channel

        pages = self._pages or Paginate.get_pages(self.embed, self.embed.fields, self.field_limit)
        len_pages = len(pages)

        i = 0
        user = None

        success = await self.turn_page(i, pages)

        if success:
            if self.dm:
                await send_to.send(self.author.mention + ", **check your DMs!**")
        else:
            if self.dm:
                await send_to.send(self.author.mention + ", I was unable to DM you! Please check your privacy settings and try again.")
            else:
                await send_to.send(self.author.mention + ", an unknown error occured while sending the message. Please report this to the Bloxlink "
                                                         f"support server here: {SERVER_INVITE}")

            raise CancelCommand


        if len_pages > 1:
            reactions = {'\N{BLACK LEFT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}': lambda: 0,
                        '\N{BLACK LEFT-POINTING TRIANGLE}': lambda: i - 1 >= 0 and i - 1,
                        '\N{BLACK RIGHT-POINTING TRIANGLE}': lambda: i + 1 < len_pages and i + 1,
                        '\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}': lambda: len_pages - 1,
                        }

            for reaction in reactions:
                try:
                    await self.sent_message.add_reaction(reaction)
                except Forbidden:
                    raise Error("I'm missing the ``Add Reactions`` permission.")

            while True:
                try:
                    reaction, user = await Bloxlink.wait_for("reaction_add", check=lambda r, u: str(r) in reactions and u == self.author and \
                                                                                                r.message.id == self.sent_message.id, timeout=120)
                except TimeoutError:
                    try:
                        await self.sent_message.clear_reactions()
                        raise CancelCommand
                    except Forbidden:
                        raise Error("I'm missing the ``Manage Messages`` permission.")
                    except NotFound:
                        raise CancelCommand

                emoji = str(reaction)
                fn = reactions[emoji]
                x = fn()

                if x is not False:
                    i = x
                    await self.turn_page(i, pages)

                if user:
                    try:
                        await self.sent_message.remove_reaction(emoji, user)
                    except Forbidden:
                        raise Error("I'm missing the ``Manage Messages`` permission.")
                    except NotFound:
                        raise CancelCommand


        return self.sent_message