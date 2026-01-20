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

from contextlib import suppress
from typing import Optional, TYPE_CHECKING
from urllib.parse import urlparse

from aiosqlite import Error as aiosqliteError
from discord import app_commands, Permissions, Embed, AllowedMentions, HTTPException
from discord.ext import commands

from utils.database.helpers import execute_query
from utils.enums.guild_feature import GuildFeature, has_guild_feature, set_guild_feature
from utils.observability.loggers import bot_logger

if TYPE_CHECKING:
    import discord
    from discord import Interaction
    from dreambot import DreamBot


class GuildFeatures(commands.Cog):
    """
    A Cogs class that manages features for a guild.

    Attributes:
        bot (DreamBot): The Discord bot class.
    """

    feature_subgroup = app_commands.Group(
        name='guild_features',
        description='Commands for managing guild features',
        default_permissions=Permissions(manage_guild=True),
        guild_only=True
    )

    def __init__(self, bot: 'DreamBot') -> None:
        """
        The constructor for the GuildFeatures class.

        Parameters:
            bot (DreamBot): The Discord bot.
        """

        self.bot = bot

    """
    MARK: - App Commands
    """

    @feature_subgroup.command(name='status', description='Checks feature statuses for the current guild')
    async def check_guild_features(self, interaction: 'Interaction[DreamBot]') -> None:
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

        embed = Embed(
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

    @feature_subgroup.command(name='modify', description='Modify feature statuses for the current guild')
    @app_commands.describe(
        direct_tag_invoke='Optional: Whether to send tags automatically without needing the tag command',
        alternative_twitter_embeds="Optional: Whether the bot should replace Twitter embeds with 'FixupX.com' "
                                   "embeds instead"
    )
    async def modify_guild_features(
            self,
            interaction: 'Interaction[DreamBot]',
            direct_tag_invoke: Optional[bool] = None,
            alternative_twitter_embeds: Optional[bool] = None
    ) -> None:
        """
        Modifies feature statuses for the current guild.

        Parameters:
            interaction (Interaction): The invocation interaction.
            direct_tag_invoke (Optional[bool]): Whether tags are able to be directly invoked in this guild.
            alternative_twitter_embeds (Optional[bool]): Whether to enable the alternative Twitter embedder.

        Returns:
            None.
        """

        assert interaction.guild_id is not None

        feature_mapping = {
            GuildFeature.TAG_DIRECT_INVOKE: direct_tag_invoke,
            GuildFeature.ALTERNATIVE_TWITTER_EMBEDS: alternative_twitter_embeds
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

    @commands.Cog.listener()
    async def on_message(self, message: 'discord.Message') -> None:
        """
        Replaces Twitter (X) embeds with better ones and eliminates tracking parameters.

        Parameters:
            message (discord.Message): The newly created message.

        Returns:
            None.
        """

        if (
            message.guild is None
            or message.author.bot
            or not self.bot.cache.guild_feature_enabled(message.guild.id, GuildFeature.ALTERNATIVE_TWITTER_EMBEDS)
        ):
            return

        # naive search for Twitter url - getting this perfect is not mission-critical nor worth expensive computations
        try:
            url = next(token for token in message.content.split() if 'x.com' in token)
        except StopIteration:
            return

        if (parsed_url := urlparse(url)) and parsed_url.netloc != 'x.com':
            return

        try:
            await message.edit(suppress=True)
            await message.reply(
                content=parsed_url._replace(netloc='fixupx.com', query='', fragment='').geturl(),
                allowed_mentions=AllowedMentions.none(),
                mention_author=False,
                silent=True
            )
        # this is a low-priority operation, so at most we'll try to restore the original embed on any failure
        except HTTPException:
            with suppress(HTTPException):
                await message.edit(suppress=False)


async def setup(bot: 'DreamBot') -> None:
    """
    A setup function that allows the cog to be treated as an extension.

    Parameters:
        bot (DreamBot): The bot the cog should be added to.

    Returns:
        None.
    """

    await bot.add_cog(GuildFeatures(bot))
    bot_logger.info('Completed Setup for Cog: GuildFeatures')
