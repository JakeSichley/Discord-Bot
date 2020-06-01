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

bot = commands.Bot(command_prefix='#', case_insensitive=True)
bot.owner_id = OWNER

# load extensions (filename)
bot.load_extension('admin')
bot.load_extension('ddo')
bot.load_extension('utility')
bot.load_extension('exceptions')
bot.load_extension('moderation')
# bot.load_extension('memecoin')


@bot.event
async def on_ready():
    await bot.change_presence(status=discord.Status.online,
                              activity=discord.Activity(name='My Spaghetti Code', type=discord.ActivityType.watching))
    print(f'{bot.user.name} has connected to Discord!')
    for guild in bot.guilds:
        print(f'Connected to Guild \'{guild.name}\'(id:{guild.id})')


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if 'calzone' in message.content.lower():
        await message.channel.send(file=discord.File('calzone.png'))

    if message.guild is None:
        print(f'Direct Message from {message.author}\nContent: {message.content}')

    await bot.process_commands(message)


bot.run(TOKEN)
