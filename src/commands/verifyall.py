from resources.structures.Bloxlink import Bloxlink # pylint: disable=import-error
from resources.exceptions import Error, UserNotVerified, Message
from config import REACTIONS, VERIFYALL_MAX_SCAN # pylint: disable=no-name-in-module
from discord import Embed
import heapq
import time
import asyncio
import math

loop = asyncio.get_event_loop()

update_member = Bloxlink.get_module("roblox", attrs=["update_member"])


class Comparable:
    def __init__(self, guild_id):
        self.id = guild_id

    def __lt__(self, other):
        return self.id < other.id



@Bloxlink.command
class VerifyAllCommand(Bloxlink.Module):
    """force update everyone in the server"""

    def __init__(self):
        self.permissions = Bloxlink.Permissions().build("BLOXLINK_UPDATER")
        self.arguments = [
            {
                "prompt": "Would you like members' **roles** to be updated, their **nickname**, or **both**?\n"
                          "Please specify one of: ``roles``, ``nickname``, or ``both``.",
                "type": "choice",
                "name": "update_what",
                "choices": ("roles", "nickname", "both")
            }
        ]
        self.category = "Premium"

        self.queue = []
        self.processed = {}
        self.queue_loop_running = False

    async def process_guild(self, guild, author=None, roles=True, nickname=True, guild_data=None, trello_board=None, trello_binds_list=None, response=None):
        if not guild.chunked:
            try:
                await self.client.request_offline_members(guild)
            except:
                pass

        if response:
            if author:
                await response.send(f"{author.mention}, your server is now being scanned.")
            else:
                await response.send(f"Your server is now being scanned.")

        for member in guild.members:
            if not member.bot:
                try:
                    added, removed, nickname, errors, roblox_user = await update_member(
                        member,
                        guild             = guild,
                        guild_data        = guild_data,
                        trello_board      = trello_board,
                        trello_binds_list = trello_binds_list,
                        roles             = roles,
                        nickname          = nickname,
                        author_data       = await self.r.table("users").get(str(member.id)).run())
                except UserNotVerified:
                    pass


        len_members = len(guild.members)

        cooldown_1 = (len_members / 1000) * 120
        cooldown_2 = 120

        cooldown = max(cooldown_1, cooldown_2)

        self.processed[guild.id][0] = time.time() + (cooldown * 60)

        await response.success("This server's scan has finished.")


    async def start_queue(self):
        if not self.queue_loop_running:
            self.queue_loop_running = True
        else:
            return

        while self.queue:
            tasks = []

            for _ in range(VERIFYALL_MAX_SCAN):
                if self.queue:
                    data = heapq.heappop(self.queue)
                    guild = data[2]
                    author = data[3]
                    response = data[4]
                    trello_binds_list = data[5]
                    trello_board = data[6]
                    update_roles = data[7]
                    update_nickname = data[8]
                    guild_data = data[9]

                    if guild:
                        tasks.append(self.process_guild(guild, author=author, roles=update_roles, nickname=update_nickname, guild_data=guild_data, trello_board=trello_board, trello_binds_list=trello_binds_list, response=response))

            await asyncio.wait(tasks)

        self.queue_loop_running = False

    async def __main__(self, CommandArgs):
        response = CommandArgs.response
        update_what = CommandArgs.parsed_args["update_what"]

        guild = CommandArgs.message.guild
        guild_data = CommandArgs.guild_data

        author = CommandArgs.message.author
        channel = CommandArgs.message.channel

        trello_board = CommandArgs.trello_board
        trello_binds_list = trello_board and await trello_board.get_list(lambda l: l.name.lower() == "bloxlink binds")

        process_guild = self.processed.get(guild.id)

        if process_guild:
            cooldown = process_guild[0]
            time_now = time.time()

            if cooldown and time_now > cooldown:
                del self.processed[guild.id]
            else:
                ending = (cooldown is not None and f"please wait **{math.ceil((cooldown-time_now)/60)}** more minutes.") or "please wait until your server has finished scanning."

                if process_guild[1] == author:
                    raise Message(f"You've recently ran a scan, {ending}", type="silly")
                else:
                    raise Message(f"**{str(process_guild[1])}** recently ran a scan, {ending}", type="silly")


        self.processed[guild.id] = [None, author]

        if not guild.chunked:
            async with channel.typing():
                try:
                    await Bloxlink.request_offline_members(guild)
                except:
                    pass

        update_roles    = update_what in ("roles", "both")
        update_nickname = update_what in ("nickname", "both")

        t = (len(guild.members), Comparable(guild.id), guild, author, response, trello_binds_list, trello_board, update_roles, update_nickname, guild_data)

        heapq.heappush(self.queue, t)

        if not self.queue_loop_running:
            loop.create_task(self.start_queue())
            await response.send("Your server will be scanned momentarily.")
        else:
            await response.send("Your server is now queued for full-member updating.")
