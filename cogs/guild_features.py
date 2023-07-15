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
from utils.database import table_dataclasses


class GuildFeatures(commands.Cog):
    """
    A Cogs class that manages features for a guild.

    Attributes:
        bot (DreamBot): The Discord bot class.
    """

    def __init__(self, bot: DreamBot) -> None:
        """
        The constructor for the GuildFeatures class.

        Parameters:
            bot (DreamBot): The Discord bot.
        """

        self.bot = bot
        self.features: dict[int, table_dataclasses.GuildFeatures] = dict()

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
            table_dataclasses.GuildFeatures,
            'SELECT * FROM GUILD_FEATURES'
        )

        for feature in features:
            self.features[feature.guild_id] = feature


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
