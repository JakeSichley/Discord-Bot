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

from typing import TYPE_CHECKING, Set

from discord import Message, AllowedMentions
from pydantic import ValidationError
from discord.ext import commands
from google.genai.errors import APIError as GeminiError

from utils.gemini import GeminiService
from utils.defaults import MessageReply
from utils.network.exceptions import EmptyResponseError
from utils.observability.loggers import bot_logger

if TYPE_CHECKING:
    from dreambot import DreamBot
    from utils.context import Context

EXPERIMENTAL_COOLDOWN = commands.CooldownMapping.from_cooldown(24, 60 * 60 * 24, commands.BucketType.default)


@commands.guild_only()
class Experimental(commands.Cog, command_attrs={'hidden': True}):
    """
    A Cogs class that contains experimental features/functionality, often locked to specific test cohort.

    Attributes:
        bot (DreamBot): The Discord bot.
        allowed_guilds (Set[int]): Guild ids included in the experimental cohort.
        allowed_users (Set[int]): User ids included in the experimental cohort.
    """

    def __init__(self, bot: 'DreamBot') -> None:
        """
        The constructor for the Experimental class.

        Parameters:
            bot (Bot): The Discord bot.

        Returns:
            None.
        """

        self.bot = bot
        self.allowed_guilds: Set[int] = {1138369898796560405, 153005652141146112}
        self.allowed_users: Set[int] = {
            91995622093123584,
            271863847630012416,
            160603016607563777,
            129077643722096640,
            163111415748624384,
            111635374069010432,
            298321570127151105,
            128693365427404800,
            99634976084987904,
            160134239310970881,
        }

        self.client = GeminiService()

    async def cog_check(self, ctx: 'Context') -> bool:  # type: ignore[override]
        """
        A method that registers a cog-wide check.
        Requires the invoking user to be in the experimental cohort(s).

        Note:
            This is implemented as a `cog_check` rather than respective discord.py decorators to allow for ease
            of manipulation and reloading (i.e.: this can `exec`'d rather than needing to modify the source file).

        Parameters:
            ctx (Context): The invocation context.

        Returns:
            (bool).
        """

        if ctx.guild is None:
            return False

        return ctx.guild.id in self.allowed_guilds or ctx.author.id in self.allowed_users

    async def cog_unload(self) -> None:
        """
        A special method that is called when the cog gets removed.

        Parameters:
            None.

        Returns:
            None.
        """

        await self.client.close()

        bot_logger.info('Completed Unload for Cog: Experimental')

    @commands.command(name='true', aliases=['true?'], cooldown=EXPERIMENTAL_COOLDOWN)
    async def true_command(self, ctx: 'Context', message_context: Message = MessageReply) -> None:
        """
        Top-level fact-check command.

        Parameters:
            ctx (Context): The invocation context.
            message_context (Message): The message the contains the claim to be checked.

        Returns:
            None.
        """

        await self._fact_check(ctx, message_context)

    @commands.group(name='fact')
    async def fact_group(self, ctx: 'Context') -> None:
        """
        Parent-level fact-check command. Requires a subcommand.

        Subcommands:
            'check' -> 'fact check'

        Parameters:
            ctx (Context): The invocation context.

        Returns:
            None.
        """

    @fact_group.command(name='check', cooldown=EXPERIMENTAL_COOLDOWN)  # type: ignore[arg-type]
    async def fact_check_command(self, ctx: 'Context', message_context: Message = MessageReply) -> None:
        """
        Leaf-level fact-check command.

        Matched Qualified Parents:
            'fact check'

        Parameters:
            ctx (Context): The invocation context.
            message_context (Message): The message the contains the claim to be checked.

        Returns:
            None.
        """

        await self._fact_check(ctx, message_context)

    @commands.group(name='is')
    async def is_group(self, ctx: 'Context') -> None:
        """
        Parent-level fact-check command. Requires a subcommand.

        Subcommands:
            'is' -> 'is true'
            'is' -> 'is true?'

            'is' -> 'is this true'
            'is' -> 'is this true?'

        Parameters:
            ctx (Context): The invocation context.

        Returns:
            None.
        """

    @is_group.command(name='true', aliases=['true?'], cooldown=EXPERIMENTAL_COOLDOWN)  # type: ignore[arg-type]
    async def is_true_command(self, ctx: 'Context', message_context: Message = MessageReply) -> None:
        """
        Leaf-level fact-check command.

        Matched Qualified Parents:
            'is true'
            'is true?'

        Parameters:
            ctx (Context): The invocation context.
            message_context (Message): The message the contains the claim to be checked.

        Returns:
            None.
        """

        await self._fact_check(ctx, message_context)

    @is_group.group(name='this')  # type: ignore[arg-type]
    async def is_this_group(self, ctx: 'Context') -> None:
        """
        Intermediate-level fact-check command. Requires a subcommand.

        Subcommands:
            'is this' -> 'is this true'
            'is this' -> 'is this true?'

        Parameters:
            ctx (Context): The invocation context.

        Returns:
            None.
        """

    @is_this_group.command(name='true', aliases=['true?'], cooldown=EXPERIMENTAL_COOLDOWN)  # type: ignore[arg-type]
    async def is_this_true_command(self, ctx: 'Context', message_context: Message = MessageReply) -> None:
        """
        Leaf-level fact-check command.

        Matched Qualified Parents:
            'is this true'
            'is this true?'

        Parameters:
            ctx (Context): The invocation context.
            message_context (Message): The message the contains the claim to be checked.

        Returns:
            None.
        """

        await self._fact_check(ctx, message_context)

    async def _fact_check(self, ctx: 'Context', message_context: Message) -> None:
        """
        Primary fact-check implementation. Attempts to fact-check a statement provided via `message_context`.
        Additional messages are provided as optional context.

        Parameters:
            ctx (Context): The invocation context.
            message_context (Message): The message the contains the claim to be checked.

        Returns:
            None.
        """

        if message_context.author.bot:
            await ctx.reply(f'I do not fact-check contents from other bots', allowed_mentions=AllowedMentions.none())
            return

        if message_context.content is None:
            await ctx.reply(f'I can only fact-check text content at this time', allowed_mentions=AllowedMentions.none())
            return

        async with ctx.channel.typing():
            history = [
                message
                async for message in ctx.channel.history(limit=5, before=message_context)
                if not message.author.bot
            ]

            try:
                response = await self.client.fact_check(
                    message_context.content, [message.content for message in history]
                )
            except (EmptyResponseError, ValidationError, GeminiError) as e:
                await ctx.reply(
                    'Something went wrong while I was trying to fact-check this statement, please try again later.',
                    allowed_mentions=AllowedMentions.none(),
                )
                bot_logger.warning(f'Failed to generate a fact checking response: Error: {e}')
                return

            if not response.is_actionable:
                await ctx.reply(
                    f'I cannot fact-check this statement (Reason: {response.formatted_refusal_reason})',
                    allowed_mentions=AllowedMentions.none(),
                )
                return
            await ctx.reply(response.formatted_verdict, allowed_mentions=AllowedMentions.none())


async def setup(bot: 'DreamBot') -> None:
    """
    A setup function that allows the cog to be treated as an extension.

    Parameters:
        bot (DreamBot): The bot the cog should be added to.

    Returns:
        None.
    """

    await bot.add_cog(Experimental(bot))
    bot_logger.info('Completed Setup for Cog: Experimental')
