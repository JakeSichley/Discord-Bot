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

from collections import defaultdict
from dataclasses import dataclass
from json.decoder import JSONDecodeError
from typing import List, Optional, Dict

import aiosqlite
import discord
from aiohttp import ClientError
from aiosqlite import Error as aiosqliteError, IntegrityError
from discord import app_commands, Interaction
from discord.app_commands import Choice, Transform, Range
from discord.ext import commands, tasks
from discord.utils import utcnow

from dreambot import DreamBot
from utils.transformers import RunescapeNumberTransformer, HumanDatetimeDuration, SentinelRange
from utils.database.helpers import execute_query, typed_retrieve_query
from utils.database.table_dataclasses import RunescapeAlert
from utils.logging_formatter import bot_logger
from utils.network_utils import network_request, NetworkReturnType, ExponentialBackoff
from utils.utils import format_unix_dt, generate_autocomplete_choices

FIVE_MINUTES = 300
ONE_DAY = 86_400
ONE_YEAR = 31_556_926


# TODO: Add frequently accessed item_id's (global? user?) for /runescape_item

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


class Runescape(commands.GroupCog, group_name='runescape', group_description='Commands for Old School Runescape'):
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
    CACHE_TTL = 120

    alert_subgroup = app_commands.Group(name='alert', description='Commands for managing item alerts')

    def __init__(self, bot: DreamBot) -> None:
        """
        The constructor for the Runescape class.

        Parameters:
            bot (DreamBot): The Discord bot.
        """

        self.bot = bot
        self.item_data: Dict[int, RunescapeItem] = {}
        self.item_names_to_ids: Dict[str, int] = {}
        self.alerts: Dict[int, List[RunescapeAlert]] = defaultdict(list)  # key: user_id
        """
        alerts can be |owner_id: [Alert]| - don't need O(1) |item_id: [Alert]| access
        Allows O(1) access for alert edit, delete access
        Flatten values (iter.chain.from_iter) allows for O(n) alert checking, which is best case
        """
        self.backoff = ExponentialBackoff(3600 * 4)
        self.query_mapping_data.start()
        self.query_market_data.start()

    async def cog_load(self) -> None:
        """
        A special method that acts as a cog local post-invoke hook.

        Parameters:
            None.

        Returns:
            None.
        """

        alerts = await typed_retrieve_query(
            self.bot.database,
            RunescapeAlert,
            'SELECT * FROM RUNESCAPE_ALERTS'
        )

        for alert in alerts:
            self.alerts[alert.owner_id].append(alert)

    @alert_subgroup.command(name='add', description='Registers an item for market alerts')
    @app_commands.describe(
        item_id='The item to receive alerts for',
        low_price='Optional: Trigger an alert if the instant buy price goes below this',
        high_price='Optional: Trigger an alert if the instant sell price goes above this',
        alert_frequency='Optional: How frequently you should be notified that the price has exceeded a target.',
        maximum_alerts='Optional: Remove the alert after receiving this many notifications'
    )
    @app_commands.rename(item_id='item')
    async def add_alert(
            self,
            interaction: Interaction,
            item_id: int,
            low_price: Optional[Transform[int, RunescapeNumberTransformer]] = None,
            high_price: Optional[Transform[int, RunescapeNumberTransformer]] = None,
            alert_frequency: Optional[Transform[int, HumanDatetimeDuration(FIVE_MINUTES, ONE_YEAR)]] = None,
            maximum_alerts: Optional[Range[int, 1, 9000]] = None  # just over a month of max frequency alerts
    ) -> None:
        """
        TODO: DOCUMENT
        Retrieves market and basic data about an Old School Runescape item.

        Parameters:
            interaction (Interaction): The invocation interaction.
            item_id (int): The internal id of the item.
            low_price
            high_price
            alert_frequency
            maximum_alerts

        Returns:
            None.
        """

        # todo: expiring cache for existing alerts for autocomplete and error checking

        if item_id not in self.item_data:
            await interaction.response.send_message("I'm unable to find that item.", ephemeral=True)
            return

        try:
            await execute_query(
                self.bot.database,
                'INSERT INTO RUNESCAPE_ALERTS ('
                'OWNER_ID,'
                'CREATED,'
                'ITEM_ID,'
                'INITIAL_LOW,'
                'INITIAL_HIGH,'
                'TARGET_LOW,'
                'TARGET_HIGH,'
                'FREQUENCY,'
                'MAXIMUM_ALERTS,'
                'LAST_ALERT'
                ') VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (
                    interaction.user.id,
                    int(utcnow().timestamp()),
                    item_id,
                    self.item_data[item_id].low,
                    self.item_data[item_id].high,
                    low_price,
                    high_price,
                    alert_frequency,
                    maximum_alerts,
                    None
                ),
                errors_to_suppress=aiosqlite.IntegrityError
            )
        except aiosqliteError as e:
            if isinstance(e, IntegrityError):
                await interaction.response.send_message('You already have an alert for this item.', ephemeral=True)
            else:
                await interaction.response.send_message('Failed to create an alert for this item.', ephemeral=True)
        else:
            await interaction.response.send_message('Successfully created alert.', ephemeral=True)
            self.alerts[interaction.user.id].append(
                RunescapeAlert(
                    interaction.user.id,
                    int(utcnow().timestamp()),
                    item_id,
                    self.item_data[item_id].low,
                    self.item_data[item_id].high,
                    low_price,
                    high_price,
                    alert_frequency,
                    maximum_alerts,
                    None
                )
            )

    @alert_subgroup.command(name='edit', description='Edit an existing item alert. Use "-1" to remove a value.')
    @app_commands.describe(
        item_id='The item to edit alerts for',
        low_price='Optional: Trigger an alert if the instant buy price goes below this',
        high_price='Optional: Trigger an alert if the instant sell price goes above this',
        alert_frequency='Optional: How frequently you should be notified that the price has exceeded a target.',
        maximum_alerts='Optional: Remove the alert after receiving this many notifications'
    )
    @app_commands.rename(item_id='item')
    async def edit_alert(
            self,
            interaction: Interaction,
            item_id: int,
            low_price: Optional[Transform[int, RunescapeNumberTransformer(sentinel_value=-1)]] = None,
            high_price: Optional[Transform[int, RunescapeNumberTransformer(sentinel_value=-1)]] = None,
            alert_frequency: Optional[
                Transform[int, HumanDatetimeDuration(FIVE_MINUTES, ONE_YEAR, sentinel_value=-1)]
            ] = None,
            maximum_alerts: Optional[Transform[int, SentinelRange(1, 9000, sentinel_value=-1)]] = None
    ) -> None:
        pass

    @alert_subgroup.command(name='delete', description='Deletes an existing item alert.')
    @app_commands.describe(item_id='The item to delete alerts for')
    @app_commands.rename(item_id='item')
    async def delete_alert(self, interaction: Interaction, item_id: int) -> None:
        """
        Deletes an existing alert.

        Parameters:
            interaction (Interaction): The invocation interaction.
            item_id (int): The internal id of the item.

        Returns:
            None.
        """

        if item_id not in self.item_data:
            await interaction.response.send_message("I'm unable to find that item.", ephemeral=True)
            return

        try:
            await execute_query(
                self.bot.database,
                'DELETE FROM RUNESCAPE_ALERTS WHERE OWNER_ID=? AND ITEM_ID=?',
                (interaction.user.id, item_id)
            )
        except aiosqliteError:
            await interaction.response.send_message('Failed to delete the alert for this item.', ephemeral=True)
        else:
            await interaction.response.send_message('Successfully deleted alert.', ephemeral=True)
        finally:
            self.alerts[interaction.user.id] = [x for x in self.alerts[interaction.user.id] if x.item_id != item_id]

    @app_commands.command(name='item', description='Returns basic data and market information for a given item')
    @app_commands.describe(item_id='The item to retrieve data for')
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
            await interaction.response.send_message("I'm unable to find that item.", ephemeral=True)
            return

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
    @edit_alert.autocomplete('item_id')
    @delete_alert.autocomplete('item_id')
    async def runescape_alert_autocomplete(self, interaction: Interaction, current: str) -> List[Choice]:
        """
        Retrieves market and basic data about an Old School Runescape item.

        Parameters:
            interaction (Interaction): The invocation interaction.
            current (str): The user's current input.

        Returns:
            (List[Choice]): A list of relevant Choices for the current input.
        """

        # check cache
        if len(self.alerts[interaction.user.id]) == 0:
            return []

        alerts = self.alerts[interaction.user.id]

        if not current:
            return [Choice(name=self.item_data[x.item_id].name, value=x.item_id) for x in alerts]

        return generate_autocomplete_choices(
            current,
            [(self.item_data[x.item_id].name, x.item_id) for x in alerts],
            minimum_threshold=100
        )

    # noinspection PyUnusedLocal
    @runescape_item.autocomplete('item_id')
    @add_alert.autocomplete('item_id')
    async def runescape_item_autocomplete(self, interaction: Interaction, current: str) -> List[Choice]:
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

        return generate_autocomplete_choices(
            current,
            [(self.item_data[key].name, key) for key in self.item_data.keys()]
        )

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
