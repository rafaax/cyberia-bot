import discord
from discord import Interaction, app_commands
from discord.ext import commands
import yt_dlp
import asyncio
import config # Importa as configurações

class MusicCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name='tocar', description='Tocar música do YouTube')
    @app_commands.describe(url='URL do vídeo do YouTube')
    @app_commands.guilds(discord.Object(id=config.GUILD_ID_INT))
    async def tocar(self, interaction: Interaction, url: str):
        """Toca uma música do YouTube no canal de voz do usuário."""
        print(f"> {interaction.user} usou o comando 'tocar'.")

        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("Você precisa estar em um canal de voz!", ephemeral=True)
            return

        voice_channel = interaction.user.voice.channel
        guild = interaction.guild

        # Conectando ou movendo para o canal de voz
        if guild.voice_client:
            vc = guild.voice_client
            if vc.channel != voice_channel:
                try:
                    await vc.move_to(voice_channel)
                except asyncio.TimeoutError:
                     await interaction.followup.send("Não consegui me mover para o seu canal a tempo.", ephemeral=True)
                     return
        else:
            try:
                vc = await voice_channel.connect(timeout=30.0) # Timeout de 30s
            except asyncio.TimeoutError:
                 await interaction.response.send_message("Não consegui me conectar ao seu canal a tempo.", ephemeral=True)
                 return
            except discord.ClientException as e:
                 await interaction.response.send_message(f"Erro ao conectar: {e}", ephemeral=True)
                 return

        # Responde primeiro para evitar timeout da interação
        await interaction.response.send_message("🔎 Processando seu pedido...", ephemeral=False)

        try:
            # Usando o contexto `with` para garantir que o ydl seja fechado
            with yt_dlp.YoutubeDL(config.YDL_OPTS) as ydl:
                await interaction.edit_original_response(content="📥 Baixando informações do áudio...")
                # Executa o bloqueante ydl.extract_info em um executor para não bloquear o bot
                info = await self.bot.loop.run_in_executor(None, lambda: ydl.extract_info(url, download=False))
                audio_url = info['url']
                title = info.get('title', 'música desconhecida')

            # Cria a fonte de áudio
            # Usar before_options pode ajudar com estabilidade em alguns casos
            ffmpeg_options = {
                'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                'options': '-vn'
            }
            source = await discord.FFmpegOpusAudio.from_probe(audio_url, **ffmpeg_options)

            if vc.is_playing() or vc.is_paused():
                vc.stop() # Para a música atual antes de tocar a nova

            vc.play(source, after=lambda e: print(f'Player error: {e}') if e else None)

            await interaction.edit_original_response(content=f"🎶 Tocando agora: **{title}**")

        except yt_dlp.utils.DownloadError as e:
             await interaction.edit_original_response(content=f"❌ Erro ao baixar: {e}. Verifique a URL ou tente novamente.")
        except Exception as e:
            print(f"Erro inesperado no comando 'tocar': {e}")
            await interaction.edit_original_response(content=f" Ocorreu um erro inesperado: {str(e)}")


    @app_commands.command(name='pausar', description='Pausa a música atual')
    @app_commands.guilds(discord.Object(id=config.GUILD_ID_INT))
    async def pausar(self, interaction: Interaction):
        """Pausa a música que está tocando."""
        vc = interaction.guild.voice_client
        if vc and vc.is_playing():
            vc.pause()
            print(f"O usuário {interaction.user} pausou a música.")
            await interaction.response.send_message("⏸️ Música pausada!")
        elif vc and vc.is_paused():
             await interaction.response.send_message("A música já está pausada.", ephemeral=True)
        else:
            await interaction.response.send_message("Não estou tocando nada no momento.", ephemeral=True)

    @app_commands.command(name='retomar', description='Retoma a música pausada')
    @app_commands.guilds(discord.Object(id=config.GUILD_ID_INT))
    async def retomar(self, interaction: Interaction):
        """Retoma a música que estava pausada."""
        vc = interaction.guild.voice_client
        if vc and vc.is_paused():
            vc.resume()
            print(f"O usuário {interaction.user} retomou a música.")
            await interaction.response.send_message("▶️ Música retomada!")
        elif vc and vc.is_playing():
             await interaction.response.send_message("A música já está tocando.", ephemeral=True)
        else:
            await interaction.response.send_message("Não há música pausada para retomar.", ephemeral=True)

    @app_commands.command(name='parar', description='Para a música e limpa a fila (se houver)')
    @app_commands.guilds(discord.Object(id=config.GUILD_ID_INT))
    async def parar(self, interaction: Interaction):
        """Para a reprodução de música atual."""
        vc = interaction.guild.voice_client
        if vc and (vc.is_playing() or vc.is_paused()):
            vc.stop()
            print(f"O usuário {interaction.user} parou a música.")
            await interaction.response.send_message("⏹️ Música parada.")
            # Se você implementar uma fila, limpe-a aqui também
        else:
            await interaction.response.send_message("Não estou tocando nada no momento.", ephemeral=True)

    @app_commands.command(name='sair', description='Faz o bot sair do canal de voz')
    @app_commands.guilds(discord.Object(id=config.GUILD_ID_INT))
    async def sair(self, interaction: Interaction):
        """Desconecta o bot do canal de voz."""
        vc = interaction.guild.voice_client
        if vc:
            await vc.disconnect(force=True) # force=True garante a desconexão
            await interaction.response.send_message("👋 Saí do canal de voz!")
        else:
            await interaction.response.send_message("Não estou em nenhum canal de voz.", ephemeral=True)

# Função essencial para carregar o Cog no bot principal
async def setup(bot: commands.Bot):
    await bot.add_cog(MusicCog(bot), guilds=[discord.Object(id=config.GUILD_ID_INT)])