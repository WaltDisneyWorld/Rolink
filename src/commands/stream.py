from resources.structures.Bloxlink import Bloxlink # pylint: disable=import-error, no-name-in-module
from resources.constants import IS_DOCKER, OWNER, ARROW, PLAYING_STATUS, STREAMERS # pylint: disable=import-error, no-name-in-module
from config import REACTIONS, PREFIX  # pylint: disable=import-error, no-name-in-module
from discord import Embed, Streaming, Game, Status



broadcast = Bloxlink.get_module("ipc", attrs="broadcast")



@Bloxlink.command
class StreamCommand(Bloxlink.Module):
    """start Twitch streaming"""

    def __init__(self):
        self.aliases = ["streaming"]
        self.hidden = True

        self._streaming = False

    async def __main__(self, CommandArgs):
        response = CommandArgs.response
        author = CommandArgs.message.author

        if author.id in STREAMERS:
            if not self._streaming:
                if author.id == OWNER:
                    parsed_args = await CommandArgs.prompt([
                        {
                            "prompt": "Please type in a stream name.",
                            "name": "stream_name"
                        },
                        {
                            "prompt": "Twitch URL?",
                            "name": "stream_url"
                        }
                    ])

                    stream_name = parsed_args["stream_name"]
                    stream_url = parsed_args["stream_url"]
                else:
                    stream_name = "LIVE ON TWITCH!"
                    stream_url = "https://www.twitch.tv/blox_link"


            if IS_DOCKER:
                if not self._streaming:
                    clusters = await broadcast(None, status=stream_name, stream_url=stream_url, presence_type="streaming", type="PLAYING_STATUS")
                    self._streaming = True
                else:
                    clusters = await broadcast(None, presence_type="normal", type="PLAYING_STATUS")
                    self._streaming = False

                embed = Embed(title="Cluster Results")
                results = []

                for cluster_id, cluster_result in clusters.items():
                    if cluster_result in ("cluster offline", "cluster timeout"):
                        results.append(f"**{cluster_id}** {ARROW} timed-out")
                    else:
                        results.append(f"**{cluster_id}** {ARROW} {REACTIONS['DONE_ANIMATED']}")


                embed.description = "\n".join(results)

                await response.send(embed=embed)

            else:
                if not self._streaming:
                    await Bloxlink.change_presence(activity=Streaming(name=stream_name, url=stream_url))
                    self._streaming = True

                    await response.success("Now streaming!")
                else:
                    await Bloxlink.change_presence(status=Status.online, activity=Game(PLAYING_STATUS.format(prefix=PREFIX)))
                    self._streaming = False

                    await response.success("Stream ended.")
