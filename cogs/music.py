# cogs/music.py
import discord
from discord import Interaction, app_commands, Embed, Color
from discord.ext import commands
import yt_dlp
import asyncio
from collections import deque
import config 

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

class MusicCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot # Bot instance
        self.queues = {} # dict de filas por guild_id
        self.current_song = {} # dict de músicas atuais por guild_id

    # --- Função Interna para Tocar a Próxima ---
    async def _play_next(self, guild_id: int):
        """Função interna chamada para tocar a próxima música na fila."""
        if guild_id in self.queues and self.queues[guild_id]:
            # Pega a próxima música da fila
            song_info = self.queues[guild_id].popleft()
            self.current_song[guild_id] = song_info # Atualiza a música atual

            guild = self.bot.get_guild(guild_id)
            if not guild:
                 print(f"Erro: Guild {guild_id} não encontrada ao tentar tocar a próxima.")
                 self.current_song.pop(guild_id, None)
                 if guild_id in self.queues: self.queues[guild_id].clear()
                 return

            vc = guild.voice_client
            if not vc or not vc.is_connected():
                print(f"Erro: VoiceClient não encontrado ou desconectado na guild {guild_id}.")
                self.current_song.pop(guild_id, None)
                if guild_id in self.queues: self.queues[guild_id].clear()
                return

            print(f"[{guild_id}] Tocando próxima: {song_info['title']}")
            try:
                source = await discord.FFmpegOpusAudio.from_probe(song_info['source_url'], **FFMPEG_OPTIONS)
                # A função after_play é crucial para a continuidade da fila
                vc.play(source, after=lambda e: self.bot.loop.create_task(self._handle_after_play(e, guild_id)))

                # Envia mensagem no canal onde a música foi pedida
                if song_info.get('channel'):
                    try:
                         await song_info['channel'].send(embed=discord.Embed(
                             description=f"🎶 Tocando agora: **{song_info['title']}** (Pedido por: {song_info['requester'].mention})",
                             color=Color.blue()
                         ))
                    except discord.HTTPException:
                         print(f"[{guild_id}] Falha ao enviar mensagem 'Tocando agora'.") # Pode falhar se o canal foi deletado

            except Exception as e:
                print(f"Erro ao tentar tocar '{song_info['title']}' na guild {guild_id}: {e}")
                self.current_song.pop(guild_id, None) # Remove a música atual se falhar
                # Tenta tocar a próxima da fila se esta falhar
                self.bot.loop.create_task(self._play_next(guild_id))
                # Informa no canal, se possível
                if song_info.get('channel'):
                     try:
                         await song_info['channel'].send(f"❌ Erro ao tocar **{song_info['title']}**: {e}")
                     except discord.HTTPException:
                         pass # Ignora se não conseguir enviar msg
        else:
            # Fila vazia, limpa o estado atual
            print(f"[{guild_id}] Fila vazia. Limpando música atual.")
            self.current_song.pop(guild_id, None)
            # Opcional: Desconectar após um tempo de inatividade? (implementação futura)

    async def _handle_after_play(self, error, guild_id):
        """Callback chamado após uma música terminar ou dar erro."""
        
        
        finished_song_info = self.current_song.get(guild_id)  # Pega as informações da música que acabou de tocar/falhar ANTES de limpar

        if error: # Erro durante a reprodução
            print(f"Erro durante a reprodução na guild {guild_id}: {error}")
            
            # Tenta notificar o canal original onde a música foi pedida
            if finished_song_info and finished_song_info.get('channel'):
                notify_channel = finished_song_info['channel']
                try:
                    # Cria um Embed para a mensagem de erro
                    error_embed = discord.Embed( 
                        title="❌ Erro de Reprodução", # Título do Embed
                        description=f"Ocorreu um erro ao tentar tocar:\n**{finished_song_info.get('title', 'Música desconhecida')}**", # Título da música
                        color=discord.Color.red(), # Cor vermelha para erro
                        timestamp=discord.utils.utcnow() # Adiciona timestamp
                    )

                    error_embed.add_field(name="Erro", value=str(error), inline=False) # Adiciona o erro como campo

                    await notify_channel.send(embed=error_embed)
                    
                except discord.HTTPException: # Falha ao enviar a mensagem (ex: permissões, canal deletado)
                    print(f"[{guild_id}] Falha ao enviar mensagem de erro para o canal {notify_channel.id}")
                except Exception as e: # Captura outros erros inesperados ao tentar enviar a mensagem
                    print(f"[{guild_id}] Erro inesperado ao enviar mensagem de erro: {e}")            
        else:
            print(f"[{guild_id}] Música '{finished_song_info.get('title', 'Desconhecida') if finished_song_info else 'Desconhecida'}' concluída.")

        self.current_song.pop(guild_id, None) # Limpa a referência da música que acabou ANTES de tentar tocar a próxima, isso evita que a música antiga permaneça como 'atual' se _play_next falhar ou se não houver próxima música.
        await self._play_next(guild_id)  # Tenta tocar a próxima música da fila, independentemente de erro ou sucesso anterior. (A lógica de _play_next lida com filas vazias.)


    # --- Comandos ---
    @app_commands.command(name='tocar', description='Toca uma música do YouTube ou adiciona à fila')
    @app_commands.describe(url='URL do vídeo ou playlist do YouTube')
    @app_commands.guilds(discord.Object(id=config.GUILD_ID_INT))
    async def tocar(self, interaction: Interaction, url: str):
        """Toca uma música ou adiciona à fila."""
        guild = interaction.guild
        if not guild:
             await interaction.response.send_message("Este comando só pode ser usado em um servidor.", ephemeral=True)
             return
        guild_id = guild.id

        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("Você precisa estar em um canal de voz!", ephemeral=True)
            return

        voice_channel = interaction.user.voice.channel

        # Garante que existe uma fila para esta guild
        if guild_id not in self.queues:
            self.queues[guild_id] = deque()

        # Conectando ou movendo para o canal de voz
        vc: discord.VoiceClient = guild.voice_client # Type hint para clareza
        if not vc or not vc.is_connected():
            try:
                vc = await voice_channel.connect(timeout=30.0)
            except asyncio.TimeoutError:
                await interaction.response.send_message("Não consegui me conectar ao seu canal a tempo.", ephemeral=True)
                return
            except discord.ClientException as e:
                await interaction.response.send_message(f"Erro ao conectar: {e}", ephemeral=True)
                return
        elif vc.channel != voice_channel:
            try:
                await vc.move_to(voice_channel)
            except asyncio.TimeoutError:
                await interaction.response.send_message("Não consegui me mover para o seu canal a tempo.", ephemeral=True)
                return

        # Responde à interação imediatamente para evitar timeout
        await interaction.response.send_message(f"🔎 Processando seu pedido para `{url}`...")

        try:
            # Usando contexto with para yt_dlp
            with yt_dlp.YoutubeDL(config.YDL_OPTS) as ydl:
                await interaction.edit_original_response(content=f"📥 Baixando informações de `{url}`...")
                # Executa a extração de informações em um executor para não bloquear
                info = await self.bot.loop.run_in_executor(None, lambda: ydl.extract_info(url, download=False))

            # --- Lidando com Playlists (Simples: Adiciona todas as entradas encontradas) ---
            entries_to_add = []
            if '_type' in info and info['_type'] == 'playlist':
                 await interaction.edit_original_response(content=f"📥 Playlist encontrada! Adicionando músicas...")
                 # Limita o número de músicas de uma playlist para evitar abuso (opcional)
                 max_playlist_songs = 50
                 count = 0
                 for entry in info.get('entries', []):
                      if count >= max_playlist_songs:
                           print(f"[{guild_id}] Limite de {max_playlist_songs} músicas da playlist atingido.")
                           break
                      # Verifica se temos URL de áudio (pode faltar em alguns casos)
                      if entry.get('url'):
                           song_data = {
                               'title': entry.get('title', 'Título desconhecido'),
                               'source_url': entry['url'],
                               'requester': interaction.user,
                               'channel': interaction.channel, # Guarda o canal para msgs futuras
                               'original_url': entry.get('webpage_url', url) # URL original para /fila
                           }
                           entries_to_add.append(song_data)
                           count += 1
                      else:
                           print(f"[{guild_id}] Música da playlist sem URL de áudio: {entry.get('title')}")
                 if not entries_to_add:
                      await interaction.edit_original_response(content=f"❌ Nenhuma música válida encontrada na playlist `{info.get('title', url)}`.")
                      return

            # --- Lidando com Vídeo Único ---
            elif 'url' in info:
                song_data = {
                    'title': info.get('title', 'Título desconhecido'),
                    'source_url': info['url'],
                    'requester': interaction.user,
                    'channel': interaction.channel,
                    'original_url': info.get('webpage_url', url)
                }
                entries_to_add.append(song_data)

            # --- Caso inesperado ---
            else:
                 await interaction.edit_original_response(content="❌ Não consegui encontrar um formato de áudio válido para esta URL.")
                 return

            # Adiciona as músicas encontradas à fila
            for song in entries_to_add:
                 self.queues[guild_id].append(song)

            num_added = len(entries_to_add)
            if num_added > 1:
                 queue_msg = f"✅ Adicionadas **{num_added}** músicas à fila!"
            else:
                 queue_msg = f"✅ Adicionado à fila: **{entries_to_add[0]['title']}**"

            # Se NADA estiver tocando, inicia a reprodução
            if not vc.is_playing() and not vc.is_paused():
                print(f"[{guild_id}] Nada tocando, iniciando reprodução.")
                # Edita a mensagem original para 'Tocando agora' em vez de 'Adicionado'
                await interaction.edit_original_response(content=f"🎶 Tocando agora: **{entries_to_add[0]['title']}** (Pedido por: {interaction.user.mention})")
                # Remove a primeira música da lista 'entries_to_add' porque _play_next a pegará da fila
                #await self._play_next(guild_id)
                # Não precisa remover da entries_to_add, _play_next pega da self.queues
                # Chamar _play_next aqui garante que a lógica de tocar seja centralizada
                await self._play_next(guild_id)

            # Se já estiver tocando, apenas informa que foi adicionado
            else:
                print(f"[{guild_id}] Adicionando à fila. Música atual: {self.current_song.get(guild_id, {}).get('title', 'Nenhuma')}")
                await interaction.edit_original_response(content=queue_msg)


        except yt_dlp.utils.DownloadError as e:
            await interaction.edit_original_response(content=f"❌ Erro ao processar a URL: `{e}`. Verifique o link ou se ele é suportado.")
        except Exception as e:
            print(f"Erro inesperado no comando 'tocar' [{guild_id}]: {e}")
            await interaction.edit_original_response(content=f" Ocorreu um erro inesperado: {str(e)}")


    @app_commands.command(name='fila', description='Mostra a fila de músicas atual')
    @app_commands.guilds(discord.Object(id=config.GUILD_ID_INT))
    async def fila(self, interaction: Interaction):
        """Exibe a fila de músicas."""
        guild = interaction.guild
        if not guild: return
        guild_id = guild.id

        queue = self.queues.get(guild_id)
        current = self.current_song.get(guild_id)

        embed = Embed(title="Fila de Músicas", color=Color.purple())

        if current:
            embed.add_field(
                name="▶️ Tocando Agora",
                value=f"[{current['title']}]({current.get('original_url', '#')})\n(Pedido por: {current['requester'].mention})",
                inline=False
            )
        else:
            embed.add_field(name="▶️ Tocando Agora", value="Nada", inline=False)

        if queue:
            queue_list = []
            # Mostra as próximas X músicas (ex: 10)
            max_display = 10
            for i, song in enumerate(list(queue)[:max_display]):
                 queue_list.append(f"{i+1}. [{song['title']}]({song.get('original_url', '#')}) (Pedido por: {song['requester'].mention})")

            if queue_list:
                 embed.add_field(name=" Músicas na Fila", value="\n".join(queue_list), inline=False)
            if len(queue) > max_display:
                 embed.set_footer(text=f"... e mais {len(queue) - max_display} música(s)")
        else:
            embed.add_field(name=" Músicas na Fila", value="A fila está vazia!", inline=False)

        await interaction.response.send_message(embed=embed)


    @app_commands.command(name='pular', description='Pula a música atual')
    @app_commands.guilds(discord.Object(id=config.GUILD_ID_INT))
    async def pular(self, interaction: Interaction):
        """Pula para a próxima música na fila."""
        guild = interaction.guild
        if not guild: return
        guild_id = guild.id

        vc = guild.voice_client
        if not vc or not vc.is_playing():
            await interaction.response.send_message("Não estou tocando nada para pular.", ephemeral=True)
            return

        
        if interaction.user.voice is None or interaction.user.voice.channel != vc.channel: # Verificar se o usuário está no mesmo canal de voz
            await interaction.response.send_message("Você precisa estar no mesmo canal de voz para pular a música.", ephemeral=True)
            return

        current = self.current_song.get(guild_id)
        title = f"**{current['title']}**" if current else "a música atual"

        print(f"[{guild_id}] {interaction.user} pulou a música.")
        await interaction.response.send_message(f"⏭️ Pulando {title}...")

        
        vc.stop() # parar a música atual acionará o callback _handle_after_play, que tocará a próxima

    @app_commands.command(name='pausar', description='Pausa a música atual')
    @app_commands.guilds(discord.Object(id=config.GUILD_ID_INT))
    async def pausar(self, interaction: Interaction):
        """Pausa a música que está tocando."""
        vc = interaction.guild.voice_client
        if vc and vc.is_playing():
            vc.pause()
            print(f"> {interaction.user} pausou a música.")
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
            print(f"> {interaction.user} retomou a música.")
            await interaction.response.send_message("▶️ Música retomada!")
        elif vc and vc.is_playing():
            await interaction.response.send_message("A música já está tocando.", ephemeral=True)
        else:
            await interaction.response.send_message("Não há música pausada para retomar.", ephemeral=True)

    @app_commands.command(name='parar', description='Para a música e limpa a fila')
    @app_commands.guilds(discord.Object(id=config.GUILD_ID_INT))
    async def parar(self, interaction: Interaction):
        """Para a reprodução de música atual e limpa a fila."""
        guild = interaction.guild
        if not guild: return
        guild_id = guild.id

        vc = guild.voice_client
        if vc and (vc.is_playing() or vc.is_paused()):
            print(f"> {interaction.user} parou a música e limpou a fila.")
            # Limpa a fila específica desta guild
            if guild_id in self.queues:
                self.queues[guild_id].clear()
            # Limpa a música atual
            self.current_song.pop(guild_id, None)
            # Para a reprodução (isso também chamará o _handle_after_play, mas a fila estará vazia)
            vc.stop()
            await interaction.response.send_message("⏹️ Música parada e fila limpa.")
        else:
            # Limpa a fila mesmo se não estiver tocando (garantia)
            if guild_id in self.queues:
                 self.queues[guild_id].clear()
            self.current_song.pop(guild_id, None)
            await interaction.response.send_message("Não estou tocando nada, mas limpei a fila por segurança.", ephemeral=True)


    @app_commands.command(name='sair', description='Faz o bot sair do canal de voz e limpa a fila')
    @app_commands.guilds(discord.Object(id=config.GUILD_ID_INT))
    async def sair(self, interaction: Interaction):
        """Desconecta o bot do canal de voz e limpa a fila."""
        guild = interaction.guild
        if not guild: return
        guild_id = guild.id

        vc = guild.voice_client
        if vc:
            print(f"> {interaction.user} fez o bot sair e limpou a fila.")
            # Limpa a fila e a música atual ANTES de desconectar
            if guild_id in self.queues:
                self.queues[guild_id].clear()
            self.current_song.pop(guild_id, None)
            # Para a música (importante para liberar recursos) e desconecta
            await vc.disconnect(force=True)
            await interaction.response.send_message("👋 Saí do canal de voz e limpei a fila!")
        else:
            # Limpa a fila mesmo se não estiver conectado (garantia)
            if guild_id in self.queues:
                self.queues[guild_id].clear()
            self.current_song.pop(guild_id, None)
            await interaction.response.send_message("Não estou em nenhum canal de voz, mas limpei a fila por segurança.", ephemeral=True)

    # Limpar a fila se o bot for desconectado manualmente ou movido
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        # Verifica se o membro que mudou de estado é o próprio bot
        if member.id == self.bot.user.id:
            guild_id = member.guild.id
            # Se o bot foi desconectado (after.channel é None)
            if before.channel is not None and after.channel is None: 
                print(f"[{guild_id}] Bot foi desconectado do canal de voz. Limpando fila.")
                if guild_id in self.queues:
                    self.queues[guild_id].clear()
                self.current_song.pop(guild_id, None)
            # Se o bot ficou sozinho no canal (pode ser implementado checando len(before.channel.members))
            # Poderia iniciar um timer para sair e limpar a fila


async def setup(bot: commands.Bot):
    await bot.add_cog(MusicCog(bot), guilds=[discord.Object(id=config.GUILD_ID_INT)])