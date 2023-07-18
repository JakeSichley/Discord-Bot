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
from utils.context import Context
from utils.logging_formatter import bot_logger


class Silverwood(commands.Cog):
    """
    A Cogs class that contains Silverwood commands for the bot.

    # TODO: These commands can be replaced after adding embed support for tags

    Attributes:
        bot (DreamBot): The Discord bot class.
    """

    def __init__(self, bot: DreamBot) -> None:
        """
        The constructor for the Silverwood class.

        Parameters:
            bot (DreamBot): The Discord bot.
        """

        self.bot = bot

    async def cog_check(self, ctx: Context) -> bool:  # type: ignore[override]
        """
        Custom Cog Check.

        Parameters:
            ctx (Context): The invocation context.

        Returns:
            (bool).
        """

        return ctx.guild is not None and ctx.guild.id == 1127457916992110735

    @commands.command(name='cc', hidden=True)
    async def cc_command(self, ctx: Context) -> None:
        """
        Custom Command.

        Parameters:
            ctx (Context): The invocation context.

        Returns:
            None.
        """

        content = '@here\nFills in Cross-Country please! ♡'
        embed = discord.Embed()
        embed.set_image(url='https://media.giphy.com/media/sNH6OwnLEcxRnOlbLA/giphy.gif')
        await ctx.send(content=content, embed=embed)

    @commands.command(name='wins', hidden=True)
    async def wins_command(self, ctx: Context) -> None:
        """
        Custom Command.

        Parameters:
            ctx (Context): The invocation context.

        Returns:
            None.
        """

        content = 'https://media.giphy.com/media/MH35qIXXwoewkXVHg0/giphy.gif'
        await ctx.send(content=content)

    @commands.command(name='wp', hidden=True)
    async def wp_command(self, ctx: Context) -> None:
        """
        Custom Command.

        Parameters:
            ctx (Context): The invocation context.

        Returns:
            None.
        """

        content = '@here\nFills in Western Pleasure please! ♡'
        embed = discord.Embed()
        embed.set_image(url='https://media.giphy.com/media/KKreoxYTGq3aRCbRLh/giphy.gif')
        await ctx.send(content=content, embed=embed)


async def setup(bot: DreamBot) -> None:
    """
    A setup function that allows the cog to be treated as an extension.

    Parameters:
        bot (DreamBot): The bot the cog should be added to.

    Returns:
        None.
    """

    await bot.add_cog(Silverwood(bot))
    bot_logger.info('Completed Setup for Cog: Silverwood')
