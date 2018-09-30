import io
import textwrap
from contextlib import redirect_stdout
from discord import Embed
from discord.errors import Forbidden
import resources.modules.roblox as roblox

# https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/admin.py


def cleanup_code(content):
	"""Automatically removes code blocks from the code."""
	# remove ```py\n```
	if content.startswith('```') and content.endswith('```'):
		return '\n'.join(content.split('\n')[1:-1])

	# remove `foo`
	return content.strip('` \n')

def get_syntax_error(e):
	if e.text is None:
		return f'```py\n{e.__class__.__name__}: {e}\n```'
	return f'```py\n{e.text}{"^":>{e.offset}}\n{e.__class__.__name__}: {e}```'



async def setup(**kwargs):
	command = kwargs.get("command")
	client = kwargs.get("client")
	r = kwargs.get("r")

	@command(name="eval", category="Developer", alias=["code"], permissions={
		"owner_only": True
	}, arguments=[
		{
			"prompt": "Please specify the code.",
			"type": "string",
			"name": "code"
		}
	])
	async def sudo(message, response, args, prefix):
		"""executes Python code"""

		channel = message.channel

		env = {
			"client": client,
			"channel": channel,
			"author": message.author,
			"guild": message.guild,
			"message": message,
			"r": r,
			"response": response,
			"roblox": roblox
		}

		env.update(globals())

		code = args.parsed_args["code"]
		code = cleanup_code(code)

		stdout = io.StringIO()

		to_compile = f'async def func():\n{textwrap.indent(code, "  ")}'

		try:
			exec(to_compile, env)
		except Exception as e:
				error_embed = Embed(
					title="Evaluation Error",
					description=f"```js\n{e.__class__.__name__}: {e}```",
					color=0xE74C3C
				)
				await response.send(embed=error_embed)

		func = env.get("func")

		ret = None
		value = None

		if func:
			try:
				with redirect_stdout(stdout):
					ret = await func()
			except Exception as e:
				error_embed = Embed(
					title="Evaluation Error",
					description=f"```js\n{e.__class__.__name__}: {e}```",
					color=0xE74C3C
				)
				await response.send(embed=error_embed)
			else:
				value = stdout.getvalue()
				try:
					await message.add_reaction('\u2705')
				except:
					pass

			# success_embed = Embed(title="Code Evaluation", color=0x2ECC71)

			if ret is None:
				if value:
					# success_embed.description = value
					success_embed = Embed(
						title="Evaluation Result",
						description=f"```py\n{value[0:2000]}```",
						color=0x36393E
					)
					try:
						await channel.send(embed=success_embed)
					except Forbidden:
						await response.send(value[0:2000])
			else:
				success_embed = Embed(
					title="Evaluation Result",
					description=f"```py\n{value}{ret[0:2000]}```",
					color=0x36393E
				)
				try:
					await channel.send(embed=success_embed)
				except Forbidden:
					await response.send(f'{value}{ret}'[0:2000])
