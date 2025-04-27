import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN_TEST")
BOT_VERSION = os.getenv("BOT_VERSION", "0")
GUILD_ID = os.getenv("GUILD_ID")

if not TOKEN:
    raise ValueError("Token do Discord não encontrado. Defina DISCORD_TOKEN no arquivo .env.")

if not GUILD_ID:
    raise ValueError("ID do Servidor (GUILD_ID) não encontrado. Defina GUILD_ID no arquivo .env.")

try: 
    GUILD_ID_INT = int(GUILD_ID) # Converte GUILD_ID para inteiro para uso com discord.Object
except ValueError:
     raise ValueError("GUILD_ID no arquivo .env deve ser um número inteiro.")

YDL_OPTS = {
    'format': 'bestaudio/best', # Melhor qualidade de áudio
    'quiet': True, # Modo silencioso (sem logs)
    'extract_flat': False, # 'False' é necessário para obter a URL direta do stream
    'nocache': True, # Não usa cache para downloads
    'noplaylist': False, # Permite processar playlists
    'ignoreerrors': True, # Pula vídeos/músicas com erro em playlists
    'cookiefile': 'cookies/yt.txt',
}