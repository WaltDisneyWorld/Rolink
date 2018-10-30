from discord import Embed

class Paginate:
	def __init__(self, **kwargs):
		self.message = kwargs.get("message")
		self.embed = kwargs.get("embed")
		self.smart_fields = kwargs.get("smart_fields")
		self.client = kwargs.get("client")

		self.page = 0

	async def start(self):
		# 1024 characters per field, 2000ish total

		fields = self.embed.fields
		pages = [] # [ [...] ]

		current_page = {}
		current_page_num = 0

		"""
		ctr = 0
		while ctr < len(self.embed.fields):
			remaining = 2000
			page = []
			#print("parsing field", flush=True)

			while remaining >= 0:
				#print("assessing field characters", flush=True)
				#print(remaining, flush=True)
				field = self.embed.fields[ctr]

				if (len(field.name) + len(field.value)) < remaining:
					#print(field.value.encode("utf-8"), flush=True)
					#print("1", flush=True)

					if len(field.value) < 1024:
						#print("2", flush=True)
						page.append([field.name, field.value])
						remaining -= len(field.name) + len(field.value)
						ctr += 1
						

					else:
						# split into multiple pages
						#print("3", flush=True)
						field_amount = (len(field.value) + len(field.name)) // 1000
						#print(len(field.value) + len(field.name), flush=True)
						#print(field_amount, flush=True)
						sliced = 0

						for i in range(1, field_amount + 2):
							print("4", flush=True)
							pages.append([[field.name, field.value[sliced:i*1000]]])
							print(field.value[sliced:i*1000].encode("utf-8"), flush=True)
							
							sliced += 1000
						ctr += 1
						break

				else:
					# split into multiple pages
					page_amount = (len(field.value) + len(field.name)) // 2000
					sliced = 0
					#print("5", flush=True)

					for i in range(1, page_amount + 2):
						print("6", flush=True)
						pages.append([[field.name, field.value[sliced:i*2000]]])
						sliced += 2000

					break

			if page:
				#print("7", flush=True)
				pages.append(page)
			else:
				ctr += 1

			#print("incrementing", flush=True)
			#ctr += 1 # could cause missing data if the field is perfect, we increment it above^

		#print(str(pages).encode('utf-8'), flush=True)
		#print(len(pages), flush=True)
		"""

		# iterate through fields, get the first 1000 characters, look ahead and get the other 1000
		# if left over, add them to the beginning of the next field

		ctr = 0

		"""
		while ctr < len(self.embed.fields):
			print("iterating through ctr", flush=True)
			remaining = 2000

			# temp variables
			sliced = 0
			current_page = []
			tries = 1
			while remaining >= 0:
				print("iterating through remaining", flush=True)
				if len(self.embed.fields) < ctr + 1:
					print("breaking", flush=True)
					break
				field = self.embed.fields[ctr]
				
				field_amount = (len(field.value) + len(field.name)) // 1000
				page = []
				#print(len(field.value) + len(field.name), flush=True)
				#print(field_amount, flush=True)
				sliced = 0

				for i in range(1, field_amount + 2):
					print("4", flush=True)
					text = field.value[sliced:i*1000]
					if len(text)  > remaining:
						self.embed.fields[ctr+1][0:]
					page.append([field.name, field.value[sliced:i*1000]])
					field.value = field.value[]
					#print(field.value[sliced:i*1000].encode("utf-8"), flush=True)
					
					sliced += 1000
				
				to_slice_amount = sliced + remaining
				if to_slice_amount > 1000:
					to_slice_amount = 1000
				sliced_text = field.value[sliced:to_slice_amount*tries]
				
				print(sliced, field.value.index(sliced_text), flush=True)
				#field.value = field.value[field.value.index(sliced_text):] # remove text from field
				field.value = field.value.replace(sliced_text, "")
				print(field.value.encode("utf-8"), flush=True)
				tries += 1
				#field.value = field.value.replace(sliced_text, "")
				sliced = sliced + len(sliced_text)
				remaining -= len(field.value)
				if sliced_text:
					current_page.append([field.name, sliced_text])
				
				if not field.value:
					# no more to slice
					print("no more field", flush=True)
					ctr += 1
					sliced = 0
					tries = 1
					
			
			pages.append(current_page)

		"""

		# iterate through fields, get the first 1000 characters, look ahead and get the other 1000
		# if left over, add them to the beginning of the next field
		while ctr < len(self.embed.fields):
			remaining = 2000
			sliced = 0
			current_page = []
			print("ctr iter", flush=True)
			while remaining >= 0:
				print("remaining iter", ctr, flush=True)
				if len(self.embed.fields) < ctr + 1:
					print("breaking", flush=True)
					break
				field = self.embed.fields[ctr]

				to_slice_amount = sliced + remaining
				print("to_slice_amount", to_slice_amount, flush=True)

				if to_slice_amount > 1000:
					to_slice_amount = 1000

				sliced_text = field.value[sliced:sliced+to_slice_amount]
				print("sliced_text", sliced_text.encode("utf-8"), flush=True)
				remaining -= len(sliced_text)
				print("remaining", remaining, flush=True)
				field.value = field.value.replace(sliced_text, "")

				sliced += len(sliced_text)

				if sliced_text:
					current_page.append([field.name, sliced_text])

				if not field.value:
					print("no more value", flush=True)
					ctr += 1
					sliced = 0
					break
			pages.append(current_page)



		print(str(pages).encode("utf-8"), flush=True)
		for page in pages:
			#print(str(page).encode("utf-8"), flush=True)
			#print(page[0].encode("utf-8"), flush=True)
			#await self.message.channel.send(embed=Embed(name=page[0], value=page[1]))
			embed = Embed()
			for field in page:
				embed.add_field(name=field[0], value=field[1], inline=False)
			
			await self.message.channel.send(embed=embed)


def new_module():
	return Paginate
