import json
import inspect
import discord
import yt_dlp
from dotenv import load_dotenv
import os
from discord import Interaction, app_commands, Intents, Client


# --------- CONFIGURAÇÕES ---------

load_dotenv()

token = os.getenv("DISCORD_TOKEN_TEST")
bot_version = os.getenv("BOT_VERSION")

if not token:
    raise ValueError("Token do Discord não encontrado. Defina DISCORD_TOKEN no arquivo .env.")


# --------- BOT SETUP ---------

intents = Intents.default() # Permissões padrão
intents.message_content = True # Permissão para ler o conteúdo das mensagens
intents.guilds = True # Permissão para ler os dados do servidor
intents.voice_states = True # Permissão para ler os dados dos canais de voz

GUILD_ID = 949532298007679008  # id do cyberia server

class Cyberia(Client):
    def __init__(self, *, intents: Intents):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self) -> None:
        await self.tree.sync(guild=discord.Object(GUILD_ID)) # Sincroniza apenas neste servidor

client = Cyberia(intents=intents)

# ----------- COMANDOS -----------

@client.event
async def on_ready():  # Evento chamado quando o bot está pronto
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
        'cookiefile': 'cookies/yt.txt',
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

@client.tree.command(description='Lista os comandos disponíveis', guild=discord.Object(GUILD_ID))
async def help(interaction: Interaction):
    commands = [
        {
            "name": command.name,
            "description": command.description,
            "parameters": [param for param in command.parameters]  # Lista nomes dos parâmetros
        }
        for command in client.tree.get_commands(guild=interaction.guild)
    ]

    embed = discord.Embed(title="Comandos disponíveis", color=0x00ff00)
    if not commands:
        embed.description = "Nenhum comando encontrado."
    else:
        for command in commands:
            params = ", ".join([param.name for param in command["parameters"]]) if command["parameters"] else "Sem parâmetros"
            embed.add_field(
                name=f"/{command['name']}",
                value=f"{command['description']}\n**Parâmetros:** {params}",
                inline=False
            )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@client.tree.command(description='Mostra informações sobre o bot', guild=discord.Object(GUILD_ID))
async def info(interaction: Interaction):
    embed = discord.Embed(title="Informações do Bot", color=0x00ff00)
    embed.add_field(name="Nome", value=client.user.name, inline=True)
    embed.add_field(name="ID", value=client.user.id, inline=True)
    embed.add_field(name="Versão", value=bot_version, inline=True)
    embed.set_thumbnail(url=client.user.avatar.url)
    await interaction.response.send_message(embed=embed, ephemeral=True)

client.run(token)