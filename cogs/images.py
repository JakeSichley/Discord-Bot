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

from typing import Union

import discord
from discord.ext import commands

from dreambot import DreamBot
from utils import image_utils
from utils.context import Context
from utils.defaults import MessageReply
from utils.logging_formatter import bot_logger


class Images(commands.Cog):
    """
    A Cogs class that invokes ImageUtils methods.

    Attributes:
        bot (DreamBot): The Discord bot class.
    """

    def __init__(self, bot: DreamBot) -> None:
        """
        The constructor for the MemeCoin class.

        Parameters:
            bot (DreamBot): The Discord bot.
        """

        self.bot = bot

    @commands.command(name='invert')
    async def invert(self, ctx: Context, source: Union[discord.Message, str] = MessageReply) -> None:
        """
        A method that invokes image inversion from ImageUtils.

        Parameters:
            ctx (Context): The invocation context.
            source ([Union[discord.Message, str]]): The source of the image to invert (can be a message reply).

        Output:
            Success: A discord.File object containing the inverted image.
            Failure: An error message.

        Returns:
            None.
        """

        async with ctx.channel.typing():
            try:
                buffer = await image_utils.extract_image_as_bytes(self.bot.session, source)
                inverted = await image_utils.invert_object(buffer)
            except image_utils.NoImage:
                await ctx.send('No image was provided.')
                return
            except image_utils.BufferSizeExceeded:
                self.bot.report_command_failure(ctx)
                await ctx.send('The supplied image is too large. Bots are limited to images of size < 8 Megabytes.')
                return
            except discord.HTTPException as e:
                self.bot.report_command_failure(ctx)
                bot_logger.error(f'File Download Failure. {e.status}. {e.text}')
                await ctx.send(f'Could not download image. Details: [Status {e.status} | {e.text}]')
                return

            try:
                await ctx.send(file=discord.File(inverted, filename="inverted.png"))
            except discord.HTTPException as e:
                self.bot.report_command_failure(ctx)
                bot_logger.error(f'File Send Failure. {e.status}. {e.text}')
                await ctx.send(f'Could not send image. Details: [Status {e.status} | {e.text}]')
            else:
                self.bot.reset_dynamic_cooldown(ctx)

    @commands.command(name='iasip', aliases=['sun', 'sunny', 'title'])
    async def iasip_title_card(self, ctx: Context, *, title: str) -> None:
        """
        A method that invokes "It's Always Sunny In Philadelphia" title card generation from ImageUtils.

        Parameters:
            ctx (Context): The invocation context.
            title (str): The text to display on the title card.

        Output:
            Success: A discord.File object containing the generated title card image.
            Failure: An error message.

        Returns:
            None.
        """

        async with ctx.channel.typing():
            if not title.startswith('"'):
                title = '"' + title

            if not title.endswith('"'):
                title += '"'

            buffer = await image_utils.title_card_generator(title)

            try:
                await ctx.send(file=discord.File(buffer, filename="iasip.png"))
            except discord.HTTPException as e:
                bot_logger.error(f'File Send Failure. {e.status}. {e.text}')
                await ctx.send(f'Could not send image. Details: [Status {e.status} | {e.text}]')
                return


async def setup(bot: DreamBot) -> None:
    """
    A setup function that allows the cog to be treated as an extension.

    Parameters:
        bot (DreamBot): The bot the cog should be added to.

    Returns:
        None.
    """

    await bot.add_cog(Images(bot))
    bot_logger.info('Completed Setup for Cog: Images')
