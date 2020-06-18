from discord import HTTPException, Message, Embed
from discord.ext import commands, tasks
from random import seed, shuffle
from re import search
from time import time
from aiohttp import ClientSession
from bs4 import BeautifulSoup
from dataclasses import dataclass
from asyncio import sleep
from json.decoder import JSONDecodeError


class DDO(commands.Cog):
    SERVERS = ('Argonnessen', 'Cannith', 'Ghallanda', 'Khyber', 'Orien', 'Sarlona', 'Thelanis', 'Wayfinder')
    ADVENTURE_TYPES = ('Quest', 'Raid', 'Wilderness')
    DIFFICULTIES = ('Casual', 'Normal', 'Hard', 'Elite', 'Reaper')
    LEX_ID = 91995622093123584

    def __init__(self, bot):
        self.bot = bot
        self.api_data = None
        self.raid_data = {}
        self.query_ddo_audit.start()
        self.check_for_valid_raids.start()

    @commands.command(name='roll', help='Simulates rolling dice. Syntax example: 9d6', ignore_extra=True)
    async def roll(self, ctx, die_pattern):
        if not search("\d+d\d+", die_pattern):
            await ctx.send('ERROR: Invalid Syntax! Expected (number of die)d(number of sides)')
        else:
            die = search("\d+d\d+", die_pattern).group().split('d')

            if int(die[1]) == 1:
                await ctx.send(int(die[0]))

            else:
                seed(time())
                dice = [x for x in range(int(die[0]), int(die[0]) * int(die[1]) + 1)]
                shuffle(dice)
                await ctx.send(dice[0])

    @commands.command(name='ddoitem', help='Pulls basic information about an item in Dungeons & Dragons Online '
                      'from the wiki')
    async def ddo_item(self, ctx, *item):
        # Join all the parameters together
        item_name = '_'.join(item)
        url = 'https://ddowiki.com/page/Item:' + item_name

        async with ClientSession() as session:
            async with session.get(url) as r:
                # If the page 404's, return an error message
                if r.status == 404:
                    await ctx.send(f'ERROR: Request Status Code 404. Please make sure the item exists!')
                    return

                # If not 404, soup-ify the page
                data = await r.text()
                soup = BeautifulSoup(data, features="html5lib")
                # Pull the main table
                table = soup.find_all('tr')

                # Tag elements don't function in this table
                # Create list of all elements in the table (type: string)
                string_elements = [str(element).strip() for element in table]

                # Prep data variables, can be checked later for 'None'
                enchantment_string = None
                minimum_level_string = None
                item_type_string = None

                # Search each element to see if it contains the data we're interested in
                for string in string_elements:
                    if string.find('Enchantments') != -1:
                        enchantment_string = string
                    elif string.lower().find('minimum level') != -1:
                        minimum_level_string = string
                    elif string.find('Item Type') != -1 or string.find('Weapon Type') != -1:
                        item_type_string = string

                # If we did not find an enchantments element, return an error
                if enchantment_string is None:
                    await ctx.send(f'ERROR: Enchantments table not found. Could not supply item data.')
                    return

                # Each enchantment is a table list element. Find the first element, and the end of the last element
                first_index = enchantment_string.find('<li>')
                last_index = enchantment_string.rfind('</li>')

                # If there are not valid list indexes, return an error
                if first_index == -1 or last_index == -1:
                    await ctx.send(f'ERROR: Enchantments table was found, but no could not find valid enchantments.')
                    return

                # Substring the main enchantments element from the above indexes
                rows = enchantment_string[first_index:last_index].split('<li>')
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
                            result = search("(?<=>)( )*(\+\d+ )*(\w|\d)(.+?)(?=</a>)", element)
                            # If our result is not a Mythic Bonus (these are on nearly every single item), add it
                            if result is not None and str(result.group(0)).find('Mythic') == -1:
                                enchantments.append(result.group(0).strip())

                # Prep other detail variables
                item_type = 'none'
                minimum_level = -1

                # If we have a minimum level string, extract the minimum level using regex
                if minimum_level_string is not None:
                    minimum_level = int(search("\d+?(?=(\n</td>))", minimum_level_string).group(0))

                # If we have a item type string, extract the item type using regex
                if item_type_string is not None:
                    item_type = search("(?<=>).+?(?=(\n</td>))", item_type_string).group(0)
                    # Sometimes (in the case of weapons) the parent type is bolded - strip these tags
                    item_type = item_type.replace('<b>', '').replace('</b>', '')

                # Check for Attuned to Heroism, as this is coded strangely
                for index in range(len(enchantments)):
                    if enchantments[index].find('Attuned to Heroism') != -1:
                        # If Attuned to Heroism is an enchantment, remove all sub-enchantments from the final list
                        enchantments = enchantments[0:index + 1]
                        break

                # Replace the item name underscores from the url with spaces
                item_name = item_name.replace('_', ' ')

                # Create and send our embedded object
                embed = Embed(title='**' + str(item_name) + '**', url=url, color=0x6879f2)
                embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar_url)
                embed.set_thumbnail(url='https://i.imgur.com/QV6uUZf.png')
                embed.add_field(name='Minimum Level', value=str(minimum_level))
                embed.add_field(name='Item Type', value=item_type)
                embed.add_field(name='Enchantments', value='\n'.join(enchantments))
                embed.set_footer(text="Please report any formatting issues to my owner!")
                await ctx.send(embed=embed)

    @commands.command(name='lfms', help='Returns a list of active LFMS for the specified server.\nValid servers include'
                      ' Argonnessen, Cannith, Ghallanda, Khyber, Orien, Sarlona, Thelanis, and Wayfinder'
                      '\nInformation is populated from \'DDO Audit\' every 20 seconds.')
    async def ddolfms(self, ctx, server='Khyber'):
        if self.api_data is None:
            return await ctx.send('Failed to query DDO Audit API.')

        if server not in self.SERVERS:
            server = 'Khyber'

        try:
            server_data = self.api_data[self.SERVERS.index(server)]
        except ValueError:
            return await ctx.send(f'No Active LFM\'s on {server}!')

        else:
            raids = [q['QuestName'] for q in server_data['Groups'] if q['AdventureType'] == 'Raid']
            quests = [q['QuestName'] for q in server_data['Groups']
                      if q['QuestName'] is not None and q['AdventureType'] != 'Raid']
            groups = [q['Comment'] for q in server_data['Groups'] if q['QuestName'] is None]

            for li in [raids, quests, groups]:
                if not li:
                    li.append('None')

            return await ctx.send(f'**Current Raids on {server}:** {", ".join(raids)}\n'
                                  f'**Current Quests on {server}:** {", ".join(quests)}\n'
                                  f'**Current Groups on {server}:** {", ".join(groups)}\n')

    @commands.command(name='flfms', help='Returns a filtered list of active LFMS for the specified server.\n'
                      'Option filters include: LFM Type: (Quest, Raid, Wilderness), Difficulty: (Casual, Normal, Hard,'
                      'Elite, Reaper), and Level: (1-30). You MUST supply a server.\n'
                      'Valid servers include Argonnessen, Cannith, Ghallanda, Khyber, Orien, Sarlona, Thelanis, and'
                      'Wayfinder\nInformation is populated from \'DDO Audit\' every 30 seconds.')
    async def ddofilterlfms(self, ctx, *args):
        if self.api_data is None:
            return await ctx.send('Failed to query DDO Audit API.')

        # attempt to parse arguments provided
        server = atype = diff = level = None

        for arg in args:
            # parse string arguments first
            if arg in self.SERVERS:
                server = arg
            elif arg in self.ADVENTURE_TYPES:
                atype = arg
            elif arg in self.DIFFICULTIES:
                diff = arg
            # if we can't parse the arg to one of the above, try to convert the arg to an int
            # if we can't cast to int OR a successful cast is outside our acceptable range, level = None
            else:
                try:
                    level = int(arg)
                    if level < 1 or level > 30:
                        level = None
                except ValueError:
                    level = None

        try:
            server_data = self.api_data[self.SERVERS.index(server)]
        except ValueError:
            return await ctx.send(f'No Active LFM\'s on {server} - Cannot filter LFMs!')

        # build sets for each of our individual filters, as well as a master set of all quests
        all_quests = {q['QuestName'] for q in server_data['Groups']}
        atypes = {q['QuestName'] for q in server_data['Groups'] if atype is not None and q['AdventureType'] == atype}
        diffs = {q['QuestName'] for q in server_data['Groups'] if diff is not None and q['Difficulty'] == diff}
        levels = {q['QuestName'] for q in server_data['Groups'] if level is not None and
                  q['MinimumLevel'] <= level <= q['MaximumLevel']}

        # if our value is not None, start performing intersection calculations on the full set
        for filtered_set, value in [(atypes, atype), (diffs, diff), (levels, level)]:
            if value is not None:
                all_quests.intersection_update(filtered_set)

        if not all_quests:
            all_quests.add('None')

        await ctx.send(f'**Filtered Results on {server}:** {", ".join(all_quests)}')

    @tasks.loop(seconds=30)
    async def query_ddo_audit(self):
        async with ClientSession() as session:
            async with session.get('https://www.playeraudit.com/api/groups') as r:
                if r.status == 200:
                    try:
                        self.api_data = await r.json(encoding='utf-8-sig', content_type='text/html')
                    except JSONDecodeError as e:
                        self.api_data = None
                        print(e)
                else:
                    self.api_data = None

    @query_ddo_audit.before_loop
    async def before_api_query_loop(self):
        await self.bot.wait_until_ready()

    @tasks.loop(seconds=30)
    async def check_for_valid_raids(self):
        lex_user = self.bot.get_user(self.LEX_ID)

        if lex_user is None or self.api_data is None:
            return

        khyber_data = None
        for data in self.api_data:
            if data['Name'] == 'Khyber':
                khyber_data = data
                break

        if khyber_data is None:
            return

        raids = [quest for quest in khyber_data['Groups'] if (quest['AdventureType'] == 'Raid'
                 and quest['MinimumLevel'] >= 20)]

        if not raids:
            self.raid_data.clear()
            return

        for raid in raids:
            name = raid['Leader']['Name']
            if name not in self.raid_data or self.raid_data[name].quest != raid['QuestName']:
                embed = build_embed(raid, name, self.bot.user.name, self.bot.user.avatar_url)

                try:
                    message = await lex_user.send(embed=embed)
                    self.raid_data[name] = RaidEmbed(raid['QuestName'], len(raid["Members"]), message, embed)
                except HTTPException as e:
                    print(e)

            elif name in self.raid_data and self.raid_data[name].quest == raid['QuestName'] and \
                    self.raid_data[name].members != len(raid["Members"]):
                self.raid_data[name].members = len(raid["Members"])
                self.raid_data[name].embed.set_field_at(2, name='Raid Size', inline=False,
                                                       value=f'{len(raid["Members"]) + 1} Members')
                self.raid_data[name].embed.set_field_at(3, name='Active Time', inline=False,
                                                       value=f'{raid["AdventureActive"]} Minutes')
                await self.raid_data[name].message.edit(embed=self.raid_data[name].embed)

    @check_for_valid_raids.before_loop
    async def before_valid_raids_loop(self):
        await self.bot.wait_until_ready()
        await sleep(3)

    @commands.command(name='killloop', hidden=True)
    async def kill_loop(self, ctx):
        self.check_for_valid_raids.cancel()
        self.query_ddo_audit.cancel()
        await ctx.send('All Loops Terminated.')

    def cog_unload(self):
        self.check_for_valid_raids.cancel()
        self.query_ddo_audit.cancel()
        self.raid_data.clear()
        print('Completed Unload for Cog: DDO')


@dataclass
class RaidEmbed:
    quest: str
    members: int
    message: Message
    embed: Embed


def build_embed(raid, name, bot_name, bot_avatar):
    comment = 'None' if raid['Comment'] is None or raid['Comment'] == '' else raid['Comment']
    title = 'Group' if raid["QuestName"] is None or raid["QuestName"] == '' else raid["QuestName"]

    embed = Embed(title=f'{raid["Leader"]["Name"]} is leading a {raid["Difficulty"]} {title}!', color=0x1dcaff)
    embed.set_author(name=bot_name, icon_url=bot_avatar)
    embed.add_field(name='Raid Leader', value=name, inline=False)
    embed.add_field(name='Difficulty', value=raid['Difficulty'], inline=False)
    embed.add_field(name='Raid Size', value=f'{len(raid["Members"]) + 1} Members', inline=False)
    embed.add_field(name='Active Time', value=f'{raid["AdventureActive"]} Minutes', inline=False)
    embed.add_field(name='Comment', value=comment, inline=False)
    embed.set_footer(text="Please report any issues to my owner!")

    return embed


def setup(bot):
    bot.add_cog(DDO(bot))
    print('Completed Setup for Cog: DDO')
