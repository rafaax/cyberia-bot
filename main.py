# main.py
import discord
from discord.ext import commands
import os
import asyncio
import config # Importa as configurações

# --- BOT SETUP ---
# Usamos commands.Bot agora, que é uma subclasse de Client com mais funcionalidades (incluindo Cogs)
intents = discord.Intents.default()
intents.message_content = True # Necessário se você planeja ler mensagens no futuro
intents.guilds = True
intents.voice_states = True # Essencial para comandos de voz

# Você pode manter sua classe customizada se precisar adicionar mais lógica a ela,
# mas para carregar Cogs, herdar de commands.Bot é mais direto.
# Se você *realmente* precisa da classe Cyberia, faça-a herdar de commands.Bot:
# class Cyberia(commands.Bot):
#     def __init__(self, *, intents: discord.Intents):
#         super().__init__(command_prefix="!", intents=intents) # command_prefix é obrigatório, mas não usado para slash commands
#         # Não precisa mais do self.tree = app_commands.CommandTree(self)
#         # commands.Bot já tem uma árvore de comandos em self.tree
#
#     async def setup_hook(self) -> None:
#         # É aqui que carregamos as extensões (Cogs) e sincronizamos
#         print("Executando setup_hook...")
#         cogs_loaded = []
#         cogs_failed = []
#         for filename in os.listdir('./cogs'):
#             if filename.endswith('.py') and not filename.startswith('__'):
#                 extension = f'cogs.{filename[:-3]}'
#                 try:
#                     await self.load_extension(extension)
#                     print(f' > Cog {extension} carregado com sucesso.')
#                     cogs_loaded.append(extension)
#                 except Exception as e:
#                     print(f' ! Falha ao carregar cog {extension}: {e}')
#                     cogs_failed.append(extension)
#
#         print("-" * 20)
#         print(f"Cogs carregados: {len(cogs_loaded)}")
#         print(f"Cogs com falha: {len(cogs_failed)}")
#         if cogs_failed:
#             print(f"Falharam: {', '.join(cogs_failed)}")
#         print("-" * 20)
#
#         # Sincroniza os comandos APENAS para o servidor especificado
#         # Remova o if se quiser sincronizar globalmente (leva mais tempo)
#         if config.GUILD_ID_INT:
#              guild_obj = discord.Object(id=config.GUILD_ID_INT)
#              self.tree.copy_global_to(guild=guild_obj)
#              await self.tree.sync(guild=guild_obj)
#              print(f"Comandos sincronizados para o servidor ID: {config.GUILD_ID_INT}")
#         else:
#              print("GUILD_ID não definido, comandos não sincronizados automaticamente.")
#              print("Use um comando de sincronização manual ou defina GUILD_ID.")
#
#     async def on_ready(self):
#         print(f'--- Bot {self.user} está online! ---')
#         print(f'Versão: {config.BOT_VERSION}')
#         print(f'ID do Bot: {self.user.id}')
#         print(f'Servidor de Teste ID: {config.GUILD_ID_INT}')
#         print('------------------------------------')
#
# # Instancia o bot
# bot = Cyberia(intents=intents)

# -- Alternativa mais simples se não precisar de uma classe Bot customizada --
bot = commands.Bot(command_prefix="!", intents=intents) # command_prefix é obrigatório, mas não usado para slash

@bot.event
async def on_ready():
    print(f'--- Bot {bot.user} está online! ---')
    print(f'Versão: {config.BOT_VERSION}')
    if bot.user: # Checagem para mypy/pylint
        print(f'ID do Bot: {bot.user.id}')
    print(f'Servidor de Teste ID: {config.GUILD_ID_INT}')
    print('------------------------------------')

# Função assíncrona para carregar cogs e iniciar o bot
async def main():
    async with bot: # Context manager para lidar com setup e teardown
        # Carregar Cogs
        print("Carregando Cogs...")
        cogs_loaded = []
        cogs_failed = []
        for filename in os.listdir('./cogs'):
             if filename.endswith('.py') and not filename.startswith('__'):
                 extension = f'cogs.{filename[:-3]}'
                 try:
                     await bot.load_extension(extension)
                     print(f' > Cog {extension} carregado com sucesso.')
                     cogs_loaded.append(extension)
                 except Exception as e:
                     print(f' ! Falha ao carregar cog {extension}: {e.__class__.__name__}: {e}')
                     cogs_failed.append(extension)
        print("-" * 20)
        print(f"Total de Cogs carregados: {len(cogs_loaded)}")
        if cogs_failed:
             print(f"Cogs com falha ({len(cogs_failed)}): {', '.join(cogs_failed)}")
        print("-" * 20)

        # Sincronizar comandos APÓS carregar cogs
        # Nota: a sincronização agora é feita dentro de cada Cog com `app_commands.guilds`
        #       ou você pode sincronizar tudo aqui se preferir.
        #       A sincronização no setup_hook (se usar a classe Cyberia) também é comum.
        #       Se você definiu `@app_commands.guilds` em cada comando, a sincronização explícita
        #       aqui pode não ser estritamente necessária, mas não custa garantir.
        if config.GUILD_ID_INT:
             guild_obj = discord.Object(id=config.GUILD_ID_INT)
             # Copia comandos globais para o servidor (se houver) e sincroniza
             # bot.tree.copy_global_to(guild=guild_obj) # Descomente se tiver comandos globais
             try:
                 synced = await bot.tree.sync(guild=guild_obj)
                 print(f"Sincronizados {len(synced)} comandos para o servidor ID: {config.GUILD_ID_INT}")
             except discord.HTTPException as e:
                  print(f"Falha ao sincronizar comandos: {e}")
             except discord.Forbidden as e:
                 print(f"Permissão negada para sincronizar comandos: {e}")
                 print("Verifique se o bot tem a permissão 'applications.commands' no servidor.")
        else:
             print("GUILD_ID não definido, sincronização de servidor específica pulada.")
             # Para sincronizar globalmente (pode levar até 1 hora para atualizar):
             # try:
             #     synced = await bot.tree.sync()
             #     print(f"Sincronizados {len(synced)} comandos globalmente.")
             # except Exception as e:
             #     print(f"Falha ao sincronizar comandos globalmente: {e}")


        # Iniciar o bot
        await bot.start(config.TOKEN)

# Executar o bot
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot desligado pelo usuário.")
    except ValueError as e: # Captura erros do config.py
         print(f"Erro de configuração: {e}")
    except discord.LoginFailure:
         print("Falha no login: Token inválido ou expirado. Verifique seu arquivo .env.")
    except Exception as e:
         print(f"Erro inesperado ao iniciar o bot: {e.__class__.__name__}: {e}")
