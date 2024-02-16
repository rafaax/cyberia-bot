import discord
import random

intents = discord.Intents.default()
intents.message_content = True


class Cyberia(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.synced = False
        self.added = False

    async def on_ready(self):
        await self.wait_until_ready()
        if not self.synced:
            await tree.sync(guild=discord.Object(
                '949532298007679008'))
            self.synced = True
        if not self.added:
            self.added = True
        print(f"Say hi to {self.user}!")


client = Cyberia()
tree = discord.app_commands.CommandTree(client)


@tree.command(description='teste por rafaax', guild=discord.Object('949532298007679008'))
async def greet(interaction: discord.Interaction):
    await interaction.response.send_message('...')


@tree.command(description='rola um dado', guild=discord.Object('949532298007679008'))
async def d20(interaction: discord.Interaction):
    roll = random.randint(1, 20)
    await interaction.response.send_message(roll)


@client.event
async def on_message(message):
    # This checks if the message is not from the bot itself. If it is, it'll ignore the message.
    if message.author == client.user:
        return

    # From here, you can add all the rules and the behaviour of the bot.
    # In this case, the bot checks if the content of the message is "Hello!" and send a message if it's true.
    if message.content == 'teste':
        print(message)
        await message.channel.send("...")
        return


# add the token of your bot
client.run('MTIwNzg0NzY1ODEyODAxOTUwNg.GcAotA.guBxC6hkfRLT-94rtdHj8KjFoDiV8Pclyygla4')
