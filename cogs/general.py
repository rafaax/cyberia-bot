import discord
from discord import Interaction, app_commands
from discord.ext import commands
import config

class GeneralCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name='help', description='Lista os comandos disponíveis')
    @app_commands.guilds(discord.Object(id=config.GUILD_ID_INT))
    async def help(self, interaction: Interaction):
        """Mostra uma lista de todos os comandos slash disponíveis neste servidor."""
        embed = discord.Embed(title="Comandos disponíveis", color=discord.Color.green()) # Usar discord.Color

        # Pega os comandos registrados para este servidor especificamente
        guild_commands = self.bot.tree.get_commands(guild=interaction.guild, type=discord.InteractionType.application_command)

        if not guild_commands:
            embed.description = "Nenhum comando slash encontrado para este servidor."
        else:
            for command in guild_commands:
                # Para comandos slash, os parâmetros estão em command.parameters
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
