from resources.structures.Bloxlink import Bloxlink
from resources.exceptions import UserNotVerified, Message, Error, RobloxNotFound
from discord import Embed

get_user = Bloxlink.get_module("roblox", attrs=["get_user"])


@Bloxlink.command
class RobloxSearchCommand(Bloxlink.Module):
    """retrieve the Roblox information of a user"""

    def __init__(self):
        self.aliases = ["rs", "search"]
        self.arguments = [
            {
                "prompt": "Please specify either a username or Roblox ID. If the person's name is all numbers, "
                          "then attach a ``--username`` flag to this command. Example: ``!getinfo 1234 --username`` will "
                          "search for a user with a Roblox username of '1234' instead of a Roblox ID.",
                "type": "string",
                "name": "target"
            }
        ]

        self.examples = [
            "roblox",
            "569422833",
            "569422833 --username"
        ]

    @Bloxlink.flags
    async def __main__(self, CommandArgs):
        target = CommandArgs.parsed_args["target"]
        flags = CommandArgs.flags
        response = CommandArgs.response

        valid_flags = ["username", "id", "avatar", "premium", "badges", "groups", "description", "blurb", "age", "banned"]

        if not all(f in valid_flags for f in flags.keys()):
            raise Error(f"Invalid flag! Valid flags are: ``{', '.join(valid_flags)}``")

        username = ID = False

        if "username" in flags:
            username = True
            flags.pop("username")
        elif target.isdigit():
            ID = True
        else:
            username = True

        async with response.loading():
            try:
                account, _ = await get_user(*flags.keys(), username=username and target, roblox_id=ID and target, send_embed=True, response=response, everything=not bool(flags), basic_details=not bool(flags))
            except RobloxNotFound:
                raise Error("This Roblox account doesn't exist.")
