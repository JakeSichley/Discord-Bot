import os
import discord
import logging
import aiosqlite
from dotenv import load_dotenv
from discord.ext.commands import ExtensionError, Bot
import datetime

# todo: update memecoin storage

print(f'Current Discord Version: {discord.__version__}')
logging.basicConfig(level=logging.INFO)

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
OWNER = int(os.getenv('OWNER_ID'))
PREFIX = os.getenv('PREFIX')
DATABASE = os.getenv('DATABASE')

# load extensions (filename)
initial_extensions = ('admin', 'ddo', 'memecoin', 'utility', 'exceptions', 'moderation')
# unused extensions: None

# define cogs with tasks for reconnection behavior
task_extensions = ('DDO',)


class DreamBot(Bot):
    RECONNECT_BEHAVIOR = False
    DATABASE_NAME = DATABASE
    DEFAULT_PREFIX = PREFIX

    def __init__(self):
        super().__init__(command_prefix=get_prefix, case_insensitive=True, owner_id=OWNER)
        self.prefixes = {}
        self.initialized = False
        self.uptime = 0

        for cog in initial_extensions:
            try:
                self.load_extension(cog)
            except ExtensionError as e:
                print(e)

    async def on_ready(self):
        if not self.initialized:
            await self.change_presence(status=discord.Status.online, activity=discord.Activity(name='My Spaghetti Code',
                                       type=discord.ActivityType.watching))
            await self.retrieve_prefixes()
            self.initialized = True
            self.uptime = datetime.datetime.now()

        print('READY')

    async def on_message(self, message):
        if message.author == self.user:
            return

        if message.guild is None:
            print(f'Direct Message from {message.author}\nContent: {message.content}')

        if self.user.mentioned_in(message) and 'prefix' in message.content.lower() and message.guild is not None:
            await message.channel.send(f'It seems you\'re trying to find the prefix for this guild! '
                                       f'**Prefix**: `{await get_prefix(self, message)}`')

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

    async def retrieve_prefixes(self):
        try:
            async with aiosqlite.connect(self.DATABASE_NAME) as db:
                async with db.execute("SELECT * FROM Prefixes") as cursor:
                    async for guild, prefix in cursor:
                        self.prefixes[int(guild)] = prefix

        except aiosqlite.Error as e:
            print(f'Retrieve Prefixes Error: {e}')

    def run(self):
        super().run(TOKEN)


async def get_prefix(bot, message):
    if message.guild.id in bot.prefixes:
        return bot.prefixes[message.guild.id]
    return PREFIX


dream_bot = DreamBot()
dream_bot.run()
