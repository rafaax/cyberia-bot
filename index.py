import json
import inspect
import discord
import yt_dlp

from discord import Interaction, app_commands, Intents, Client

# Leitura e salvamento do token no config.json
try:
    with open("storage/config.json") as f:
        config = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    config = {}

token = config.get("token", None)
if not token:
    token = input('Cole seu token do Discord aqui: ').strip()
    config["token"] = token
    with open("storage/config.json", "w") as f:
        json.dump(config, f, indent=2)
else:
    print(
        f"\n--- Detected token in ./config.json"
        " (saved from a previous run). Using stored token. ---\n"
    )

# --------- BOT SETUP ---------
# Escolha intents adequadas ao funcionamento dos comandos de música e slash
intents = Intents.default()
intents.message_content = True  # Necessário para responder mensagens (caso use comandos normais futuramente)
intents.guilds = True
intents.voice_states = True

GUILD_ID = 949532298007679008  # Coloque aqui o ID do seu servidor

class Cyberia(Client):
    def __init__(self, *, intents: Intents):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self) -> None:
        await self.tree.sync(guild=discord.Object(GUILD_ID)) # Sincroniza apenas neste servidor

client = Cyberia(intents=intents)

# ----------- COMANDOS -----------

@client.tree.command(description='Envia um Olá', guild=discord.Object(GUILD_ID))
async def hello(interaction: Interaction):
    print(f"> {interaction.user} used the command 'hello'.")
    await interaction.response.send_message(f"Olá **{interaction.user}** :flushed:.")

@client.tree.command(description='Envia um "Joke"', guild=discord.Object(GUILD_ID))
async def haha(interaction: Interaction):
    print(f"> {interaction.user} used the command 'haha'.")
    await interaction.response.send_message(':joy:')

@client.event
async def on_ready():
    print(f"cyberia bot online {client.user}")

@client.tree.command(description='Tocar música do YouTube', guild=discord.Object(GUILD_ID))
@app_commands.describe(url='URL do vídeo do YouTube')
async def tocar(interaction: Interaction, url: str):
    print(f"> {interaction.user} usou o comando de 'tocar'.")
    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.response.send_message("Você precisa estar em um canal de voz!", ephemeral=True)
        return

    voice_channel = interaction.user.voice.channel

    if interaction.guild.voice_client:
        vc = interaction.guild.voice_client
        if vc.channel != voice_channel:
            await vc.move_to(voice_channel)
    else:
        vc = await voice_channel.connect()

    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'extract_flat': False,
        'nocache': True,
        'cookiefile': 'storage/cookies.txt',
    }

    await interaction.response.send_message(f'🔎 Baixando áudio... aguarde!', ephemeral=True)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            url2 = info['url']

        source = await discord.FFmpegOpusAudio.from_probe(url2)
        if vc.is_playing():
            vc.stop()
        vc.play(source)
        await interaction.followup.send(f"🎶 Tocando agora: **{info.get('title', 'música')}**", ephemeral=False)
    except Exception as e:
        await interaction.followup.send(f"Ocorreu um erro ao tentar tocar a música: {str(e)}", ephemeral=True)

@client.tree.command(description='Sai do canal de voz', guild=discord.Object(GUILD_ID))
async def sair(interaction: Interaction):
    if interaction.guild.voice_client:
        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message("Saí do canal de voz!")
    else:
        await interaction.response.send_message("Não estou em nenhum canal de voz.")

# --------- RODA O BOT ----------
client.run(token)