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

from typing import Optional

import discord
from aiosqlite import Error as aiosqliteError
from discord import app_commands, Interaction
from discord.ext import commands

from dreambot import DreamBot
from utils.database.helpers import execute_query
from utils.enums.guild_feature import GuildFeature, has_guild_feature, set_guild_feature
from utils.logging_formatter import bot_logger


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

        features = self.bot.cache.guild_features.get(interaction.guild_id, 0)

        embed = discord.Embed(
            title='Guild Features',
            description=f'Feature statuses for {interaction.guild.name}',
            color=0x00BD96,
        )

        for feature in GuildFeature:
            embed.add_field(
                name=f'{feature.name}', value='Enabled' if has_guild_feature(features, feature) else 'Disabled'
            )

        embed.set_footer(text='Please report any issues to my owner!')

        await interaction.response.send_message(embed=embed)

    @feature_subgroup.command(  # type: ignore[arg-type]
        name='modify', description='Modify feature statuses for the current guild'
    )
    @app_commands.describe(
        direct_tag_invoke='Optional: Whether to send tags automatically without needing the tag command',
    )
    async def modify_guild_features(
            self,
            interaction: Interaction,
            direct_tag_invoke: Optional[bool] = None,
    ) -> None:
        """
        Modifies feature statuses for the current guild.

        Parameters:
            interaction (Interaction): The invocation interaction.
            direct_tag_invoke (Optional[bool]): Whether tags are able to be directly invoked in this guild.

        Returns:
            None.
        """

        assert interaction.guild_id is not None

        feature_mapping = {
            GuildFeature.TAG_DIRECT_INVOKE: direct_tag_invoke
        }

        if all(x is None for x in feature_mapping.values()):
            await interaction.response.send_message('No guild features were modified.', ephemeral=True)
            return

        features = self.bot.cache.guild_features.get(interaction.guild_id, 0)

        for feature, value in feature_mapping.items():
            features = set_guild_feature(features, feature, value)

        try:
            await execute_query(
                self.bot.database,
                'INSERT INTO GUILD_FEATURES (GUILD_ID, FEATURES) VALUES (?, ?) '
                'ON CONFLICT(GUILD_ID) DO UPDATE SET FEATURES=EXCLUDED.FEATURES',
                (interaction.guild_id, features)
            )
        except aiosqliteError:
            await interaction.response.send_message('Failed to modify guild features as requested.', ephemeral=True)
        else:
            await interaction.response.send_message('Successfully modified guild features.', ephemeral=True)
            self.bot.cache.guild_features[interaction.guild_id] = features


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
