import os
import discord
from dotenv import load_dotenv
from discord.ext import commands
import time
import random
import re
import datetime
import pytz
import requests
from bs4 import BeautifulSoup

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = int(os.getenv('DISCORD_GUILD'))
OWNER = int(os.getenv('OWNER_ID'))

bot = commands.Bot(command_prefix='!')


@bot.event
async def on_ready():
    await bot.change_presence(status=discord.Status.online, activity=discord.Game('Building a Bot Friend!'))
    print(f'{bot.user.name} has connected to Discord!')
    for guild in bot.guilds:
        print(f'Connected to Guild \'{guild.name}\'(id:{guild.id})')


@bot.command(name='roll', help='Simulates rolling dice. Syntax example: 9d6')
async def roll(ctx, die_pattern):
    if not re.search("\d+d\d+", die_pattern):
        await ctx.send('ERROR: Invalid Syntax! Expected (number of die)d(number of sides)')
    else:
        die = re.search("\d+d\d+", die_pattern).group().split('d')

        if int(die[1]) == 1:
            await ctx.send(int(die[0]))

        else:
            '''random.seed(time.time())
            dice = [
                random.choice(range(1, int(die[1])))
                # numpy.random.randint(1, int(die[1]))
                for _ in range(int(die[0]))
            ]
            await ctx.send(sum(dice))'''

            random.seed(time.time())
            dice = [x for x in range(int(die[0]), int(die[0]) * int(die[1]) + 1)]
            random.shuffle(dice)
            await ctx.send(dice[0])


'''@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if 'cool' in message.content.lower():
        response = 'Cool. Cool cool cool cool cool cool cool, no doubt no doubt no doubt no doubt.'
        if message.author.id == OWNER:
            response = response.upper()

        await message.channel.send(response)'''


@bot.command(name='time', help='Responds with the current time. Can be supplied with a timezone.\nFor a full list of '
                               'supported timezones, see https://en.wikipedia.org/wiki/List_of_tz_database_time_zones')
async def current_time(ctx, timezone='UTC'):
    # await ctx.send(f'{ctx.author.mention}, the current time is {time.asctime(time.localtime())}')
    if timezone not in pytz.all_timezones:
        timezone = 'UTC'
    today = datetime.datetime.now(pytz.timezone(timezone))
    printable_format = today.strftime('%I:%M%p on %A, %B %d, %Y (%Z)')
    await ctx.send(f'{ctx.author.mention}, the current time is {printable_format}')


@bot.command(name='DDOItem', help='Pulls basic information about an item in Dungeons & Dragons Online from the wiki')
async def ddo_item(ctx, *item):
    itemname = '_'.join(item)
    url = 'https://ddowiki.com/page/Item:' + itemname
    r = requests.get(url)

    if r.status_code == 404:
        await ctx.send(f'ERROR: Request Status Code 404. Please make sure the item exists!')
        return

    data = r.text
    soup = BeautifulSoup(data, features="html5lib")
    table = soup.find_all('tr')

    string_elements = []
    for element in table:
        string_elements.append(str(element))

    enchantments = None
    minimumlevelstring = None
    itemtypestring = None

    for string in string_elements:
        if string.find('Enchantments') is not -1:
            enchantments = string
        elif string.lower().find('minimum level') is not -1:
            minimumlevelstring = string
        elif string.find('Item Type') is not -1 or string.find('Weapon Type') is not -1:
            itemtypestring = string

    if enchantments is None:
        await ctx.send(f'ERROR: Enchantments table not found. Could not supply item data.')
        return

    firstindex = enchantments.find('<li>')
    lastindex = enchantments.rfind('</li>')

    if firstindex == -1 or lastindex == -1:
        await ctx.send(f'ERROR: Enchantments table was found, but no could not find valid enchantments.')
        return

    rows = enchantments[firstindex:lastindex].split('<li>')

    final = []
    for row in rows:
        element = row.strip()

        if element is not '':
            if element.find('has_tooltip') == -1 and element.find('</a>') == -1:
                if element != '</li>':
                    result = (element.replace('</li>', '').replace('\n', '').replace('<ul>', ''))
                    if result is not '' and result.find('Elemental damage') == -1:
                        final.append(result)
            elif element.find('has_tooltip') != -1:
                result = re.search("(?<=>)( )*(\+\d+ )*(\w|\d)(.+?)(?=</a>)", element)
                if result is not None and str(result.group(0)).find('Mythic') == -1:
                    final.append(result.group(0).strip())

    itemtype = 'none'
    minimumlevel = -1

    if minimumlevelstring is not None:
        minimumlevel = int(re.search("\d+?(?=(\n</td>))", minimumlevelstring).group(0))

    if itemtypestring is not None:
        itemtype = re.search("(?<=>).+?(?=(\n</td>))", itemtypestring).group(0)
        itemtype = itemtype.replace('<b>', '').replace('</b>', '')

    # Check for Attuned nonsense
    for index in range(len(final)):
        if final[index].find('Attuned to Heroism') is not -1:
            final = final[0:index + 1]
            break

    finalenchantments = ''
    for enchantment in final:
        finalenchantments = finalenchantments + '\n\t' + enchantment

    # TODO: Update result to utilize discord.Embed

    itemname = itemname.replace('_', ' ')
    await ctx.send(f'```{itemname}\n\nItem Type: {itemtype}\nMinimum Level: {minimumlevel}\
                    \nEnchantments:{finalenchantments}```')


bot.run(TOKEN)
