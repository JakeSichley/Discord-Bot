"""
MIT License

Copyright (c) 2019-Present Jake Sichley

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from utils.enums.ddo_enums import Servers, AdventureTypes, Difficulties

import re
from asyncio import sleep, TimeoutError
from json.decoder import JSONDecodeError
from random import seed, randrange
from re import search
from time import time
from typing import no_type_check, Dict, Optional, Any, Union

from aiohttp import ClientError
from bs4 import BeautifulSoup
from discord import Embed
from discord import app_commands, Interaction
from discord.ext import commands, tasks

from dreambot import DreamBot
from utils.context import Context
from utils.enums.network_return_type import NetworkReturnType
from utils.logging_formatter import bot_logger
from utils.network_utils import network_request, ExponentialBackoff


class DDO(commands.Cog):
    """
    A Cogs class that contains Dungeons & Dragons Online commands.

    Constants:
        SERVERS (tuple): A tuple of valid servers for DDOAudit
        ADVENTURE_TYPES (tuple): A tuple of valid adventure types for DDOAudit
        DIFFICULTIES (tuple): A tuple of valid difficulties for DDOAudit
        QUERY_INTERVAL (int): How frequently API data from DDOAudit should be queried.
        feature_subgroup (app_commands.Group): The AppCommand Group for commands (not implicit - `roll` is top-level)

    Attributes:
        bot (DreamBot): The Discord bot.
        api_data (dict): The response data from DDOAudit (used for LFMs).
        query_ddo_audit (ext.tasks): Stores the task that queries DDOAudit every {QUERY_INTERVAL} seconds.
        backoff (ExponentialBackoff): Exponential Backoff calculator for network requests.
    """

    QUERY_INTERVAL = 15

    feature_subgroup = app_commands.Group(
        name='ddo',
        description='Commands for Dungeons & Dragons Online',
        guild_only=False
    )

    def __init__(self, bot: DreamBot) -> None:
        """
        The constructor for the DDO class.

        Parameters:
            bot (DreamBot): The Discord bot.
        """

        self.bot = bot
        self.api_data: Dict[Servers, Optional[Dict[str, Any]]]  = {server: None for server in Servers}
        self.backoff = ExponentialBackoff(60 * 60 * 4)
        self.roll_regex = re.compile('(?P<quantity>\d{0,6})d(?P<sides>\d{1,6}) ?(?P<modifier>[-+] ?\d{1,6})?')
        # self.query_ddo_audit.start()  # disable for dev testing

    @commands.hybrid_command(name='roll', help='Simulates rolling dice. Syntax example: 9d6')
    async def roll(self, ctx: Union[Context, Interaction[DreamBot]], *, pattern: str) -> None:
        """
        A method to simulate the rolling of dice.

        Parameters:
            ctx (Context): The invocation context.
            pattern (str): The die pattern to roll. Example: 9d6 -> Nine Six-Sided die.

        Output:
            Success: The result of the die pattern rolled.
            Failure: A description of the syntax error that occurred.

        Returns:
            None.
        """

        match = self.roll_regex.match(pattern)

        if match is None:
            raise commands.UserInputError('Could not extract a valid dice roll pattern.')

        die_quantity = match.group('quantity')
        die_sides = match.group('sides')
        modifier = match.group('modifier')

        # sides is required, quantity and modifier are optional
        die_sides = parse_match(die_sides, 'Die Sides')

        try:
            die_quantity = parse_match(die_quantity, 'Number of Dice')
        except commands.UserInputError:
            die_quantity = 1

        try:
            modifier = parse_match(modifier, 'Modifier', negative_allowed=True)
        except commands.UserInputError:
            modifier = 0

        seed(time())
        die_total = sum(randrange(1, die_sides + 1) for _ in range(die_quantity)) + modifier

        await ctx.send(f'{die_total:,}')

    # noinspection GrazieInspection
    # needs cleanup
    # -> 6/22/24 - ignoring during migration as command is essentially disabled
    @no_type_check
    @commands.is_owner()
    @commands.command(name='ddoitem', help='Pulls basic information about an item in Dungeons & Dragons Online '
                                           'from the wiki')
    async def ddo_item(self, ctx: Context, *, item: str) -> None:
        """
        A method that outputs an embed detailing the properties of an item on the DDOWiki.

        Parameters:
            ctx (Context): The invocation context.
            item (str): The name of the item to return details on.

        Output:
            Success: A discord.Embed detailing the item type, minimum level, and enchantments.
            Failure: A description of the syntax error that occurred.

        Returns:
            None.
        """

        url = 'https://ddowiki.com/page/Item:' + item.replace(' ', '_')
        data = await network_request(self.bot.session, url)
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
            await ctx.send(f'ERROR: Enchantments table not found. Could not fetch item data.')
            return

        # Each enchantment is a table list element. Find the first element, and the end of the last element
        first_index = enchantment_string.find('<li>')
        last_index = enchantment_string.rfind('</li>')

        # If the list indexes are not valid, return an error
        if first_index == -1 or last_index == -1:
            await ctx.send(f'ERROR: Enchantments table was found, but could not find valid enchantments.')
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
                    # These characters are always preceded by a word or a digit
                    # Sometimes, enchantments have a leading space, or a '+' character
                    #   look for 0 or more of these and add them to our match
                    # Finally, Positive Lookbehind to match the closing '>' character preceding our description
                    # Note: This description was written 'backwards', (positive lookbehind occurs first, etc.)
                    result = search("(?<=>)( )*(\+\d+ )*(\w|\d)(.+?)(?=</a>)", element)
                    # If our result is not a Mythic Bonus (these are on nearly every single item), add it
                    if result and str(result.group(0)).find('Mythic') == -1:
                        enchantments.append(result.group(0).strip())

        # Prep other detail variables
        item_type = 'none'
        minimum_level = -1

        # If we have a minimum level string, extract the minimum level using regex
        if minimum_level_string is not None:
            minimum_level = int(search("\d+?(?=(\n</td>))", minimum_level_string).group(0))

        # If we have an item type string, extract the item type using regex
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

        # Create and send our embedded object
        embed = Embed(title=f'**{item}**', url=url, color=0x6879f2)
        embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar.url)
        embed.set_thumbnail(url='https://i.imgur.com/QV6uUZf.png')
        embed.add_field(name='Minimum Level', value=str(minimum_level))
        embed.add_field(name='Item Type', value=item_type)
        embed.add_field(name='Enchantments', value='\n'.join(enchantments))
        embed.set_footer(text="Please report any formatting issues to my owner!")
        await ctx.send(embed=embed)

    @app_commands.command(
        name='lfms',
        description=f'Returns a list of active LFMs for the specified server. '
                    f'Information is populated from \'DDO Audit\' every {QUERY_INTERVAL} seconds.'
    )
    @app_commands.describe(server='The server to fetch LFM data for')
    async def ddo_lfms(self, interaction: Interaction, server: Servers) -> None:
        """
        A method that outputs a list of all active groups on a server.

        Parameters:
            interaction (Interaction): The invocation interaction.
            server (str): The name of the server to return lfms for. Default: 'Khyber'.

        Output:
            Success: A message detailing the lfms per category.
            Failure: A description of the error that occurred.

        Returns:
            None.
        """

        try:
            server_data = self.api_data[server]

            if server_data is None:
                raise ValueError

        except KeyError:
            await ctx.send(f'No Active LFM\'s on {server}!')
            return
        except ValueError:
            await ctx.send('Failed to query DDO Audit API.')
            return

        # Divide the groups into three lists: Raids, Quests, and Groups (No Listed Quest)
        else:
            raids = [q['Quest']['Name'] for q in server_data['Groups'] if
                     q['Quest'] and q['Quest']['GroupSize'] == 'Raid']
            quests = [q['Quest']['Name'] for q in server_data['Groups'] if
                      q['Quest'] and q['Quest']['GroupSize'] != 'Raid']
            groups = [q['Comment'] for q in server_data['Groups'] if not q['Quest'] and q['Comment']]

            # Should a list be empty, append 'None'
            for li in [raids, quests, groups]:
                if not li:
                    li.append('None')

            await ctx.send(f'**Current Raids on {server}:** {", ".join(raids)}\n'
                           f'**Current Quests on {server}:** {", ".join(quests)}\n'
                           f'**Current Groups on {server}:** {", ".join(groups)}\n')

    @commands.command(name='flfms', help=f'Returns a filtered list of active LFMs for the specified server.\n'
                                         f'Optional filters include: LFM Type: (Solo, Quest, Raid), Difficulty: '
                                         f'(Casual, Normal, Hard, Elite, Reaper), and Level: (1-32).\nYou MUST supply a'
                                         f' server.\nValid servers include Argonnessen, Cannith, Ghallanda, Khyber,'
                                         f' Orien, Sarlona, Thelanis, Wayfinder, and Hardcore.\nInformation is '
                                         f'populated from \'DDO Audit\' every {QUERY_INTERVAL} seconds.')
    async def ddo_filter_lfms(self, ctx: Context, *args: str) -> None:
        """
        A method that outputs a list of all active groups on a server that match the specified filters.

        Parameters:
            ctx (Context): The invocation context.
            args (str): The filter options. Options include Type, Difficulty, Level, and a non-optional Server.

        Output:
            Success: A message detailing the filtered lfms.
            Failure: A description syntax error that occurred.

        Returns:
            None.
        """

        # attempt to parse arguments provided
        server = atype = diff = level = None

        # server_data = self.api_data[Servers.Khyber]
        server_data: Dict[str, Any] = dict()

        # build sets for each of our individual filters, as well as a master set of all quests
        # sets are tuples of (LeaderName, QuestName, Difficulty, AdventureType), with LeaderName
        #   included to allow for different hashes of otherwise identical groups

        all_quests = {(q['Leader']['Name'], q['Quest']['Name'], q['Difficulty'], q['Quest']['GroupSize'])
                      for q in server_data['Groups'] if q['Quest']}
        atypes = {(q['Leader']['Name'], q['Quest']['Name'], q['Difficulty'], q['Quest']['GroupSize'])
                  for q in server_data['Groups'] if q['Quest'] and atype and q['Quest']['GroupSize'] == atype}
        diffs = {(q['Leader']['Name'], q['Quest']['Name'], q['Difficulty'], q['Quest']['GroupSize'])
                 for q in server_data['Groups'] if q['Quest'] and diff and q['Difficulty'] == diff}
        levels = {(q['Leader']['Name'], q['Quest']['Name'], q['Difficulty'], q['Quest']['GroupSize']) for q
                  in server_data['Groups'] if q['Quest'] and level and q['MinimumLevel'] <= level <= q['MaximumLevel']}

        # if our value is not None, start performing intersection calculations on the full set
        for filtered_set, value in [(atypes, atype), (diffs, diff), (levels, level)]:
            if value is not None:
                all_quests.intersection_update(filtered_set)

        if not all_quests:
            await ctx.send(f'**Filtered Results on {server}:** None')
        else:
            await ctx.send(f'**Filtered Results on {server}:** {", ".join(x[1] for x in all_quests)}')

    @tasks.loop(seconds=QUERY_INTERVAL)
    async def query_ddo_audit(self) -> None:
        """
        A discord.ext.tasks loop that queries the DDOAudit API for LFM information.
        Executes every {QUERY_INTERVAL} seconds to comply with DDOAudit's rate limit.

        Parameters:
            None.

        Returns:
            None.
        """

        async def backoff(current_server: Servers) -> None:
            """
            A local function for handling exponential backoff during network errors.
            Backoff behavior is desirable during any exception, though other behavior is exception-specific.

            Parameters:
                current_server (str) The current iteration's server.

            Returns:
                None.
            """

            # if we backoff for more than 5 minutes, invalidate all LFM data
            # this works out to roughly the 4th backoff
            # this is also when we care about start caring about log entries
            self.backoff.next_backoff()

            if self.backoff.backoff_count >= 4:
                self.api_data = {s: None for s in Servers}
                bot_logger.warning(
                    f'DDOAudit Total Backoff Duration Will Exceed 5 Minutes. '
                    f'Clearing all LFM data and backing off for {self.backoff.str_time}.'
                )
            else:
                self.api_data[current_server] = None

            await sleep(self.backoff.total_backoff_seconds)

        server = list(Servers)[self.query_ddo_audit.current_loop % len(Servers)]

        try:
            self.api_data[server] = await network_request(
                self.bot.session,
                f'https://api.ddoaudit.com/groups/{server.value.lower()}',
                return_type=NetworkReturnType.JSON, ssl=False
            )
            self.backoff.reset()

        except ClientError:
            await backoff(server)

        except (JSONDecodeError, UnicodeError, TimeoutError) as e:
            bot_logger.warning(f'DDOAudit Query[{server}] Error: {type(e)} - {e}')
            await backoff(server)

        except Exception as e:
            bot_logger.error(f'DDOAudit Query[{server}] Unhandled Exception: {type(e)} - {e}')
            await self.bot.report_exception(e)
            await backoff(server)

    async def cog_unload(self) -> None:
        """
        A method detailing custom extension unloading procedures.
        Clears internal caches and immediately and forcefully exits any discord.ext.tasks.

        Parameters:
            None.

        Returns:
            None.
        """

        self.query_ddo_audit.cancel()
        self.api_data = dict()

        bot_logger.info('Completed Unload for Cog: DDO')


def parse_match(match: str, match_name: str, negative_allowed: bool = False) -> int:
    """
    Parses a match string to a valid integer value.

    Parameters:
        match (str): The match string.
        match_name (str): The name of match being parsed.
        negative_allowed (bool): Whether negative values are allowed.

    Throws:
        commands.UserInputError.

    Returns:
        (int).
    """

    try:
        base_value = int(match.replace(' ', ''))
    except (ValueError, AttributeError):
        raise commands.UserInputError(f'Could not parse {match_name}.')

    if not negative_allowed and base_value <= 0:
        raise commands.UserInputError(f'{match_name} was out-of-bounds (negative or zero).')

    return base_value


async def setup(bot: DreamBot) -> None:
    """
    A setup function that allows the cog to be treated as an extension.

    Parameters:
        bot (DreamBot): The bot the cog should be added to.

    Returns:
        None.
    """

    await bot.add_cog(DDO(bot))
    bot_logger.info('Completed Setup for Cog: DDO')
