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
        self.bot = bot
        self.queues = {} # Guarda as filas de músicas por guild
        self.current_song = {} # Guarda a música atual tocando
        self.inactivity_timers = {} # Guarda as asyncio.Tasks de verificação
        self.last_text_channel = {} # Guarda o último canal de texto usado

    # --- Funções de Controle de Inatividade ---

    async def _disconnect_inactive(self, guild_id: int):
        """Tarefa que desconecta o bot após um período de inatividade."""
        try:
            await asyncio.sleep(120) # 2 min 

            guild = self.bot.get_guild(guild_id) # Verifica se a guild ainda existe
            if not guild:
                self._cleanup_guild_state(guild_id) # Limpa estado se guild não existe
                return

            vc = guild.voice_client # Pega o VoiceClient da guild
            
            if vc and vc.is_connected() and not vc.is_playing() and not vc.is_paused() and not self.queues.get(guild_id): # REVERIFICA as condições de inatividade ANTES de desconectar
                print(f"[{guild_id}] Desconectando devido a inatividade.")

                last_channel = self.last_text_channel.get(guild_id) # Pega o último canal conhecido

                if last_channel: # Se o canal ainda existe, tenta enviar a mensagem de desconexão
                    try:
                        await last_channel.send(embed=discord.Embed(
                            description="👋 Desconectando após 2 minutos de inatividade.",
                            color=Color.orange()
                        ))
                    except discord.HTTPException:
                        print(f"[{guild_id}] Falha ao enviar msg de desconexão por inatividade.")

                await vc.disconnect(force=True) # Desconecta o bot do canal de voz
                self._cleanup_guild_state(guild_id) # Limpa tudo após desconectar


            else: # Se não está mais inativo, apenas remove o timer (a verificação falhou)
                print(f"[{guild_id}] Verificação de inatividade concluída, mas bot não está mais inativo.")
                self.inactivity_timers.pop(guild_id, None) # Remove a referência da tarefa concluída

        except asyncio.CancelledError: # A tarefa foi cancelada, o que é normal se houver nova atividade
            print(f"[{guild_id}] Verificação de inatividade cancelada.")
        except Exception as e:
            print(f"[{guild_id}] Erro inesperado na tarefa _disconnect_inactive: {e}")
            self._cleanup_guild_state(guild_id) # Limpa em caso de erro inesperado


    def _schedule_inactivity_check(self, guild_id: int):
        """Agenda a tarefa de verificação de inatividade para uma guild."""
        
        self._cancel_inactivity_check(guild_id) # Cancela qualquer timer anterior existente para esta guild

        print(f"[{guild_id}] Agendando verificação de inatividade (2 minutos).")
        
        self.inactivity_timers[guild_id] = self.bot.loop.create_task( # Cria e armazena a nova tarefa
            self._disconnect_inactive(guild_id)
        )

    def _cancel_inactivity_check(self, guild_id: int):
        """Cancela a tarefa de verificação de inatividade, se existir."""

        if guild_id in self.inactivity_timers:
            task = self.inactivity_timers.pop(guild_id, None) # remove primeiro para evitar race condition
            if task and not task.done():
                print(f"[{guild_id}] Cancelando verificação de inatividade.")
                task.cancel()


    def _cleanup_guild_state(self, guild_id: int):
        """Limpa todas as informações de estado para uma guild."""

        print(f"[{guild_id}] Limpando estado completo da guild (fila, música, timer, canal).")

        if guild_id in self.queues: # Se a guild tem uma fila
            self.queues[guild_id].clear() # Limpa a queue

        self.current_song.pop(guild_id, None) # Limpa a música atual
        self._cancel_inactivity_check(guild_id) # Garante que o timer seja cancelado
        self.last_text_channel.pop(guild_id, None) # Limpa o último canal conhecido



    # --- Funções Principais de Reprodução ---
    async def _play_next(self, guild_id: int):
        """Função interna chamada para tocar a próxima música na fila."""

        
        guild = self.bot.get_guild(guild_id)  # Pega a guild pelo ID

        if not guild: # Se a guild não existe, limpa o estado e sai
            self._cleanup_guild_state(guild_id) # Limpa o estado da guild
            return # morre aqui

        
        self._cancel_inactivity_check(guild_id) # tira o estado de inativdade, pois houve atividade

        if guild_id in self.queues and self.queues[guild_id]:
            song_info = self.queues[guild_id].popleft() # Pega a próxima música da fila
            self.current_song[guild_id] = song_info # Atualiza a música atual tocando
            
            if song_info.get('channel'): # Se o canal de texto foi definido, atualiza o último canal conhecido
                self.last_text_channel[guild_id] = song_info['channel'] 

            vc = guild.voice_client # Pega o VoiceClient da guild

            if not vc or not vc.is_connected():
                print(f"Erro: VoiceClient não encontrado ou desconectado na guild {guild_id} ao iniciar _play_next.") 
                self._cleanup_guild_state(guild_id) # Limpa estado se desconectado
                return # morre aqui

            print(f"[{guild_id}] Tocando próxima: {song_info['title']}")

            try:
                source = await discord.FFmpegOpusAudio.from_probe(song_info['source_url'], **FFMPEG_OPTIONS) # Cria o source de áudio
                vc.play(source, after=lambda e: self.bot.loop.create_task(self._handle_after_play(e, guild_id))) # Toca a música e define o callback para quando terminar

                if song_info.get('channel'): # Se o canal de texto foi definido, envia a mensagem de "tocando agora"
                    try:
                        await song_info['channel'].send(embed=discord.Embed(
                            description=f"🎶 Tocando: **{song_info['title']}** (Pedido por: {song_info['requester'].mention})",
                            color=Color.purple()
                        ))
                        self.last_text_channel[guild_id] = song_info['channel'] # Garante atualização
                    except discord.HTTPException:
                        print(f"[{guild_id}] Falha ao enviar mensagem 'Tocando agora'.")

            except Exception as e:
                print(f"Erro ao tentar tocar '{song_info['title']}' na guild {guild_id}: {e}")
                if song_info.get('channel'):
                    try:
                        await song_info['channel'].send(f"❌ Erro ao tocar **{song_info['title']}**: {e}")
                    except discord.HTTPException:
                        pass
                
                self.bot.loop.create_task(self._handle_after_play(e, guild_id)) # Mesmo com erro, chama handle_after_play para limpar e tentar a próxima na esperança 
        
        else:
            # Fila vazia, agenda a verificação de inatividade

            print(f"[{guild_id}] Fila vazia após tentativa de _play_next.")

            vc = guild.voice_client # Pega o VoiceClient da guild
            if vc and vc.is_connected(): # Só agenda se ainda estiver conectado no canal 
                self._schedule_inactivity_check(guild_id)
            else:
                print(f"[{guild_id}] VoiceClient desconectado ou não encontrado. Limpando estado.")
                self._cleanup_guild_state(guild_id)  # Limpa o estado da guild, pois não há mais conexão com o canal de voz

    async def _handle_after_play(self, error, guild_id):
        """Callback chamado após uma música terminar ou dar erro."""
        
        finished_song_info = self.current_song.pop(guild_id, None) # Pega E REMOVE a música atual

        if error: # Se houve erro na reprodução
            print(f"Erro durante a reprodução na guild {guild_id}: {error}")
            if finished_song_info and finished_song_info.get('channel'):
                notify_channel = finished_song_info['channel']
                self.last_text_channel[guild_id] = notify_channel # Atualiza último canal
                try:
                    error_embed = discord.Embed(
                        title="❌ Erro de Reprodução",
                        description=f"Ocorreu um erro ao tentar tocar:\n**{finished_song_info.get('title', 'Música desconhecida')}**",
                        color=discord.Color.red(),
                        timestamp=discord.utils.utcnow()
                    )
                    error_embed.add_field(name="Detalhes", value=f"`{error}`", inline=False)
                    await notify_channel.send(embed=error_embed)
                except discord.HTTPException:
                    print(f"[{guild_id}] Falha ao enviar mensagem de erro para o canal {notify_channel.id}")
                except Exception as e:
                    print(f"[{guild_id}] Erro inesperado ao enviar mensagem de erro: {e}")
        
        
        else: # Se não houve erro, apenas informa que a música terminou
            
            title = finished_song_info.get('title', 'Desconhecida') if finished_song_info else 'Desconhecida'
            print(f"[{guild_id}] Música '{title}' concluída.")
            
            if finished_song_info and finished_song_info.get('channel'): 
                # Atualiza last_text_channel se a música tocou com sucesso
                self.last_text_channel[guild_id] = finished_song_info.get('channel')

        
        await self._play_next(guild_id) # Tenta tocar a próxima. _play_next agendará inatividade se a fila estiver vazia.

    
    
    
    
    
    
    
    
    
    
    
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
        # Atualiza o último canal de texto conhecido
        self.last_text_channel[guild_id] = interaction.channel

        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("Você precisa estar em um canal de voz!", ephemeral=True)
            return
        voice_channel = interaction.user.voice.channel

        if guild_id not in self.queues:
            self.queues[guild_id] = deque()

        vc: discord.VoiceClient = guild.voice_client
        if not vc or not vc.is_connected():
            try:
                # Cancela timer ANTES de tentar conectar
                self._cancel_inactivity_check(guild_id)
                vc = await voice_channel.connect(timeout=30.0)
            # ... (tratamento de erro de conexão) ...
            except asyncio.TimeoutError: # Restante do try/except da conexão/movimento
                 await interaction.response.send_message("Não consegui me conectar ao seu canal a tempo.", ephemeral=True)
                 return
            except discord.ClientException as e:
                 await interaction.response.send_message(f"Erro ao conectar: {e}", ephemeral=True)
                 return
        elif vc.channel != voice_channel:
            try:
                 # Cancela timer ANTES de tentar mover
                 self._cancel_inactivity_check(guild_id)
                 await vc.move_to(voice_channel)
            except asyncio.TimeoutError:
                 await interaction.response.send_message("Não consegui me mover para o seu canal a tempo.", ephemeral=True)
                 return

        await interaction.response.send_message(f"🔎 Processando seu pedido para `{url}`...")

        try:
            # ... (lógica ytdl para extrair info - sem mudanças) ...
            with yt_dlp.YoutubeDL(config.YDL_OPTS) as ydl: # Extrai info da URL
                await interaction.edit_original_response(content=f"📥 Baixando informações de `{url}`...")
                info = await self.bot.loop.run_in_executor(None, lambda: ydl.extract_info(url, download=False))

            entries_to_add = [] # Lista para guardar as músicas a serem adicionadas
            playlist_title = None # Guarda o título da playlist

            if info and '_type' in info and info['_type'] == 'playlist': # Verifica se é playlist
                playlist_title = info.get('title', 'Playlist')
                await interaction.edit_original_response(content=f"📥 Playlist '{playlist_title}' encontrada! Adicionando músicas...")
                max_playlist_songs = 50 # limite
                count = 0
                for entry in info.get('entries', []): # itera sobre as entradas da playlist
                    if count >= max_playlist_songs:
                        print(f"[{guild_id}] Limite de {max_playlist_songs} músicas da playlist atingido.")
                        break
                    if entry and entry.get('url'): # se a entrada é válida e tem url
                        song_data = {
                            'title': entry.get('title', 'Título desconhecido'),
                            'source_url': entry['url'],
                            'requester': interaction.user,
                            'channel': interaction.channel,
                            'original_url': entry.get('webpage_url', url)
                        }
                        entries_to_add.append(song_data)
                        count += 1
                    else:
                        title = entry.get('title', 'entrada inválida') if entry else 'entrada nula'
                        print(f"[{guild_id}] Música da playlist inválida ou sem URL de áudio: {title}")
                if not entries_to_add:
                    await interaction.edit_original_response(content=f"❌ Nenhuma música válida encontrada na playlist `{playlist_title or url}`.")
                    # Agenda inatividade se nada foi adicionado e nada está tocando
                    if not vc.is_playing() and not vc.is_paused():
                        self._schedule_inactivity_check(guild_id)
                    return
            elif info and 'url' in info: # Verifica se é vídeo único
                song_data = {
                    'title': info.get('title', 'Título desconhecido'),
                    'source_url': info['url'],
                    'requester': interaction.user,
                    'channel': interaction.channel,
                    'original_url': info.get('webpage_url', url)
                }
                entries_to_add.append(song_data)
            else: # Caso inesperado ou erro na extração
                errmsg = "❌ Não consegui processar esta URL."
                if not info: errmsg += " (Falha ao obter informações)"
                elif 'url' not in info: errmsg += " (Formato de áudio não encontrado)"
                await interaction.edit_original_response(content=errmsg)
                # Agenda inatividade se falhou e nada está tocando
                if not vc.is_playing() and not vc.is_paused():
                    self._schedule_inactivity_check(guild_id)
                return


            # Adiciona à fila
            if entries_to_add:
                 # Cancela timer pois houve atividade
                 self._cancel_inactivity_check(guild_id)
                 for song in entries_to_add:
                      self.queues[guild_id].append(song)
            else:
                 # Se por algum motivo entries_to_add ficou vazia após processar, não faz nada
                 # (O código anterior já teria retornado ou agendado inatividade)
                 return


            num_added = len(entries_to_add)
            if num_added > 1:
                queue_msg = f"✅ Adicionadas **{num_added}** músicas da playlist '{playlist_title}' à fila!"
            elif num_added == 1 :
                queue_msg = f"✅ Adicionado à fila: **{entries_to_add[0]['title']}**"
            # Se num_added == 0, não chega aqui


            # Inicia a reprodução se NADA estiver tocando
            if not vc.is_playing() and not vc.is_paused():
                print(f"[{guild_id}] Nada tocando, iniciando reprodução com a(s) nova(s) música(s).")
                # Edita a msg original ANTES de chamar _play_next
                await interaction.edit_original_response(content=f"▶️ Iniciando reprodução com: **{entries_to_add[0]['title']}**")
                await self._play_next(guild_id) # _play_next vai enviar a msg "Tocando"
            else:
                # Se já estiver tocando, apenas informa que foi adicionado
                print(f"[{guild_id}] Adicionando à fila. Música atual ou pausada existe.")
                await interaction.edit_original_response(content=queue_msg)


        except yt_dlp.utils.DownloadError as e:
            await interaction.edit_original_response(content=f"❌ Erro ao processar a URL: `{e}`. Verifique o link ou se ele é suportado.")
            # Agenda inatividade se deu erro e nada está tocando
            if vc and not vc.is_playing() and not vc.is_paused():
                self._schedule_inactivity_check(guild_id)
        except Exception as e:
            print(f"Erro inesperado no comando 'tocar' [{guild_id}]: {e}")
            await interaction.edit_original_response(content=f" Ocorreu um erro inesperado: {str(e)}")
            # Agenda inatividade se deu erro e nada está tocando
            if vc and not vc.is_playing() and not vc.is_paused():
                self._schedule_inactivity_check(guild_id)


    @app_commands.command(name='pular', description='Pula a música atual')
    @app_commands.guilds(discord.Object(id=config.GUILD_ID_INT))
    async def pular(self, interaction: Interaction):
        """Pula para a próxima música na fila."""
        guild = interaction.guild
        if not guild: return
        guild_id = guild.id
        self.last_text_channel[guild_id] = interaction.channel # Atualiza canal

        vc = guild.voice_client
        # Verifica se está tocando OU pausado para poder pular
        if not vc or (not vc.is_playing() and not vc.is_paused()):
            await interaction.response.send_message("Não estou tocando ou pausado para pular.", ephemeral=True)
            return

        if interaction.user.voice is None or interaction.user.voice.channel != vc.channel:
            await interaction.response.send_message("Você precisa estar no mesmo canal de voz para pular.", ephemeral=True)
            return

        current = self.current_song.get(guild_id) # Pega a música atual ANTES de parar
        title = f"**{current['title']}**" if current else "a música atual"

        print(f"[{guild_id}] {interaction.user} pulou a música.")
        await interaction.response.send_message(f"⏭️ Pulando {title}...")
    
        vc.stop() # Parar a música atual acionará _handle_after_play


    @app_commands.command(name='retomar', description='Retoma a música pausada')
    @app_commands.guilds(discord.Object(id=config.GUILD_ID_INT))
    async def retomar(self, interaction: Interaction):
        """Retoma a música que estava pausada."""
        guild = interaction.guild

        if not guild:  # Verifica se o comando foi chamado em um servidor
            return
        

        guild_id = guild.id # Pega o ID da guild

        self.last_text_channel[guild_id] = interaction.channel # Atualiza canal que o comando foi chamado

        vc = interaction.guild.voice_client # Pega o VoiceClient da guild

        if vc and vc.is_paused(): # Verifica se o bot está pausado
            self._cancel_inactivity_check(guild_id) # Cancela timer pois retomar é uma atividade válida
            vc.resume() # Retoma a música pausada

            print(f"> {interaction.user} retomou a música.")
            await interaction.response.send_message("▶️ Música retomada!")

        elif vc and vc.is_playing(): # Verifica se já está tocando
            await interaction.response.send_message("A música já está tocando.", ephemeral=True)
        else: # Caso não esteja tocando ou pausado
            await interaction.response.send_message("Não há música pausada para retomar.", ephemeral=True)


    @app_commands.command(name='parar', description='Para a música e limpa a fila')
    @app_commands.guilds(discord.Object(id=config.GUILD_ID_INT))
    async def parar(self, interaction: Interaction):
        """Para a reprodução de música atual e limpa a fila."""

        guild = interaction.guild # Pega a guild do comando

        if not guild: # Verifica se o comando foi chamado em um servidor
            return 
        
        guild_id = guild.id # Pega o ID da guild

        self.last_text_channel[guild_id] = interaction.channel # Atualiza canal onde o comando foi chamado

        vc = guild.voice_client # Pega o VoiceClient da guild

        was_active = vc and (vc.is_playing() or vc.is_paused()) # Verifica se estava tocando ou pausado

        print(f"> {interaction.user} usou /parar.")
        
        self._cleanup_guild_state(guild_id) # Limpa tudo, incluindo timer antes de parar a música

        if was_active: # Se estava tocando ou pausado
            vc.stop() # Para a reprodução (não vai mais chamar _handle_after_play pois o estado está limpo)
            await interaction.response.send_message("⏹️ Música parada e fila limpa.")
        else:
            await interaction.response.send_message("Não estava tocando nada, mas limpei a fila.", ephemeral=True)


    @app_commands.command(name='sair', description='Faz o bot sair do canal de voz e limpa a fila')
    @app_commands.guilds(discord.Object(id=config.GUILD_ID_INT))
    async def sair(self, interaction: Interaction):
        """Desconecta o bot do canal de voz e limpa a fila."""
        
        guild = interaction.guild # Pega a guild do comando

        if not guild: # Verifica se o comando foi chamado em um servidor
            return 
        
        guild_id = guild.id # Pega o ID da guild

        self.last_text_channel[guild_id] = interaction.channel # Atualiza canal onde o comando foi chamado

        vc = guild.voice_client # Pega o VoiceClient da guild
        
        was_connected = vc and vc.is_connected() # Verifica se o bot está conectado ao canal de voz

        print(f"> {interaction.user} usou /sair.")
        
        self._cleanup_guild_state(guild_id) # Limpa tudo, incluindo timer antes de desconectar

        if was_connected: # Se estava conectado
            await vc.disconnect(force=True) # Desconecta
            await interaction.response.send_message("👋 Saí do canal de voz e limpei a fila!")
        else:
            await interaction.response.send_message("Não estava em um canal de voz.", ephemeral=True)




    @app_commands.command(name='fila', description='Mostra a fila de músicas atual')
    @app_commands.guilds(discord.Object(id=config.GUILD_ID_INT))
    async def fila(self, interaction: Interaction):
        """Exibe a fila de músicas."""
        
        guild = interaction.guild # Pega a guild do comando
        
        if not guild: # Verifica se o comando foi chamado em um servidor
            return 
        

        guild_id = guild.id # Pega o ID da guild

        self.last_text_channel[guild_id] = interaction.channel # Atualiza canal onde o comando foi chamado

        queue = self.queues.get(guild_id) # Pega a fila de músicas da guild
        current = self.current_song.get(guild_id) # Pega a música atual tocando na guild

        embed = Embed(title="Fila de Músicas", color=Color.purple()) 

        if current: # Se houver uma música tocando

            requester_mention = current['requester'].mention if current.get('requester') else 'Desconhecido' # Se houver 'requester', pega o .mention; caso contrário, usa 'Desconhecido'

            embed.add_field(
                name="▶️ Tocando Agora",
                value=f"[{current['title']}]({current.get('original_url', '#')})\n(Pedido por: {requester_mention})",
                inline=False
            )
        else: # Se não houver música tocando
            vc = guild.voice_client # Pega o VoiceClient da guild

            if vc and vc.is_connected() and vc.is_paused(): # Se o bot está conectado e pausado
                embed.add_field(name="⏸️ Pausado", value="Nenhuma música ativa, mas o bot está pausado.", inline=False) 
            else:
                embed.add_field(name="▶️ Tocando Agora", value="Nada", inline=False)

        if queue: # Se houver músicas na fila
            queue_list = [] # Lista para guardar as músicas da fila
            max_display = 10 # Limite de músicas a serem exibidas na fila (10 por padrão)

            for i, song in enumerate(list(queue)[:max_display]): # Limita a exibição a max_display músicas
                if song.get('requester'):
                    requester_mention = song['requester'].mention
                else:
                    requester_mention = 'Desconhecido'

                queue_list.append(f"{i+1}. [{song['title']}]({song.get('original_url', '#')}) (por: {requester_mention})") # Adiciona a música à lista formatada

            if queue_list:
                embed.add_field( # Adiciona a lista de músicas à embed
                    name=f" Fila ({len(queue)} música{'s' if len(queue) > 1 else ''})", 
                    value="\n".join(queue_list), 
                    inline=False
                )  

            if len(queue) > max_display: # Se a fila tem mais músicas do que o limite de exibição
                embed.set_footer(text=f"... e mais {len(queue) - max_display} música(s)")
        else: # Se não houver músicas na fila
            embed.add_field(name=" Fila", value="A fila está vazia!", inline=False)

        await interaction.response.send_message(embed=embed) # Envia a embed com a fila de músicas

    @app_commands.command(name='pausar', description='Pausa a música atual')
    @app_commands.guilds(discord.Object(id=config.GUILD_ID_INT))
    async def pausar(self, interaction: Interaction):
        """Pausa a música que está tocando."""

        guild = interaction.guild # Pega a guild do comando

        if not guild: # Verifica se o comando foi chamado em um servidor
            return
        
        guild_id = guild.id # Pega o ID da guild
        self.last_text_channel[guild_id] = interaction.channel # Atualiza canal onde o comando foi chamado

        vc = interaction.guild.voice_client # Pega o VoiceClient da guild

        if vc and vc.is_playing(): # Verifica se o bot está tocando música /// Pausar NÃO deve cancelar o timer de inatividade se ele estiver rodando
            
            vc.pause() # Pausa a música atual

            print(f"> {interaction.user} pausou a música.")

            await interaction.response.send_message("⏸️ Música pausada!")
        elif vc and vc.is_paused():
            await interaction.response.send_message("A música já está pausada.", ephemeral=True)
        else:
            await interaction.response.send_message("Não estou tocando nada no momento.", ephemeral=True)


    # --- Listener para Limpeza/Inatividade Automática ---
    @commands.Cog.listener()
    # O QUE É O  @commands.Cog.listener()?

    # É um decorador usado para criar funções que "escutam" (recebem) eventos do Discord, dentro de um Cog.
    # Um Cog é uma forma de organizar comandos e eventos em módulos no bot do Discord.
    # COMO FUNCIONA?

    # Quando você coloca @commands.Cog.listener() antes de um método em uma classe que herda de commands.Cog, você está dizendo que esse método é um ouvinte de evento.
    # O nome do método precisa ser o mesmo nome de um evento do Discord.py (ex: on_message, on_member_join, etc.).
    # Sempre que esse evento acontecer no Discord, o método correspondente será chamado.

    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        # 1. Bot foi desconectado?
        if member.id == self.bot.user.id:
            guild = member.guild # Pega a guild do membro

            if before.channel is not None and after.channel is None: # Verifica se o bot estava em um canal e agora não está mais
                print(f"[{guild.id}] Bot foi desconectado do canal de voz (evento). Limpando estado.")
                self._cleanup_guild_state(guild.id) # Chama a função de limpeza

        # 2. Bot ficou sozinho no canal? (Alguém saiu/moveu e não é o bot)
        elif before.channel is not None and member.id != self.bot.user.id:
            guild = before.channel.guild # Pega a guild do canal de voz
            vc = guild.voice_client # Pega o VoiceClient da guild

            # Verifica se o bot está NO MESMO canal que a pessoa saiu E se só sobrou o bot
            if vc and vc.channel == before.channel and len(before.channel.members) == 1 and before.channel.members[0].id == self.bot.user.id:
                print(f"[{guild.id}] Bot ficou sozinho no canal {before.channel.name}. Agendando verificação de inatividade.")
                self._schedule_inactivity_check(guild.id) # Agenda a desconexão como se a fila tivesse acabado POIS NÃO TEM NINGUEM NO CANAL

        # 3. Alguém entrou no canal onde o bot estava sozinho e inativo?
        elif after.channel is not None and member.id != self.bot.user.id: 
            guild = after.channel.guild # Pega a guild do canal de voz
            vc = guild.voice_client # Pega o VoiceClient da guild
            # Verifica se o bot está nesse canal, se antes só tinha ele e se agora tem mais gente
            if vc and vc.channel == after.channel and len(after.channel.members) > 1 and len(before.channel.members) == 1 if before.channel == after.channel else True :
                # Verifica se havia um timer de inatividade agendado
                if guild.id in self.inactivity_timers:
                    print(f"[{guild.id}] Usuário entrou no canal onde o bot estava inativo. Cancelando timer.")
                    self._cancel_inactivity_check(guild.id)


async def setup(bot: commands.Bot):
    await bot.add_cog(MusicCog(bot), guilds=[discord.Object(id=config.GUILD_ID_INT)])