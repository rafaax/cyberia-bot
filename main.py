import discord
import random
from Cyberia import Cyberia

# This will load the permissions the bot has been granted in the previous configuration
intents = discord.Intents.default()
intents.message_content = True


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
