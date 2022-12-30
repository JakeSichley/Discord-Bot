"""
MIT License

Copyright (c) 2019-2022 Jake Sichley

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

from dataclasses import dataclass
from json.decoder import JSONDecodeError
from typing import List, Optional, Dict

import discord
from aiohttp import ClientError
from discord import app_commands, Interaction
from discord.app_commands import Choice
from discord.ext import commands, tasks

from dreambot import DreamBot
from utils.logging_formatter import bot_logger
from utils.network_utils import network_request, NetworkReturnType, ExponentialBackoff
from utils.utils import format_unix_dt, AutocompleteModel


@dataclass
class ItemMarketData:
    """
    A dataclass that represents the market data associated with an Old School Runescape Item.

    Attributes:
        high (Optional[int]): The item's most recent "instant-buy" price.
        highTime (Optional[int]): The time the item's most recent "instant-buy" transaction occurred.
        low (Optional[int]): The item's most recent "instant-sell" price.
        lowTime (Optional[int]): The time the item's most recent "instant-sell" transaction occurred.
    """

    high: Optional[int] = None
    highTime: Optional[int] = None
    low: Optional[int] = None
    lowTime: Optional[int] = None


@dataclass
class RunescapeItem:
    """
    A dataclass that represents the raw components of an Old School Runescape Item.

    Attributes:
        id (int): The item's internal id.
        name (str): The item's name.
        examine (str): The item's description.
        icon (str): The item's icon name on the Old School Wiki.
        members (bool): Whether the item is members-only.
        value (int): The item's base value.
        limit (Optional[int]): The item's Grand Exchange limit, if any.
        lowalch (Optional[int]): The item's low alchemy value, if any.
        highalch (Optional[int]): The item's high alchemy value, if any.
        high (Optional[int]): The item's most recent "instant-buy" price.
        highTime (Optional[int]): The time the item's most recent "instant-buy" transaction occurred.
        low (Optional[int]): The item's most recent "instant-sell" price.
        lowTime (Optional[int]): The time the item's most recent "instant-sell" transaction occurred.
    """

    id: int
    name: str
    examine: str
    icon: str
    members: bool
    value: int
    limit: Optional[int] = None
    lowalch: Optional[int] = None
    highalch: Optional[int] = None
    high: Optional[int] = None
    highTime: Optional[int] = None
    low: Optional[int] = None
    lowTime: Optional[int] = None

    def update_with_mapping_fragment(self, fragment: 'RunescapeItem') -> None:
        """
        A method that updates the item's internal data.

        Parameters:
            fragment (RunescapeItem): The RunescapeItem fragment to update the item with.

        Returns:
            None.
        """

        self.id = fragment.id
        self.name = fragment.name
        self.examine = fragment.examine
        self.icon = fragment.icon
        self.members = fragment.members
        self.value = fragment.value
        self.limit = fragment.limit
        self.lowalch = fragment.lowalch
        self.highalch = fragment.highalch

    def update_with_market_fragment(self, fragment: ItemMarketData) -> None:
        """
        A method that updates the item's market data.

        Parameters:
            fragment (ItemMarketData): The ItemMarketData fragment to update the item with.

        Returns:
            None.
        """

        self.high = fragment.high
        self.highTime = fragment.highTime
        self.low = fragment.low
        self.lowTime = fragment.lowTime


class Runescape(commands.Cog):
    """
    A Cogs class that contains Old School Runescape commands.

    Constants:
        MAPPING_QUERY_INTERVAL (int): How frequently API data from DDOAudit should be queried.

    Attributes:
        bot (DreamBot): The Discord bot.
        item_data.
        query_ddo_audit (ext.tasks): Stores the task that queries DDOAudit every {QUERY_INTERVAL} seconds.
        backoff (ExponentialBackoff): Exponential Backoff calculator for network requests.
    """

    MAPPING_QUERY_INTERVAL = 60 * 60  # 1 hour
    MARKET_QUERY_INTERVAL = 60  # 1 minute

    def __init__(self, bot: DreamBot) -> None:
        """
        The constructor for the Runescape class.

        Parameters:
            bot (DreamBot): The Discord bot.
        """

        self.bot = bot
        self.item_data: Dict[int, RunescapeItem] = {}
        self.item_names_to_ids: Dict[str, int] = {}
        self.backoff = ExponentialBackoff(3600 * 4)
        self.query_mapping_data.start()
        self.query_market_data.start()

    @app_commands.command(
        name='runescape_item', description='Returns basic data and market information for a given item'
    )
    @app_commands.describe(item_id='The item to retrieve data for.')
    @app_commands.rename(item_id='item')
    async def runescape_item(self, interaction: Interaction, item_id: int) -> None:
        """
        Retrieves market and basic data about an Old School Runescape item.

        Parameters:
            interaction (Interaction): The invocation interaction.
            item_id (int): The internal id of the item.

        Returns:
            None.
        """

        if item_id not in self.item_data:
            await interaction.response.send_message("I'm unable to find that item.")
        else:
            item = self.item_data[item_id]
            embed = discord.Embed(
                title=item.name,
                color=0x971212,
                url=f'https://oldschool.runescape.wiki/w/{item.name.replace(" ", "_")}'
            )
            embed.description = item.examine
            embed.set_thumbnail(url=f'https://static.runelite.net/cache/item/icon/{item_id}.png')

            buy_price = f'{item.high:,} coins' if item.high else 'N/A'
            embed.add_field(name='Buy Price', value=buy_price)

            sell_price = f'{item.low:,} coins' if item.low else 'N/A'
            embed.add_field(name='Sell Price', value=sell_price)

            limit = f'{item.limit:,}' if item.limit else 'N/A'
            embed.add_field(name='Buy Limit', value=limit)

            buy_time = format_unix_dt(item.highTime, 'R') if item.highTime else 'N/A'
            embed.add_field(name='Buy Time', value=buy_time)

            sell_time = format_unix_dt(item.lowTime, 'R') if item.lowTime else 'N/A'
            embed.add_field(name='Sell Time', value=sell_time)

            embed.add_field(name='​', value='​')

            high_alch = f'{item.highalch:,} coins' if item.highalch else 'N/A'
            embed.add_field(name='High Alch', value=high_alch)

            low_alch = f'{item.lowalch:,} coins' if item.lowalch else 'N/A'
            embed.add_field(name='Low Alch', value=low_alch)

            value = f'{item.value:,} coins' if item.value else 'N/A'
            embed.add_field(name='Value', value=value)

            embed.set_footer(text='Please report any issues to my owner!')

            await interaction.response.send_message(embed=embed)

    # noinspection PyUnusedLocal
    @runescape_item.autocomplete('item_id')
    async def runescape_item_item_autocomplete(self, interaction: Interaction, current: str) -> List[Choice]:
        """
        Retrieves market and basic data about an Old School Runescape item.

        Parameters:
            interaction (Interaction): The invocation interaction.
            current (str): The user's current input.

        Returns:
            (List[Choice]): A list of relevant Choices for the current input.
        """

        if not current:
            return [Choice(name=self.item_data[x].name, value=x) for x in self.item_data][:25]

        ratios = sorted([
            AutocompleteModel(self.item_data[x].name, x, current) for x in self.item_data
        ], reverse=True)

        return [x.to_choice() for x in ratios[:25]]

    @tasks.loop(seconds=MAPPING_QUERY_INTERVAL)
    async def query_mapping_data(self) -> None:
        """
        A discord.ext.tasks loop that queries the OSRS Wiki API for item information.
        Executes every {MAPPING_QUERY_INTERVAL} seconds.

        Parameters:
            None.

        Returns:
            None.
        """

        try:
            mapping_response = await network_request(
                self.bot.session,
                'https://prices.runescape.wiki/api/v1/osrs/mapping',
                return_type=NetworkReturnType.JSON
            )

            for item in [RunescapeItem(**item) for item in mapping_response if 'id' in item]:
                self.item_names_to_ids[item.name] = item.id

                if item.id in self.item_data:
                    self.item_data[item.id].update_with_mapping_fragment(item)
                else:
                    self.item_data[item.id] = item

        except ClientError:
            pass

        except TypeError as e:
            bot_logger.warning(f'OSRS RunescapeItem Init Error: {e}')

        except (JSONDecodeError, UnicodeError) as e:
            bot_logger.warning(f'OSRS Mapping Query Error: {type(e)} - {e}')

        except Exception as e:
            bot_logger.error(f'OSRS Mapping Query Unhandled Exception: {type(e)} - {e}')
            await self.bot.report_exception(e)

    @tasks.loop(seconds=MARKET_QUERY_INTERVAL)
    async def query_market_data(self) -> None:
        """
        A discord.ext.tasks loop that queries the OSRS Wiki API for item market data.
        Executes every {MARKET_QUERY_INTERVAL} seconds.

        Parameters:
            None.

        Returns:
            None.
        """

        try:
            market_response = await network_request(
                self.bot.session,
                'https://prices.runescape.wiki/api/v1/osrs/latest',
                return_type=NetworkReturnType.JSON
            )

            for item_id in [item_id for item_id in market_response['data'] if int(item_id) in self.item_data]:
                fragment = ItemMarketData(**market_response['data'][item_id])
                self.item_data[int(item_id)].update_with_market_fragment(fragment)

        except ClientError:
            pass

        except TypeError as e:
            bot_logger.warning(f'OSRS RunescapeItem Init Error: {e}')

        except (JSONDecodeError, UnicodeError) as e:
            bot_logger.warning(f'OSRS Mapping Query Error: {type(e)} - {e}')

        except Exception as e:
            bot_logger.error(f'OSRS Mapping Query Unhandled Exception: {type(e)} - {e}')
            await self.bot.report_exception(e)

    async def cog_unload(self) -> None:
        """
        A method detailing custom extension unloading procedures.
        Clears internal caches and immediately and forcefully exits any discord.ext.tasks.

        Parameters:
            None.

        Returns:
            None.
        """

        self.query_mapping_data.cancel()
        self.query_market_data.cancel()

        bot_logger.info('Completed Unload for Cog: Runescape')


async def setup(bot: DreamBot) -> None:
    """
    A setup function that allows the cog to be treated as an extension.

    Parameters:
        bot (DreamBot): The bot the cog should be added to.

    Returns:
        None.
    """

    await bot.add_cog(Runescape(bot))
    bot_logger.info('Completed Setup for Cog: Runescape')
