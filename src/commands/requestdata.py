from resources.structures.Bloxlink import Bloxlink # pylint: disable=import-error
from resources.exceptions import Message, CancelCommand # pylint: disable=import-error
from json import dumps
from math import ceil
from time import time
from discord import File
from io import StringIO


@Bloxlink.command
class RequestDataCommand(Bloxlink.Module):
    """view all of your data saved under your Discord ID"""

    def __init__(self):
        self.aliases = ["rd"]

    async def __main__(self, CommandArgs):
        author = CommandArgs.message.author
        author_data = await self.r.table("users").get(str(author.id)).run() or {}

        response = CommandArgs.response

        time_now = time()
        last_requested = author_data.get("lastRequestedData", 0)
        on_cooldown = last_requested > time_now
        days_left = last_requested > time_now and ceil((last_requested - time_now)/86400)

        if on_cooldown:
            raise Message("You've recently requested a copy of your data! You may request again in "
                          f"**{days_left}** day{days_left > 1 and 's'}.", type="silly")

        try:
            user_json = dumps(author_data)
            buffer = StringIO(user_json)

            message = await response.info("As you've requested, here's your data. You may request again "
                                          "in **30** days.", files=[File(buffer, filename=f"{author.id}.json")],
                                          dm=True, strict_post=True)

            if not message:
                raise CancelCommand

            last_requested = time() + (86400*30)

            await self.r.table("users").insert({
                "id": str(author.id),
                "lastRequestedData": last_requested
            }, conflict="update").run()

        finally:
            buffer.close()
