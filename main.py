# main.py (Corrigido)
import discord
from discord.ext import commands
import os
import asyncio
import config

# --- Configuração de Intents ---
intents = discord.Intents.default() 
intents.message_content = True # Necessário para ler mensagens
intents.guilds = True # Necessário para comandos de slash
intents.voice_states = True # Necessário para comandos de voz

class CyberiaBot(commands.Bot):
    def __init__(self):
        # command_prefix é tecnicamente necessário, mas não usado para slash commands
        super().__init__(command_prefix="!", intents=intents)
        # A árvore de comandos (self.tree) já existe em commands.Bot

    async def setup_hook(self) -> None:
        """
        Este hook é chamado automaticamente após o login mas antes do bot estar completamente pronto. Ideal para carregar extensões e sincronizar comandos.
        """
        print("--- Executando setup_hook ---")

        # 1. Carregar Cogs
        print("Carregando Cogs...")
        cogs_loaded = []
        cogs_failed = []
        
        if os.path.isdir('./cogs'): # Certifica que a pasta 'cogs' existe no mesmo nível que main.py
            for filename in os.listdir('./cogs'):
                if filename.endswith('.py') and not filename.startswith('__'):
                    extension = f'cogs.{filename[:-3]}'
                    try:
                        await self.load_extension(extension)
                        print(f' > Cog {extension} carregado com sucesso.')
                        cogs_loaded.append(extension)
                    except commands.ExtensionNotFound:
                        print(f' ! Erro: Cog {extension} não encontrado.')
                        cogs_failed.append(extension)
                    except commands.ExtensionAlreadyLoaded:
                        print(f' ! Aviso: Cog {extension} já estava carregado.')
                        # Não adiciona aos falhados se já estava carregado
                    except commands.NoEntryPointError:
                        print(f' ! Erro: Cog {extension} não possui uma função setup().')
                        cogs_failed.append(extension)
                    except Exception as e:
                        print(f' ! Falha ao carregar cog {extension}: {e.__class__.__name__}: {e}')
                        cogs_failed.append(extension)
        else:
            print(" ! Aviso: Diretório './cogs' não encontrado. Nenhum cog carregado.")

        print("-" * 20)
        print(f"Total de Cogs carregados: {len(cogs_loaded)}")
        if cogs_failed:
            print(f"Cogs com falha ({len(cogs_failed)}): {', '.join(cogs_failed)}")
        print("-" * 20)
            
        print("Sincronizando comandos...")
        if config.GUILD_ID_INT:
            guild_obj = discord.Object(id=config.GUILD_ID_INT)
            try:
                self.tree.copy_global_to(guild=guild_obj) # Descomente se tiver comandos globais para copiar
                synced = await self.tree.sync(guild=guild_obj)
                print(f"Sincronizados {len(synced)} comandos para o servidor ID: {config.GUILD_ID_INT}")
            except discord.HTTPException as e:
                print(f"Falha ao sincronizar comandos para o servidor: {e}")
            except discord.Forbidden as e:
                print(f"Permissão negada para sincronizar comandos: {e}")
                print("Verifique se o bot tem a permissão 'applications.commands' no servidor.")
            except Exception as e:
                print(f"Erro inesperado durante a sincronização de servidor: {e}")
        else:
            print("GUILD_ID não definido no .env. Sincronização específica de servidor pulada.")
            try:
               synced = await self.tree.sync()
               print(f"Sincronizados {len(synced)} comandos globalmente.")
            except Exception as e:
               print(f"Falha ao sincronizar comandos globalmente: {e}")

        print("--- setup_hook concluído ---")


    async def on_ready(self):
        """Chamado quando o bot está pronto e operacional."""
        print('------------------------------------')
        print(f'--- Bot {self.user} está online! ---')
        print(f'Versão: {config.BOT_VERSION}')
        if self.user:
            print(f'ID do Bot: {self.user.id}')
        print(f'Servidor de Teste ID: {config.GUILD_ID_INT}')
        print('------------------------------------')

# --- Função Principal para Iniciar ---
async def main():
    bot = CyberiaBot()
    print("Iniciando o bot...")
    async with bot:
        await bot.start(config.TOKEN)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot desligado pelo usuário.")
    except ValueError as e: # Captura erros do config.py
        print(f"Erro de configuração: {e}")
    except discord.LoginFailure:
        print("Falha no login: Token inválido ou expirado. Verifique seu arquivo .env.")
    except discord.PrivilegedIntentsRequired:
        print("Erro de Intents: Uma ou mais intents privilegiadas (ex: message_content, members) estão habilitadas no código, mas não estão ativadas no Portal do Desenvolvedor do Discord para este bot.")
    except Exception as e:
        print(f"Erro crítico ao tentar iniciar o bot: {e.__class__.__name__}: {e}")