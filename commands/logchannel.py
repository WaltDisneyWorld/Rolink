from discord import Embed

events = {
	"verify": "fired after a member verifies",
	"error": "fired after a permission error occurs",
	"setup": "fired if a setting changes"
}
events_choices = list(events.keys())
events_text = "```fix\n" + "\n".join([x + " ➜ " + y for x,y in events.items()]) + "```"

async def setup(**kwargs):
	command = kwargs.get("command")
	r = kwargs.get("r")

	@command(name="logchannel", category="Administration", permissions={
		"raw": "manage_guild"
	}, arguments=[
		{
			"prompt": "Would you like to ``view``, ``delete``, or ``add`` a new event?",
			"type": "choice",
			"choices": ["view", "delete", "add"],
			"name": "choice"
		}
	], aliases=["logchannels"])
	async def logchannel(message, response, args):
		"""subscribes to Bloxlink events"""

		author = message.author
		guild = message.guild

		choice = args.parsed_args["choice"]

		guild_data = await r.table("guilds").get(str(guild.id)).run() or {}
		log_channels = guild_data.get("logChannels", {})

		if choice == "view":

			embed = Embed(title="Bloxlink Events")
			embed.set_author(name=guild.name, icon_url=guild.icon_url)

			if log_channels:
				for x,y in log_channels.items():
					if y:
						log_channel = guild.get_channel(int(y))
						log_channel_mention = log_channel and log_channel.mention or "N/A (deleted)"
						embed.add_field(name=f"Event: {x}", value=f"Channel: {log_channel_mention}")
				if embed.fields:
					await response.send(embed=embed)
				else:
					await response.error("No results to show.")
			else:
				await response.error("No results to show.")

		elif choice == "add":
			parsed_args, is_cancelled = await args.call_prompt([
				{
					"prompt": "Which event would you like to register? Choices: " + events_text,
					"type": "choice",
					"choices": events_choices,
					"name": "event_name"
				},
				{
					"prompt": "Which channel would you like to use for this event?",
					"type": "channel",
					"name": "channel"
				}
			])
			if not is_cancelled:
				log_channels[parsed_args["event_name"]] = str(parsed_args["channel"].id)

				await r.table("guilds").insert({
					"id": str(guild.id),
					"logChannels": log_channels
				}, conflict="update").run()

				await response.success(f'Saved! {parsed_args["channel"].mention} will now ' \
					 f'be used for **{parsed_args["event_name"]}** events.')
		elif choice == "delete":
			parsed_args, is_cancelled = await args.call_prompt([
				{
					"prompt": "Which event would you like to DELETE? Choices: " + events_text,
					"type": "choice",
					"choices": events_choices,
					"name": "event_name"
				}
			])
			if not is_cancelled:
				if log_channels.get(parsed_args["event_name"]):
					log_channels[parsed_args["event_name"]] = None
					await r.table("guilds").insert({
						"id": str(guild.id),
						"logChannels": log_channels
					}, conflict="update").run()
					await response.success("Successfully **deleted** this event.")
				else:
					await response.error("You don't have this event registered.")
