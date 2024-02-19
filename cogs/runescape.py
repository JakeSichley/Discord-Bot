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

from asyncio import Event, TimeoutError
from collections import defaultdict
from contextlib import suppress
from itertools import chain
from json.decoder import JSONDecodeError
from typing import List, Optional, Dict, Literal, Tuple

import aiosqlite
import discord
from aiohttp import ClientError
from aiosqlite import Error as aiosqliteError, IntegrityError
from discord import app_commands, Interaction
from discord.app_commands import Choice, Transform, Range
from discord.ext import commands, tasks
from discord.utils import utcnow
from humanfriendly import format_timespan

from dreambot import DreamBot
from utils.database.helpers import execute_query, typed_retrieve_query, typed_retrieve_one_query
from utils.database.table_dataclasses import RunescapeAlert
from utils.enums.network_return_type import NetworkReturnType
from utils.logging_formatter import bot_logger
from utils.network_utils import network_request, ExponentialBackoff
from utils.runescape.runescape_data_classes import (
    RunescapeItem, ItemMarketData, AlertEmbedFragment, RunescapeHerbComparison
)
from utils.runescape.runescape_herbs import generate_herb_comparison
from utils.transformers import RunescapeNumberTransformer, HumanDatetimeDuration, SentinelRange
from utils.utils import format_unix_dt, generate_autocomplete_choices

FIVE_MINUTES = 300
ONE_YEAR = 31_556_926
MIN_ALERTS = 1
MAX_ALERTS = 2_147_483_647


# TODO: Add frequently accessed item_id's (global? user?) for /runescape_item

# autocomplete namespaces result in a lot of duplicated code
# noinspection DuplicatedCode
# noinspection PyUnusedLocal
class Runescape(commands.GroupCog, group_name='runescape', group_description='Commands for Old School Runescape'):
    """
    A Cogs class that contains Old School Runescape commands.

    Constants:
        MAPPING_QUERY_INTERVAL (int): How frequently item data from the OSRS Wiki's API should be queried.
        MARKET_QUERY_INTERVAL (int): How frequently market data from the OSRS Wiki's API should be queried.
        alert_subgroup (app_commands.Group): The Runescape Alert command group.

    Attributes:
        bot (DreamBot): The Discord bot.
        item_data (Dict[int, RunescapeItem]): A mapping of Runescape items.
        item_names_to_ids (Dict[str, int]): A lookup mapping of Runescape item names.
        alerts (Dict[int, Dict[int, RunescapeAlert]]): A mapping of user alerts for Runescape items.
        backoff (ExponentialBackoff): Exponential Backoff calculator for network requests.
    """

    MAPPING_QUERY_INTERVAL = 60 * 60  # 1 hour
    MARKET_QUERY_INTERVAL = 60  # 1 minute

    alert_subgroup = app_commands.Group(name='alert', description='Commands for managing item alerts')

    def __init__(self, bot: DreamBot) -> None:
        """
        The constructor for the Runescape class.

        Parameters:
            bot (DreamBot): The Discord bot.
        """

        self.bot = bot
        self.item_data: Dict[int, RunescapeItem] = {}  # [item_id: RunescapeItem]
        self.item_names_to_ids: Dict[str, int] = {}  # [item_name: item_id]
        self.alerts: Dict[int, Dict[int, RunescapeAlert]] = defaultdict(dict)  # [user_id: [item_id: RunescapeAlert]]
        self.backoff = ExponentialBackoff(3600 * 4)
        self.initial_mapping_data_event: Event = Event()
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
            self.alerts[alert.owner_id][alert.item_id] = alert

    """
    MARK: - App Commands
    """

    @app_commands.command(name='item', description='Returns basic data and market information for a given item')
    @app_commands.describe(item_id='The item to retrieve data for')
    @app_commands.rename(item_id='item')
    async def runescape_item(self, interaction: Interaction[DreamBot], item_id: int) -> None:
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
            description=item.examine,
            color=0x971212,
            url=f'https://oldschool.runescape.wiki/w/{item.name.replace(" ", "_")}'
        )
        embed.set_thumbnail(url=f'https://static.runelite.net/cache/item/icon/{item_id}.png')

        embed.add_field(name='Buy Price', value=f'{item.high:,} coins' if item.high else 'N/A')
        embed.add_field(name='Sell Price', value=f'{item.low:,} coins' if item.low else 'N/A')
        embed.add_field(name='Buy Limit', value=f'{item.limit:,}' if item.limit else 'N/A')
        embed.add_field(name='Buy Time', value=format_unix_dt(item.highTime, 'R') if item.highTime else 'N/A')
        embed.add_field(name='Sell Time', value=format_unix_dt(item.lowTime, 'R') if item.lowTime else 'N/A')
        embed.add_field(name='​', value='​')
        embed.add_field(name='High Alch', value=f'{item.highalch:,} coins' if item.highalch else 'N/A')
        embed.add_field(name='Low Alch', value=f'{item.lowalch:,} coins' if item.lowalch else 'N/A')
        embed.add_field(name='Value', value=f'{item.value:,} coins' if item.value else 'N/A')
        embed.set_footer(text='Please report any issues to my owner!')

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name='herb_comparison', description='Compares profitability for various herbs')
    @app_commands.describe(patches='The number of herb patches to use in the calculation')
    @app_commands.describe(average_herbs='The average number of herbs harvested per patch')
    async def runescape_herb_comparison(
            self,
            interaction: Interaction[DreamBot],
            patches: Optional[Range[int, 1, 9]] = 9,
            average_herbs: Optional[Range[int, 1, 50]] = 8
    ) -> None:
        """
        Generates an embed detailing the profitability of each herb based on current market data.

        Parameters:
            interaction (Interaction): The invocation interaction.
            patches (int): The number of herb patches to use in the calculation.
            average_herbs (int): The average number of herbs harvested per patch.

        Returns:
            None.
        """

        herb_comparisons: List[RunescapeHerbComparison] = generate_herb_comparison(
            self.item_data,
            patches,
            average_herbs
        )
        herb_comparisons.sort(reverse=True, key=lambda x: x.max)

        patches_pluralized = 'patch' if patches == 1 else 'patches'

        embed = discord.Embed(
            title="Old School Runescape Herb Profitability Comparison",
            description=f"**{patches} {patches_pluralized}** with **{average_herbs} herbs** per patch based on "
                        f"current market data.",
            color=0x971212
        )
        embed.set_thumbnail(url="https://oldschool.runescape.wiki/images/Herblore_icon_%28detail%29.png")
        embed.set_footer(text="Please report any issues to my owner!")

        embed.add_field(name='Herb', value='\n'.join(f'{x.emoji} {x.name}' for x in herb_comparisons))
        embed.add_field(
            name='Profit (Clean)', value='\n'.join(f'{x.clean_profit:,}' for x in herb_comparisons)
        )
        embed.add_field(
            name='Profit (Grimy)', value='\n'.join(f'**{x.grimy_profit:,}**' for x in herb_comparisons)
        )

        # for comparison in herb_comparisons[:8]:
        #     embed.add_field(name=f'{comparison.name} Cost', value=f'{comparison.cost:,}')
        #     embed.add_field(name=f'{comparison.name} Profit (Clean)', value=)
        #     embed.add_field(name=f'{comparison.name} Profit (Grimy)', value=f'{comparison.grimy_profit:,}')

        await interaction.response.send_message(embed=embed)

    """
    MARK: - Alerts
    """

    @alert_subgroup.command(name='add', description='Registers an item for market alerts')
    @app_commands.describe(
        item_id='The item to receive alerts for',
        low_price='Optional: Trigger an alert if the instant buy price goes below this value',
        high_price='Optional: Trigger an alert if the instant sell price goes above this value',
        alert_frequency='Optional: How frequently you should be notified that the price has exceeded a target',
        maximum_alerts='Optional: Remove the alert after receiving this many notifications'
    )
    @app_commands.rename(item_id='item')
    async def add_alert(
            self,
            interaction: Interaction[DreamBot],
            item_id: int,
            low_price: Optional[Transform[int, RunescapeNumberTransformer]] = None,
            high_price: Optional[Transform[int, RunescapeNumberTransformer]] = None,
            alert_frequency: Optional[Transform[int, HumanDatetimeDuration(FIVE_MINUTES, ONE_YEAR)]] = None,
            maximum_alerts: Optional[Range[int, MIN_ALERTS, MAX_ALERTS]] = None
    ) -> None:
        """
        Creates a market alert for a Runescape item.

        Parameters:
            interaction (Interaction): The invocation interaction.
            item_id (int): The internal id of the item.
            low_price (Optional[int]): Trigger an alert if the item's instant buy price goes below this.
            high_price (Optional[int]): Trigger an alert if the item's instant sell price goes above this.
            alert_frequency (Optional[int]): How frequently an alert should be triggered (in seconds).
            maximum_alerts (Optional[int]): The maximum number of alerts to trigger before deleting this alert.

        Returns:
            None.
        """

        alert = RunescapeAlert(
            interaction.user.id,
            int(utcnow().timestamp()),
            item_id,
            0,
            maximum_alerts,
            None,
            alert_frequency,
            self.item_data[item_id].low,
            self.item_data[item_id].high,
            low_price,
            high_price
        )

        if item_id not in self.item_data:
            await interaction.response.send_message("I'm unable to find that item.", ephemeral=True)
            return

        if low_price is not None and high_price is not None and low_price >= high_price:
            await interaction.response.send_message(
                'You cannot have a low price greater than or equal to the high price.', ephemeral=True
            )
            return

        try:
            await execute_query(
                self.bot.database,
                'INSERT INTO RUNESCAPE_ALERTS VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                alert.unpack(),
                errors_to_suppress=aiosqlite.IntegrityError
            )
        except aiosqliteError as e:
            if isinstance(e, IntegrityError):
                await interaction.response.send_message('You already have an alert for this item.', ephemeral=True)
            else:
                await interaction.response.send_message('Failed to create an alert for this item.', ephemeral=True)
        else:
            await interaction.response.send_message('Successfully created alert.', ephemeral=True)
            self.alerts[interaction.user.id][item_id] = alert

    @alert_subgroup.command(
        name='edit', description='Edit an existing item alert. You do not have to use autocomplete options.'
    )
    @app_commands.describe(
        item_id='The item to edit alerts for',
        low_price='Optional: Trigger an alert if the instant buy price goes below this value',
        high_price='Optional: Trigger an alert if the instant sell price goes above this value',
        alert_frequency='Optional: How frequently you should be notified that the price has exceeded a target',
        maximum_alerts='Optional: Remove the alert after receiving this many notifications. Resets existing count'
    )
    @app_commands.rename(item_id='item')
    async def edit_alert(
            self,
            interaction: Interaction[DreamBot],
            item_id: int,
            low_price: Optional[Transform[int, RunescapeNumberTransformer(sentinel_value=-1)]] = None,
            high_price: Optional[Transform[int, RunescapeNumberTransformer(sentinel_value=-1)]] = None,
            alert_frequency: Optional[
                Transform[int, HumanDatetimeDuration(FIVE_MINUTES, ONE_YEAR, sentinel_value='-1')]
            ] = None,
            maximum_alerts: Optional[Transform[int, SentinelRange(MIN_ALERTS, MAX_ALERTS, sentinel_value=-1)]] = None
    ) -> None:
        """
        Edits an existing market alert for a Runescape item.

        Parameters:
            interaction (Interaction): The invocation interaction.
            item_id (int): The internal id of the item.
            low_price (Optional[int]): Trigger an alert if the item's instant buy price goes below this.
            high_price (Optional[int]): Trigger an alert if the item's instant sell price goes above this.
            alert_frequency (Optional[int]): How frequently an alert should be triggered (in seconds).
            maximum_alerts (Optional[int]): The maximum number of alerts to trigger before deleting this alert.

        Returns:
            None.
        """

        def parse_sentinel_option(existing_value: Optional[int], option: Optional[int]) -> Optional[int]:
            """
            Parses a sentinel value to update alert values.

            Parameters:
                existing_value (Optional[int]): The existing alert's value.
                option (Optional[int]): The new option's value.

            Returns:
                (Optional[int]): The parsed value.
            """

            if option == -1:
                return None

            if option is None:
                return existing_value

            return option

        if item_id not in self.item_data:
            await interaction.response.send_message("I'm unable to find that item.", ephemeral=True)
            return

        if low_price is not None and high_price is not None and low_price >= high_price:
            await interaction.response.send_message(
                'You cannot have a low price greater than or equal to the high price.', ephemeral=True
            )
            return

        try:
            alert = await typed_retrieve_one_query(
                self.bot.database,
                RunescapeAlert,
                'SELECT * FROM RUNESCAPE_ALERTS WHERE OWNER_ID=? AND ITEM_ID=? LIMIT 1',
                (interaction.user.id, item_id)
            )
        except aiosqliteError:
            await interaction.response.send_message('Failed to find an alert for this item.', ephemeral=True)
            return

        alert.target_low = parse_sentinel_option(alert.target_low, low_price)
        alert.target_high = parse_sentinel_option(alert.target_high, high_price)
        alert.frequency = parse_sentinel_option(alert.frequency, alert_frequency)
        alert.maximum_alerts = parse_sentinel_option(alert.maximum_alerts, maximum_alerts)

        try:
            await execute_query(
                self.bot.database,
                'INSERT OR REPLACE INTO RUNESCAPE_ALERTS VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                alert.unpack()
            )
        except aiosqliteError:
            await interaction.response.send_message('Failed to update the alert.', ephemeral=True)
        else:
            await interaction.response.send_message('Successfully updated alert.', ephemeral=True)
            self.alerts[interaction.user.id][item_id] = alert

    @alert_subgroup.command(name='view', description='Views an existing item alert.')
    @app_commands.describe(item_id='The item to view an alert for')
    @app_commands.rename(item_id='item')
    async def view_alert(self, interaction: Interaction[DreamBot], item_id: int) -> None:
        """
        Views an existing market alert for a Runescape item.

        Parameters:
            interaction (Interaction): The invocation interaction.
            item_id (int): The internal id of the item.

        Returns:
            None.
        """

        if item_id not in self.alerts[interaction.user.id] or item_id not in self.item_data:
            await interaction.response.send_message("I'm unable to find that alert.", ephemeral=True)
            return

        alert = self.alerts[interaction.user.id][item_id]
        item = self.item_data[item_id]

        embed = discord.Embed(
            title=item.name,
            description=item.examine,
            color=0x971212,
            url=f'https://oldschool.runescape.wiki/w/{item.name.replace(" ", "_")}'
        )
        embed.set_thumbnail(url=f'https://static.runelite.net/cache/item/icon/{item_id}.png')

        embed.add_field(name='Alert Buy Price', value=f'{alert.target_high:,} coins' if alert.target_high else 'N/A')
        embed.add_field(name='Alert Sell Price', value=f'{alert.target_low:,} coins' if alert.target_low else 'N/A')
        embed.add_field(name='​', value='​')
        embed.add_field(name='Initial Buy Price', value=f'{alert.initial_low:,} coins' if alert.initial_low else 'N/A')
        embed.add_field(
            name='Initial Sell Price', value=f'{alert.initial_high:,} coins' if alert.initial_high else 'N/A'
        )
        embed.add_field(name='​', value='​')
        embed.add_field(name='Alert Frequency', value=format_timespan(alert.frequency) if alert.frequency else 'None')
        embed.add_field(name='Last Alert', value=format_unix_dt(alert.last_alert, "R") if alert.last_alert else 'Never')
        embed.add_field(name='​', value='​')
        embed.add_field(name='Current Alerts', value=str(alert.current_alerts) if alert.current_alerts else '0')
        embed.add_field(name='Maximum Alerts', value=str(alert.maximum_alerts) if alert.maximum_alerts else 'None')
        embed.add_field(name='​', value='​')

        embed.set_footer(text='Please report any issues to my owner!')

        await interaction.response.send_message(embed=embed)

    @alert_subgroup.command(name='delete', description='Deletes an existing item alert.')
    @app_commands.describe(item_id='The item to delete alerts for')
    @app_commands.rename(item_id='item')
    async def delete_alert(self, interaction: Interaction[DreamBot], item_id: int) -> None:
        """
        Deletes an existing market alert for a Runescape item.

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
            with suppress(KeyError):
                del self.alerts[interaction.user.id][item_id]

            await interaction.response.send_message('Successfully deleted alert.', ephemeral=True)

    """
    MARK: - Autocomplete Methods
    """

    @edit_alert.autocomplete('item_id')
    @view_alert.autocomplete('item_id')
    @delete_alert.autocomplete('item_id')
    async def existing_alert_item_autocomplete(
            self, interaction: Interaction[DreamBot], current: str
    ) -> List[Choice[int]]:
        """
        Autocompletes item names to item id's for alert commands from a subset of item's with existing alerts.

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
            return [Choice(name=self.item_data[x.item_id].name, value=x.item_id) for x in list(alerts.values())[:25]]

        return generate_autocomplete_choices(
            current,
            [(self.item_data[x.item_id].name, x.item_id) for x in alerts.values()],
            minimum_threshold=100
        )

    # noinspection PyUnusedLocal
    @runescape_item.autocomplete('item_id')
    @add_alert.autocomplete('item_id')
    async def item_autocomplete(self, interaction: Interaction[DreamBot], current: str) -> List[Choice[int]]:
        """
        Autocompletes item names to item id's for the alert.add and item commands.

        Parameters:
            interaction (Interaction): The invocation interaction.
            current (str): The user's current input.

        Returns:
            (List[Choice]): A list of relevant Choices for the current input.
        """

        if not current:
            return [Choice(name=item.name, value=item_id) for item_id, item in list(self.item_data.items())[:25]]

        return generate_autocomplete_choices(
            current,
            [(self.item_data[key].name, key) for key in self.item_data.keys()]
        )

    @add_alert.autocomplete('low_price')
    async def add_item_market_low_price_autocomplete(
            self, interaction: Interaction[DreamBot], current: str
    ) -> List[Choice[str]]:
        """
        Autocompletes item market prices for price parameters.

        Parameters:
            interaction (Interaction): The invocation interaction.
            current (str): The user's current input.

        Returns:
            (List[Choice]): A list of relevant Choices for the current input.
        """

        choices: List[Choice[str]] = []

        if interaction.namespace.item not in self.item_data:
            return choices

        item = self.item_data[interaction.namespace.item]

        if interaction.namespace.low_price == current and item.low is not None:
            choices.append(Choice(name=f'Current Market Low: {item.low:,} coins', value=str(item.low)))

        if current:
            choices.insert(0, Choice(name=f'New Value: {current}', value=current))

        return choices

    @add_alert.autocomplete('high_price')
    async def add_item_market_high_price_autocomplete(
            self, interaction: Interaction[DreamBot], current: str
    ) -> List[Choice[str]]:
        """
        Autocompletes item market prices for price parameters.

        Parameters:
            interaction (Interaction): The invocation interaction.
            current (str): The user's current input.

        Returns:
            (List[Choice]): A list of relevant Choices for the current input.
        """

        choices: List[Choice[str]] = []

        if interaction.namespace.item not in self.item_data:
            return choices

        item = self.item_data[interaction.namespace.item]

        if interaction.namespace.high_price == current and item.high is not None:
            choices.append(Choice(name=f'Current Market High: {item.high:,} coins', value=str(item.high)))

        if current:
            choices.insert(0, Choice(name=f'New Value: {current}', value=current))

        return choices

    @add_alert.autocomplete('alert_frequency')
    async def add_item_alert_frequency_autocomplete(
            self, interaction: Interaction[DreamBot], current: str
    ) -> List[Choice[str]]:
        """
        Autocompletes parameters for the edit command, which also allows for sentinel values.

        Parameters:
            interaction (Interaction): The invocation interaction.
            current (str): The user's current input.

        Returns:
            (List[Choice]): A list of relevant Choices for the current input.
        """

        choices = [
            Choice(name='Maximum Frequency: 5 minutes', value=f'{FIVE_MINUTES}s'),
            Choice(name='Minimum Frequency: 1 year', value=f'{ONE_YEAR}s')
        ]

        if current:
            choices.insert(0, Choice(name=f'New Value: {current}', value=current))

        return choices

    @add_alert.autocomplete('maximum_alerts')
    async def add_item_maximum_alerts_autocomplete(
            self, interaction: Interaction[DreamBot], current: str
    ) -> List[Choice[str]]:
        """
        Autocompletes parameters for the edit command, which also allows for sentinel values.

        Parameters:
            interaction (Interaction): The invocation interaction.
            current (str): The user's current input.

        Returns:
            (List[Choice]): A list of relevant Choices for the current input.
        """

        choices = [
            Choice(name=f'Minimum Alerts: {MIN_ALERTS:,} alert', value=str(MIN_ALERTS)),
            Choice(name=f'Maximum Alerts: {MAX_ALERTS:,} alerts', value=str(MAX_ALERTS))
        ]

        if current:
            choices.insert(0, Choice(name=f'New Value: {current}', value=current))

        return choices

    @edit_alert.autocomplete('low_price')
    async def edit_item_autocomplete(self, interaction: Interaction[DreamBot], current: str) -> List[Choice[str]]:
        """
        Autocompletes parameters for the edit command, which also allows for sentinel values.

        Parameters:
            interaction (Interaction): The invocation interaction.
            current (str): The user's current input.

        Returns:
            (List[Choice]): A list of relevant Choices for the current input.
        """

        choices: List[Choice[str]] = []

        item_id = interaction.namespace.item

        if item_id not in self.item_data or item_id not in self.alerts[interaction.user.id]:
            return choices

        item = self.item_data[interaction.namespace.item]
        alert = self.alerts[interaction.user.id][item_id]

        if item.low is not None:
            choices.append(Choice(name=f'Current Market Low: {item.low:,} coins', value=str(item.low)))

        if alert.target_low is not None:
            choices.append(Choice(name=f'Remove Existing Value: {alert.target_low:,} coins', value='-1'))

        if current:
            choices.insert(0, Choice(name=f'New Value: {current}', value=current))

        return choices

    @edit_alert.autocomplete('high_price')
    async def edit_item_high_price_autocomplete(
            self, interaction: Interaction[DreamBot], current: str
    ) -> List[Choice[str]]:
        """
        Autocompletes parameters for the edit command, which also allows for sentinel values.

        Parameters:
            interaction (Interaction): The invocation interaction.
            current (str): The user's current input.

        Returns:
            (List[Choice]): A list of relevant Choices for the current input.
        """

        choices: List[Choice[str]] = []

        item_id = interaction.namespace.item

        if item_id not in self.item_data or item_id not in self.alerts[interaction.user.id]:
            return choices

        item = self.item_data[interaction.namespace.item]
        alert = self.alerts[interaction.user.id][item_id]

        if item.high is not None:
            choices.append(Choice(name=f'Current Market High: {item.high:,} coins', value=str(item.high)))

        if alert.target_high is not None:
            choices.append(Choice(name=f'Remove Existing Value: {alert.target_high:,} coins', value='-1'))

        if current:
            choices.insert(0, Choice(name=f'New Value: {current}', value=current))

        return choices

    @edit_alert.autocomplete('alert_frequency')
    async def edit_item_alert_frequency_autocomplete(
            self, interaction: Interaction[DreamBot], current: str
    ) -> List[Choice[str]]:
        """
        Autocompletes parameters for the edit command, which also allows for sentinel values.

        Parameters:
            interaction (Interaction): The invocation interaction.
            current (str): The user's current input.

        Returns:
            (List[Choice]): A list of relevant Choices for the current input.
        """

        if interaction.namespace.item not in self.alerts[interaction.user.id]:
            return []

        choices = [
            Choice(name='Maximum Frequency: 5 minutes', value=str(FIVE_MINUTES)),
            Choice(name='Minimum Frequency: 1 year', value=str(ONE_YEAR))
        ]

        alert = self.alerts[interaction.user.id][interaction.namespace.item]

        if alert.frequency is not None:
            choices.append(Choice(name=f'Remove Existing Value: {format_timespan(alert.frequency)}', value='-1'))

        if current:
            choices.insert(0, Choice(name=f'New Value: {current}', value=current))

        return choices

    @edit_alert.autocomplete('maximum_alerts')
    async def edit_item_maximum_alerts_autocomplete(
            self, interaction: Interaction[DreamBot], current: str
    ) -> List[Choice[str]]:
        """
        Autocompletes parameters for the edit command, which also allows for sentinel values.

        Parameters:
            interaction (Interaction): The invocation interaction.
            current (str): The user's current input.

        Returns:
            (List[Choice]): A list of relevant Choices for the current input.
        """

        if interaction.namespace.item not in self.alerts[interaction.user.id]:
            return []

        choices = [
            Choice(name=f'Minimum Alerts: {MIN_ALERTS:,} alert', value=str(MIN_ALERTS)),
            Choice(name=f'Maximum Alerts: {MAX_ALERTS:,} alerts', value=str(MAX_ALERTS))
        ]

        alert = self.alerts[interaction.user.id][interaction.namespace.item]

        if alert.maximum_alerts is not None:
            choices.append(Choice(name=f'Remove Existing Value: {alert.maximum_alerts:,} alerts', value='-1'))

        if current:
            choices.insert(0, Choice(name=f'New Value: {current}', value=current))

        return choices

    """
    MARK: - Tasks
    """

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

        else:
            self.initial_mapping_data_event.set()

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

        except (JSONDecodeError, UnicodeError, TimeoutError) as e:
            bot_logger.warning(f'OSRS Mapping Query Error: {type(e)} - {e}')

        except Exception as e:
            bot_logger.error(f'OSRS Mapping Query Unhandled Exception: {type(e)} - {e}')
            await self.bot.report_exception(e)

        else:
            await self.check_alerts()

    @query_market_data.before_loop
    async def wait_for_item_data(self) -> None:
        """
        Waits to fetch market data until the initial item data has been fetched.

        Parameters:
            None.

        Returns:
            None.
        """

        await self.initial_mapping_data_event.wait()
        await self.bot.wait_until_ready()

    """
    MARK: - Alert Helpers
    """

    async def check_alerts(self) -> None:
        """
        Checks alerts against the latest market data.

        Notes:
            An item's low price (`low`) is the price an item will instantly sell for.
            An item's high price (`high`) is the price an item will instantly buy for.

            An alert's low price (`low_price`) is the price a user wants to buy items for.
                Therefore, trigger an alert if item.high (instant buy) <= alert.target_low.

            An alerts high price (`high_price`) is the price a user wants to sell items for.
                Therefore, trigger an alert if item.low (instant sell) >= alert.target_high.

        Parameters:
            None.

        Returns:
            None.
        """

        now = int(utcnow().timestamp())

        # noinspection PyShadowingNames
        def validate_alert(alert: RunescapeAlert) -> bool:
            """
            Filters out Alerts that don't meet send requirements.

            Parameters:
                alert (RunescapeAlert): The alert to validate.

            Returns:
                (bool): Whether the alert is valid can be used to check against market data.
            """

            if alert.item_id not in self.item_data:
                return False

            if alert.frequency is None:
                return False

            if alert.maximum_alerts is not None and alert.current_alerts >= alert.maximum_alerts:
                return False

            if alert.last_alert is not None and alert.last_alert + alert.frequency > now:
                return False

            return True

        valid_alerts = filter(
            validate_alert,
            chain.from_iterable(x.values() for x in self.alerts.values())
        )

        embed_fragment_type = dict[int, dict[Literal['low', 'high'], List[AlertEmbedFragment]]]
        # [user_id: ['low', 'high': [AlertEmbedFragment]]]
        embed_fragments: embed_fragment_type = defaultdict(lambda: defaultdict(list))

        for alert in valid_alerts:
            item_low = self.item_data[alert.item_id].low
            item_high = self.item_data[alert.item_id].high

            if alert.target_high is not None and item_low is not None and item_low >= alert.target_high:
                embed_fragments[alert.owner_id]['high'].append(
                    AlertEmbedFragment(
                        alert.owner_id,
                        alert.item_id,
                        self.item_data[alert.item_id].name,
                        item_low,
                        alert.target_high
                    )
                )

            if alert.target_low is not None and item_high is not None and item_high <= alert.target_low:
                embed_fragments[alert.owner_id]['low'].append(
                    AlertEmbedFragment(
                        alert.owner_id,
                        alert.item_id,
                        self.item_data[alert.item_id].name,
                        item_high,
                        alert.target_low
                    )
                )

        for user_id in embed_fragments:
            await self.send_alert(user_id, embed_fragments[user_id])

    async def send_alert(self, user_id: int, alerts: dict[Literal['low', 'high'], List[AlertEmbedFragment]]) -> None:
        """
        Sends filtered and validated alerts to users.

        Parameters:
            user_id (int): The id of the user.
            alerts (dict[Literal['low', 'high'], List[AlertEmbedFragment]]): A mapping containing alert fragments.

        Returns:
            None.
        """

        user = self.bot.get_user(user_id)
        # TODO: failure logic (unavailable checks)
        if user is None:
            return

        embed = discord.Embed(
            title="Old School Runescape Market Alerts",
            description="The following items had their market prices exceed your alert thresholds!",
            color=0x971212
        )
        embed.set_thumbnail(
            url="https://oldschool.runescape.wiki/images/thumb/Grand_Exchange_logo.png/150px-Grand_Exchange_logo.png"
        )

        if high := alerts['high']:
            embed.add_field(name="Price Gains", value='\n'.join(x.name for x in alerts['high']))
            embed.add_field(name="Alert Price", value='\n'.join(f'{x.target_price:,}' for x in alerts['high']))
            embed.add_field(
                name="Market Price",
                value='\n'.join(
                    f'{x.current_price:,} ({percentage_change(x.target_price, x.current_price)})' for x in high
                )
            )

        if low := alerts['low']:
            embed.add_field(name="Price Drops", value='\n'.join(x.name for x in alerts['low']))
            embed.add_field(name="Alert Price", value='\n'.join(f'{x.target_price:,}' for x in alerts['low']))
            embed.add_field(
                name="Market Price",
                value='\n'.join(
                    f'{x.current_price:,} ({percentage_change(x.target_price, x.current_price)})' for x in low
                )
            )

        embed.set_footer(text="Please report any issues to my owner!")

        try:
            await user.send(embed=embed)
        except discord.HTTPException:
            pass
        else:
            now = int(utcnow().timestamp())
            for alert in alerts['high'] + alerts['low']:
                await record_alert(self.bot.database, alert.owner_id, alert.item_id, now)
                self.alerts[alert.owner_id][alert.item_id].record_alert(now)

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


async def record_alert(database: str, user_id: int, item_id: int, last_alert_time: int) -> None:
    """
    Attempts to increment the usage count of an alert.

    Parameters:
        database (str): The name of the bot's database.
        user_id (str): The user_id of the alert.
        item_id (int): The item_id of the alert.
        last_alert_time (int): The time of the last alert.

    Returns:
        None.
    """

    try:
        await execute_query(
            database,
            'UPDATE RUNESCAPE_ALERTS SET CURRENT_ALERTS=CURRENT_ALERTS+1, LAST_ALERT=? WHERE OWNER_ID=? AND ITEM_ID=?',
            (last_alert_time, user_id, item_id)
        )
    except aiosqliteError:
        pass


def percentage_change(start: int, final: int) -> str:
    """
    Calculates the percentage the initial value has changed.

    Parameters:
        start (int): The initial value.
        final (int): The current value.

    Returns:
        (str): The percentage change, formatted to two decimal places.
    """

    change = (final - start) / start
    return '{0:,.2f}%'.format(change * 100)


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
