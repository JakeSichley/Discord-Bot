"""
MIT License

Copyright (c) 2019-2023 Jake Sichley

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

import discord
from discord.ext import commands

from dreambot import DreamBot
from utils.database.helpers import typed_retrieve_query
from utils.logging_formatter import bot_logger
from utils.database import table_dataclasses as TableDC
from discord import app_commands, Interaction
from discord.app_commands import Choice, Transform, Range
from collections import defaultdict
from utils.guild_feature import GuildFeature


class GuildFeatures(commands.Cog):
    """
    A Cogs class that manages features for a guild.

    Attributes:
        bot (DreamBot): The Discord bot class.
    """

    feature_subgroup = app_commands.Group(
        name='guild_features',
        description='Commands for managing guild features',
        default_permissions=discord.Permissions(manage_guild=True),
        guild_only=True
    )

    def __init__(self, bot: DreamBot) -> None:
        """
        The constructor for the GuildFeatures class.

        Parameters:
            bot (DreamBot): The Discord bot.
        """

        self.bot = bot
        self.features: dict[int, TableDC.GuildFeatures] = dict()

    async def cog_load(self) -> None:
        """
        A special method that acts as a cog local post-invoke hook.

        Parameters:
            None.

        Returns:
            None.
        """

        features = await typed_retrieve_query(
            self.bot.database,
            TableDC.GuildFeatures,
            'SELECT * FROM GUILD_FEATURES'
        )

        for feature in features:
            self.features[feature.guild_id] = feature

    """
    MARK: - App Commands
    """

    @feature_subgroup.command(  # type: ignore[arg-type]
        name='status', description='Checks feature statuses for the current guild'
    )
    async def check_guild_features(self, interaction: Interaction) -> None:
        """
        Retrieves feature statuses for the current guild.

        Parameters:
            interaction (Interaction): The invocation interaction.

        Returns:
            None.
        """

        assert interaction.guild_id is not None
        assert interaction.guild is not None

        try:
            features = self.features[interaction.guild_id]
        except KeyError:
            features = TableDC.GuildFeatures(interaction.guild_id, 0)

        embed = discord.Embed(
            title='Guild Features',
            description=f'Feature statuses for {interaction.guild.name}',
            color=0x00BD96,
        )

        for feature in GuildFeature:
            embed.add_field(name=f'{feature.name}', value='Enabled' if features.has_feature(feature) else 'Disabled')

        embed.set_footer(text='Please report any issues to my owner!')

        await interaction.response.send_message(embed=embed)

    """"
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
            maximum_alerts: Optional[Range[int, MIN_ALERTS, MAX_ALERTS]] = None
    ) -> None:
        ""
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
        ""

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
        """


async def setup(bot: DreamBot) -> None:
    """
    A setup function that allows the cog to be treated as an extension.

    Parameters:
        bot (DreamBot): The bot the cog should be added to.

    Returns:
        None.
    """

    await bot.add_cog(GuildFeatures(bot))
    bot_logger.info('Completed Setup for Cog: GuildFeatures')
