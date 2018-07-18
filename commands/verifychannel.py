from discord.utils import find
from discord.errors import Forbidden
from resources.modules.utils import post_event


async def setup(**kwargs):
	command = kwargs.get("command")
	r = kwargs.get("r")

	@command(name="verifychannel", category="Administration", permissions={"raw": "manage_guild"})
	async def verifychannel(message, response, args, prefix):
		"""creates a verification channel. All messages will occasionally be deleted from this channel"""

		guild = message.guild
		author = message.author

		errors = []

		try:
			category = find(lambda c: c.name == "Verification", guild.categories) or \
				await guild.create_category("Verification")
		except Forbidden:
			errors.append("Unable to create ``Verification`` category. Please ensure I have the " \
				"the ``Manage Channels`` permission.")

		if category:

			try:
				verify_channel = find(lambda c: c.name == "verify", category.channels) or \
					await guild.create_text_channel("verify", category=category)
			except Forbidden:
				errors.append("Unable to create verification channel. Please ensure I have the " \
					"the ``Manage Channels`` permission.")		

			try:
				instructions = find(lambda c: c.name == "verify-instructions", category.channels) or \
					await guild.create_text_channel("verify-instructions", category=category)
			except Forbidden:
				errors.append("Unable to create instructions channel. Please ensure I have the " \
					"the ``Manage Channels`` permission.")


			if verify_channel and instructions:
				await instructions.send("This server uses Bloxlink to manage Roblox verification. In "\
				"order to unlock all the features of this server, you'll need to verify your Roblox account " \
				f"with your Discord account!\n\nTo do this, run ``{prefix}verify`` in {verify_channel.mention} and follow the instructions.")

				try:
					for role in guild.roles:
							await instructions.set_permissions(role, send_messages=False, read_messages=True)

				except Forbidden:
					errors.append("Unable to add role(s) to instructions channel. Please ensure I have the " \
						"``Manage Channels`` and ``Manage Roles`` permission.")		

			try:
				if verify_channel:
					for target, overwrite in verify_channel.overwrites:
						await verify_channel.set_permissions(target, overwrite=None)

					for role in guild.roles:
						await verify_channel.set_permissions(role, send_messages=True, read_messages=True)

			except Forbidden:
				errors.append("Unable to set channel permissions. Please ensure I have the " \
					"``Manage Channels`` permission.")

			if errors:
				for error in errors:
					success = await post_event(
						"error",
						error,
						guild=guild,
						color=0xE74C3C
					)

				if not success:
					await response.error(f'Numberous permission errors occured: ``{", ".join(errors)}``\n' \
						"Pro-tip: set an errors channel with ``!logchannel`` to suppress these error messages.")
			else:

				await r.table("guilds").insert({
					"id": str(guild.id),
					"verifyChannel": str(verify_channel.id)
				}, conflict="update").run()

				await response.success(f"All done! Your new verification channel is {verify_channel.mention} and " \
					"is now managed by Bloxlink.")





