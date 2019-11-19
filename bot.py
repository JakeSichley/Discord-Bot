import os
import discord
from dotenv import load_dotenv
from discord.ext import commands
from memecoin import MemeCoin
from ddo import DDO
from utility import UtilityFunctions
from exceptions import Exceptions

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
OWNER = int(os.getenv('OWNER_ID'))

bot = commands.Bot(command_prefix='!')


@bot.event
async def on_ready():
    await bot.change_presence(status=discord.Status.online, activity=discord.Game('Doin\' Bot Stuff'))
    print(f'{bot.user.name} has connected to Discord!')
    for guild in bot.guilds:
        print(f'Connected to Guild \'{guild.name}\'(id:{guild.id})')

    bot.owner_id = OWNER

    bot.add_cog(MemeCoin(bot))
    bot.add_cog(DDO(bot))
    bot.add_cog(UtilityFunctions(bot))
    bot.add_cog(Exceptions(bot))


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if 'calzone' in message.content.lower():
        await message.channel.send(file=discord.File('calzone.png'))

    await bot.process_commands(message)


bot.run(TOKEN)
