import discord
class Cyberia(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.synced = False
        self.added = False

    async def on_ready(self):
        await self.wait_until_ready()
        if not self.synced:
            await tree.sync(guild=discord.Object(
                '949532298007679008'))
            self.synced = True
        if not self.added:
            self.added = True
        print(f"Say hi to {self.user}!")