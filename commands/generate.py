from discord import File
from io import BytesIO

from resources.module import get_module
generate_code = get_module("utils", attrs=["generate_code"])


async def check_number(message, number, previous_args):
	return number.isdigit(), "You must pass a number"

async def setup(**kwargs):
	command = kwargs.get("command")

	@command(name="generate", category="Developer", arguments=[
		{
			"prompt": "What prefix would you like to use?",
			"type": "string",
			"name": "prefix"
		},
		{
			"prompt": "How long should the codes last for?",
			"type": "string",
			"check": check_number,
			"name": "duration"
		},
		{
			"prompt": "How many codes would you like to generate?",
			"type": "string",
			"check": check_number,
			"name": "num_codes"
		},
		{
			"prompt": "How many people can redeem the code?",
			"type": "string",
			"check": check_number,
			"name": "max_uses",
			"optional": True
		}
	])
	async def generate(message, response, args, prefix):
		"""generates Bloxlink Premium codes"""

		author = message.author

		codes = []

		num_codes = int(args.parsed_args.get("num_codes", 1))

		for _ in range(num_codes):
			code = await generate_code(
				args.parsed_args["prefix"],
				int(args.parsed_args["duration"]),
				int(args.parsed_args.get("max_uses", 1))
			)
			if code:
				codes.append(code)

		codes = list(set(codes))

		real_amount = len(codes)

		failed_count = 0

		if real_amount != num_codes:
			failed_count = abs(num_codes - real_amount)


		selly_buffer = BytesIO()
		selly_buffer.write(bytes(",\n".join(codes), "utf-8"))

		codes_buffer = BytesIO()
		codes_buffer.write(bytes("\n".join(codes), "utf-8"))

		await author.send(f'Here {real_amount > 1 and "are" or "is" } **{real_amount}** code{real_amount > 1 and "s" or ""}',
			files=[
				File(selly_buffer.getvalue(), filename="selly_codes.txt"),
				File(codes_buffer.getvalue(), filename="codes.txt")
			]
		)

		await author.send(
			("```\n" + "\n".join(codes)[0:1950] + "\n```")
		)

		if failed_count:
			await response.error(f'**{failed_count}** codes failed to deliver.')

		await message.add_reaction("✅")
