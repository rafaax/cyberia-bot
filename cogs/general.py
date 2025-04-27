import discord
from discord import Interaction, app_commands
from discord.ext import commands
import config

class GeneralCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    
    @app_commands.command(name="ping", description="Latência do bot :)")
    @app_commands.guilds(discord.Object(id=config.GUILD_ID_INT))
    async def ping_command(self, interaction: Interaction):
        await interaction.response.send_message(f"{round(self.bot.latency * 1000)}ms de latência my brotha", ephemeral=True)
        print("Comando /ping executado.")

    




    @app_commands.command(name='help', description='Lista os comandos disponíveis')
    @app_commands.guilds(discord.Object(id=config.GUILD_ID_INT))
    async def help(self, interaction: Interaction):
        """Mostra uma lista de todos os comandos slash disponíveis neste servidor."""

        print(f"--- Comando /help acionado por {interaction.user} na Guild ID: {interaction.guild.id} ---")

        embed = discord.Embed(title="Comandos disponíveis (Leitura Local)", color=discord.Color.green())

        if not interaction.guild:
            await interaction.response.send_message("Erro: Guild não encontrada na interação.", ephemeral=True)
            return
        if not config.GUILD_ID_INT or interaction.guild.id != config.GUILD_ID_INT:
            await interaction.response.send_message("Erro: Comando não aplicável a esta guild.", ephemeral=True)
            return

        # --- WORKAROUND: Acessar comandos diretamente da árvore ---
        local_commands_for_guild = []
         
        if config.GUILD_ID_INT in self.bot.tree._guild_commands: 
            local_commands_for_guild = list(self.bot.tree._guild_commands[config.GUILD_ID_INT].values())  # Acessa os comandos da guilda diretamente

        if not local_commands_for_guild:
            embed.description = "Nenhum comando slash encontrado (erro na leitura local da árvore)."
        else:
            sorted_commands = sorted(local_commands_for_guild, key=lambda cmd: cmd.name)

            # Adiciona os comandos ao embed
            for command in sorted_commands:
                if isinstance(command, discord.app_commands.Command):
                    params_list = [f"`{param.name}`{'*' if param.required else ''}" for param in command.parameters]
                    params_str = ", ".join(params_list) if params_list else "Sem parâmetros"

                    embed.add_field(
                        name=f"/{command.name}",
                        value=f"{command.description or 'Sem descrição.'}\n**Parâmetros:** {params_str}",
                        inline=False
                    )

            embed.set_footer(text="* indica parâmetro obrigatório.")

        await interaction.response.send_message(embed=embed, ephemeral=True)





    @app_commands.command(name='info', description='Mostra informações sobre o bot')
    @app_commands.guilds(discord.Object(id=config.GUILD_ID_INT))
    async def info(self, interaction: Interaction):
        """Exibe informações básicas sobre o bot."""
        embed = discord.Embed(title="Informações do Bot", color=discord.Color.blue()) # Usar discord.Color
        if self.bot.user: # Garante que self.bot.user não é None
            embed.add_field(name="Nome", value=self.bot.user.name, inline=True)
            embed.add_field(name="ID", value=self.bot.user.id, inline=True)
            if self.bot.user.avatar:
                 embed.set_thumbnail(url=self.bot.user.avatar.url)
        embed.add_field(name="Versão", value=config.BOT_VERSION, inline=True)
        embed.add_field(name="Latência", value=f"{round(self.bot.latency * 1000)}ms", inline=True)
        embed.add_field(name="discord.py", value=discord.__version__, inline=True)


        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
     await bot.add_cog(GeneralCog(bot), guilds=[discord.Object(id=config.GUILD_ID_INT)])
