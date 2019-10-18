import os
import discord
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = int(os.getenv('DISCORD_GUILD'))

client = discord.Client()


@client.event
async def on_ready():
    await client.change_presence(status=discord.Status.online, activity=discord.Game('Building a Bot Friend!'))
    print(f'{client.user.name} has connected to Discord!')
    for guild in client.guilds:
        print(f'Connected to Guild \'{guild.name}\'(id:{guild.id})')


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if 'cool' in message.content.lower():
        response = 'Cool. Cool cool cool cool cool cool cool, no doubt no doubt no doubt no doubt.'
        await message.channel.send(response)

client.run(TOKEN)
