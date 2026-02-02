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

from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from utils.checks import guild_only
from utils.observability.loggers import bot_logger

if TYPE_CHECKING:
    from dreambot import DreamBot
    from utils.context import Context


class Howrse(commands.Cog):
    """
    A Cogs class that contains Howrse commands for the bot.

    # TODO: These commands can be replaced after adding embed support for tags

    Attributes:
        bot (DreamBot): The Discord bot class.
    """

    def __init__(self, bot: 'DreamBot') -> None:
        """
        The constructor for the Howrse class.

        Parameters:
            bot (DreamBot): The Discord bot.
        """

        self.bot = bot

    @guild_only(1127457916992110735)
    @commands.command(name='cc', hidden=True)
    async def silverwood_cc_command(self, ctx: Context) -> None:
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

    @guild_only(1127457916992110735)
    @commands.command(name='wins', hidden=True)
    async def silverwood_wins_command(self, ctx: Context) -> None:
        """
        Custom Command.

        Parameters:
            ctx (Context): The invocation context.

        Returns:
            None.
        """

        content = 'https://media.giphy.com/media/MH35qIXXwoewkXVHg0/giphy.gif'
        await ctx.send(content=content)

    @guild_only(1127457916992110735)
    @commands.command(name='wp', hidden=True)
    async def silverwood_wp_command(self, ctx: Context) -> None:
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

    @guild_only(1165414326417502218)
    @commands.command(name='xc', hidden=True)
    async def horsemen_xc_command(self, ctx: Context) -> None:
        """
        Custom Command.

        Parameters:
            ctx (Context): The invocation context.

        Returns:
            None.
        """

        content = '@here Fills in Cross-Country please! ♡'
        embed = discord.Embed()
        embed.set_image(url='https://media.giphy.com/media/sNH6OwnLEcxRnOlbLA/giphy.gif')
        await ctx.send(content=content, embed=embed)

    @guild_only(1165414326417502218)
    @commands.command(name='c', hidden=True)
    async def horsemen_c_command(self, ctx: Context) -> None:
        """
        Custom Command.

        Parameters:
            ctx (Context): The invocation context.

        Returns:
            None.
        """

        content = '@here Fills in Cutting please! ♡'
        embed = discord.Embed()
        embed.set_image(url='https://media.giphy.com/media/KKreoxYTGq3aRCbRLh/giphy.gif')
        await ctx.send(content=content, embed=embed)

    @guild_only(1165414326417502218)
    @commands.command(name='w', hidden=True)
    async def horsemen_w_command(self, ctx: Context) -> None:
        """
        Custom Command.

        Parameters:
            ctx (Context): The invocation context.

        Returns:
            None.
        """

        content = 'Thank you for wins! ♡'
        embed = discord.Embed()
        embed.set_image(url='https://media.tenor.com/Np6Be0U7BocAAAAC/groove-i-win.gif')
        await ctx.send(content=content, embed=embed)


async def setup(bot: 'DreamBot') -> None:
    """
    A setup function that allows the cog to be treated as an extension.

    Parameters:
        bot (DreamBot): The bot the cog should be added to.

    Returns:
        None.
    """

    await bot.add_cog(Howrse(bot))
    bot_logger.info('Completed Setup for Cog: Howrse')
