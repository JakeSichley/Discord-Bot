import os
import discord
from dotenv import load_dotenv
from discord.ext import commands
import logging

print(f'Current Discord Version: {discord.__version__}')
logging.basicConfig(level=logging.INFO)

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
OWNER = int(os.getenv('OWNER_ID'))

# load extensions (filename)
initial_extensions = ('admin', 'ddo', 'utility', 'exceptions', 'moderation')
# unused extensions: 'memecoin'

# define cogs with tasks for reconnection behavior
task_extensions = ('DDO', 'MemeCoin')


class DreamBot(commands.Bot):
    RECONNECT_BEHAVIOR = False

    def __init__(self):
        super().__init__(command_prefix='!', case_insensitive=True, owner_id=OWNER)

        for cog in initial_extensions:
            try:
                self.load_extension(cog)
            except commands.ExtensionError as e:
                print(e)

    async def on_ready(self):
        await self.change_presence(status=discord.Status.online, activity=discord.Activity(name='My Spaghetti Code',
                                   type=discord.ActivityType.watching))
        print('READY')

    async def on_message(self, message):
        if message.author == self.user:
            return

        if 'calzone' in message.content.lower():
            await message.channel.send(file=discord.File('calzone.png'))

        if message.guild is None:
            print(f'Direct Message from {message.author}\nContent: {message.content}')

        await self.process_commands(message)

    async def on_disconnect(self):
        if self.RECONNECT_BEHAVIOR:
            for cog in task_extensions:
                try:
                    self.get_cog(cog).disconnect()
                    print(f'Disconnected Cog: {cog} (Event: on_disconnect')
                except AttributeError as e:
                    print(e)
        print('DISCONNECTED')

    async def on_resumed(self):
        if self.RECONNECT_BEHAVIOR:
            for cog in task_extensions:
                try:
                    self.get_cog(cog).disconnect()
                    print(f'Reconnected Cog: {cog} (Event: on_resumed')
                except AttributeError as e:
                    print(e)
        print('RESUMED')

    async def on_connect(self):
        if self.RECONNECT_BEHAVIOR:
            pass
        print('CONNECTED')

    def run(self):
        super().run(TOKEN)


bot = DreamBot()
bot.run()
