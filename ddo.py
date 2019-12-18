import discord
from discord.ext import commands
import random
import re
import time
import requests
from bs4 import BeautifulSoup


class DDO(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='roll', help='Simulates rolling dice. Syntax example: 9d6', ignore_extra=True)
    async def roll(self, ctx, die_pattern):
        if not re.search("\d+d\d+", die_pattern):
            await ctx.send('ERROR: Invalid Syntax! Expected (number of die)d(number of sides)')
        else:
            die = re.search("\d+d\d+", die_pattern).group().split('d')

            if int(die[1]) == 1:
                await ctx.send(int(die[0]))

            else:
                random.seed(time.time())
                dice = [x for x in range(int(die[0]), int(die[0]) * int(die[1]) + 1)]
                random.shuffle(dice)
                await ctx.send(dice[0])

    @commands.command(name='ddoitem',
                      help='Pulls basic information about an item in Dungeons & Dragons Online from the wiki')
    async def ddo_item(self, ctx, *item):
        # Join all the parameters together
        itemname = '_'.join(item)
        url = 'https://ddowiki.com/page/Item:' + itemname
        r = requests.get(url)

        # If the page 404's, return an error message
        if r.status_code == 404:
            await ctx.send(f'ERROR: Request Status Code 404. Please make sure the item exists!')
            return

        # If not 404, soup-ify the page
        data = r.text
        soup = BeautifulSoup(data, features="html5lib")
        # Pull the main table
        table = soup.find_all('tr')

        # Tag elements don't function in this table
        # Create list of all elements in the table (type: string)
        string_elements = [str(element).strip() for element in table]

        # Prep data variables, can be checked later for 'None'
        enchantmentstring = None
        minimumlevelstring = None
        itemtypestring = None

        # Search each element to see if it contains the data we're interested in
        for string in string_elements:
            if string.find('Enchantments') != -1:
                enchantmentstring = string
            elif string.lower().find('minimum level') != -1:
                minimumlevelstring = string
            elif string.find('Item Type') != -1 or string.find('Weapon Type') != -1:
                itemtypestring = string

        # If we did not find an enchantments element, return an error
        if enchantmentstring is None:
            await ctx.send(f'ERROR: Enchantments table not found. Could not supply item data.')
            return

        # Each enchantment is a table list element. Find the first element, and the end of the last element
        firstindex = enchantmentstring.find('<li>')
        lastindex = enchantmentstring.rfind('</li>')

        # If there are not valid list indexes, return an error
        if firstindex == -1 or lastindex == -1:
            await ctx.send(f'ERROR: Enchantments table was found, but no could not find valid enchantments.')
            return

        # Substring the main enchantments element from the above indexes
        rows = enchantmentstring[firstindex:lastindex].split('<li>')
        enchantments = []

        for element in rows:
            if element != '':
                # 'pure' elements have no tooltip or any other html tags
                if element.find('has_tooltip') == -1 and element.find('</a>') == -1:
                    if element != '</li>':
                        # Clean up element from whitespace and tags
                        result = (element.replace('</li>', '').replace('\n', '').replace('<ul>', ''))
                        # Weird case where an augment slips through
                        if result != '' and result.find('Elemental damage') == -1:
                            enchantments.append(result)
                # If the element has a tooltip, do some regex magic
                elif element.find('has_tooltip') != -1:
                    # Enchantment description is always before the first closing '</a>'
                    # Positive Lookahead for the fewest number of characters
                    # These characters are always preceeded by a word or a digit
                    # Sometimes, enchantments have a leading space, or a '+' character
                    #   look for 0 or more of these and add them to our match
                    # Finally, Positive Lookbehind to match the closing '>' character preceeding our description
                    # Note: This description was written 'backwards', (positive lookbehind occurs first, etc)
                    result = re.search("(?<=>)( )*(\+\d+ )*(\w|\d)(.+?)(?=</a>)", element)
                    # If our result is not a Mythic Bonus (because these are on nearly every single item), add it
                    if result is not None and str(result.group(0)).find('Mythic') == -1:
                        enchantments.append(result.group(0).strip())

        # Prep other detail variables
        itemtype = 'none'
        minimumlevel = -1

        # If we have a minimum level string, extract the minimum level using regex
        if minimumlevelstring is not None:
            minimumlevel = int(re.search("\d+?(?=(\n</td>))", minimumlevelstring).group(0))

        # If we have a item type string, extract the item type using regex
        if itemtypestring is not None:
            itemtype = re.search("(?<=>).+?(?=(\n</td>))", itemtypestring).group(0)
            # Sometimes (in the case of weapons) the parent type is bolded - strip these tags
            itemtype = itemtype.replace('<b>', '').replace('</b>', '')

        # Check for Attuned to Heroism, as this is coded strangely
        for index in range(len(enchantments)):
            if enchantments[index].find('Attuned to Heroism') != -1:
                # If Attuned to Heroism is an enchantment, remove all sub-enchantments from the final list
                enchantments = enchantments[0:index + 1]
                break

        # Replace the item name underscores from the url with spaces
        itemname = itemname.replace('_', ' ')

        # Create and send our embedded object
        embed = discord.Embed(title='**' + str(itemname) + '**', url=url, color=0x6879f2)
        embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar_url)
        embed.set_thumbnail(url='https://i.imgur.com/QV6uUZf.png')
        embed.add_field(name='Minimum Level', value=str(minimumlevel))
        embed.add_field(name='Item Type', value=itemtype)
        embed.add_field(name='Enchantments', value='\n'.join(enchantments))
        embed.set_footer(text="Please report any formatting issues to my owner!")
        await ctx.send(embed=embed)
