"""
MIT License

Copyright (c) 2019-2024 Jake Sichley

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

from discord import app_commands, Interaction
from discord.ext import commands

from dreambot import DreamBot
from utils.logging_formatter import bot_logger

from utils.database.helpers import execute_query
import aiosqlite
from discord.utils import utcnow
from aiosqlite import Error as aiosqliteError, IntegrityError


class Groups(commands.Cog):
    """
    A Cogs class that contains Groups commands for the bot.

    Attributes:
        bot (DreamBot): The Discord bot class.
    """

    group_subgroup = app_commands.Group(name='group', description='Commands for managing groups')

    def __init__(self, bot: DreamBot) -> None:
        """
        The constructor for the Groups class.

        Parameters:
            bot (DreamBot): The Discord bot.
        """

        self.bot = bot

    @group_subgroup.command(  # type: ignore[arg-type]
        name='create', description='Creates a new group for this guild'
    )
    @app_commands.describe(group_name='The name of the group')
    async def create_group(
            self, interaction: Interaction,
            group_name: app_commands.Range[str, 1, 100],
    ) -> None:
        """
        Creates a new group for the guild. Name must be unique.

        Parameters:
            interaction (Interaction): The invocation interaction.
            group_name (str): The name of the group to create.

        Returns:
            None.
        """

        try:
            await execute_query(
                self.bot.database,
                'INSERT INTO GROUPS VALUES (?, ?, ?, ?)',
                (interaction.guild_id, interaction.user.id, int(utcnow().timestamp()), group_name),
                errors_to_suppress=aiosqlite.IntegrityError
            )
        except aiosqliteError as e:
            if isinstance(e, IntegrityError):
                await interaction.response.send_message('A group with this name already exists.', ephemeral=True)
            else:
                await interaction.response.send_message('Failed to create a new group.', ephemeral=True)
        else:
            await interaction.response.send_message('Successfully created group.', ephemeral=True)


async def setup(bot: DreamBot) -> None:
    """
    A setup function that allows the cog to be treated as an extension.

    Parameters:
        bot (DreamBot): The bot the cog should be added to.

    Returns:
        None.
    """

    await bot.add_cog(Groups(bot))
    bot_logger.info('Completed Setup for Cog: Groups')
