from resources.structures.Bloxlink import Bloxlink # pylint: disable=import-error
from resources.exceptions import Message, Error # pylint: disable=import-error
import time
import math
from discord import Embed, Object


transfer_premium, get_features = Bloxlink.get_module("premium", attrs=["transfer_premium", "get_features"])
cache_pop = Bloxlink.get_module("cache", attrs="pop")


@Bloxlink.command
class TransferCommand(Bloxlink.Module):
    """transfer your Bloxlink premium"""

    def __init__(self):
        self.examples = ["@justin", "disable"]
        self.arguments = [{
            "prompt": "Please specify the user to transfer premium to.",
            "name": "user",
            "type": "user",
        }]
        self.category = "Premium"
        self.free_to_use = True

    @Bloxlink.flags
    async def __main__(self, CommandArgs):
        author = CommandArgs.message.author
        guild = CommandArgs.message.guild
        transfer_to = CommandArgs.parsed_args.get("user")
        response = CommandArgs.response
        prefix = CommandArgs.prefix

        if transfer_to.bot:
            raise Message("You cannot transfer your premium to bots!", type="silly")

        author_data = await self.r.db("bloxlink").table("users").get(str(author.id)).run() or {"id": str(author.id)}

        time_now = time.time()

        author_premium_data = author_data.get("premium", {})

        transfer_cooldown = author_premium_data.get("transferCooldown") or 0
        on_cooldown = transfer_cooldown > time_now

        if on_cooldown:
            days_left = math.ceil((transfer_cooldown - time_now)/86400)

            raise Message(f"You recently transferred your premium! You may transfer again in **{days_left}** day{days_left > 1 and 's' or ''}.", type="silly")

        if author_premium_data.get("transferTo"):
            raise Message(f"You are currently transferring your premium to another user! Please disable it with ``{prefix}transfer "
                           "disable`` first.", type="silly")
        elif author_premium_data.get("transferFrom"):
            raise Error("You may not transfer premium that someone else transferred to you. You must first revoke the transfer "
                       f"with ``{prefix}transfer disable``.")

        prem_data, _ = await get_features(author, author_data, cache=False, rec=False, partner_check=False)

        if not prem_data.features.get("premium"):
            raise Error("You must have premium in order to transfer it!")

        recipient_data = await self.r.db("bloxlink").table("users").get(str(transfer_to.id)).run() or {}
        recipient_data_premium = recipient_data.get("premium", {})

        if recipient_data_premium.get("transferFrom"):
            raise Error(f"Another user is already forwarding their premium to this user. The recipient must run ``{prefix}transfer disable`` "
                        "to revoke the external transfer.")

        await transfer_premium(transfer_from=author, transfer_to=transfer_to, guild=guild, apply_cooldown=True)

        await response.success(f"Successfully **transferred** your premium to **{transfer_to}!**")


    @Bloxlink.subcommand()
    async def disable(self, CommandArgs):
        """disable your Bloxlink premium transfer"""

        author = CommandArgs.message.author
        guild = CommandArgs.message.guild
        response = CommandArgs.response

        author_data = await self.r.db("bloxlink").table("users").get(str(author.id)).run() or {"id": str(author.id)}

        author_data_premium = author_data.get("premium", {})
        transfer_to = author_data_premium.get("transferTo")

        if not transfer_to:
            transfer_from = author_data_premium.get("transferFrom")

            if not transfer_from:
                raise Message("You've not received a premium transfer!", type="silly")

            # clear original transferee and recipient data
            transferee_data = await self.r.db("bloxlink").table("users").get(transfer_from).run() or {"id": transfer_from}
            transferee_data_premium = transferee_data.get("premium", {})

            author_data_premium["transferFrom"] = None
            transferee_data_premium["transferTo"] = None

            author_data["premium"] = author_data_premium
            transferee_data["premium"] = transferee_data_premium

            await self.r.db("bloxlink").table("users").insert(author_data, conflict="update").run()
            await self.r.db("bloxlink").table("users").insert(transferee_data, conflict="update").run()

            await cache_pop("premium_cache", author.id)
            await cache_pop("premium_cache", int(transfer_from))
            await cache_pop("premium_cache", guild.id)

            raise Message("Successfully **disabled** the premium transfer!", type="success")

        else:
            recipient_data = await self.r.db("bloxlink").table("users").get(transfer_to).run() or {"id": str(transfer_to)}
            recipient_data_premium = recipient_data.get("premium", {})

            author_data_premium["transferTo"] = None
            recipient_data_premium["transferFrom"] = None

            author_data["premium"] = author_data_premium
            recipient_data["premium"] = recipient_data_premium

            await self.r.db("bloxlink").table("users").insert(author_data, conflict="update").run()
            await self.r.db("bloxlink").table("users").insert(recipient_data, conflict="update").run()

            await cache_pop("premium_cache", author.id)
            await cache_pop("premium_cache", int(transfer_to))
            await cache_pop("premium_cache", guild.id)

            await response.success("Successfully **disabled** your premium transfer!")
