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

import datetime
from re import findall
from typing import Optional, Union, List, TYPE_CHECKING

import pytz
from discord import Embed, utils, Member, Message
from discord.ext import commands
from discord.utils import format_dt

from utils.checks import dynamic_cooldown
from utils.defaults import MessageReply
from utils.emoji_manager import (
    EmojiManager, EmojiComponent, NoViableEmoji, NoRemainingEmojiSlots, NoEmojisFound, FailureStage
)
from utils.observability.loggers import bot_logger
from utils.utils import readable_flags

if TYPE_CHECKING:
    from dreambot import DreamBot
    from utils.context import Context


class Utility(commands.Cog):
    """
    A Cogs class that contains utility commands for the bot.

    Attributes:
        bot (DreamBot): The Discord bot class.
    """

    def __init__(self, bot: 'DreamBot') -> None:
        """
        The constructor for the UtilityFunctions class.

        Parameters:
            bot (DreamBot): The Discord bot.
        """

        self.bot = bot

    @commands.command(name='time', help='Responds with the current time. Can be supplied with a timezone.\nFor a full '
                                        'list of supported timezones, see '
                                        'https://en.wikipedia.org/wiki/List_of_tz_database_time_zones')
    async def current_time(self, ctx: 'Context', timezone: str = 'UTC') -> None:
        """
        A method to output the current time in a specified timezone.

        Parameters:
            ctx (Context): The invocation context.
            timezone (str): A supported tz timezone. Default: 'UTC'.

        Output:
            The time in the specified timezone.

        Returns:
            None.
        """

        if timezone not in pytz.all_timezones:
            timezone = 'UTC'
        today = datetime.datetime.now(pytz.timezone(timezone))
        printable_format = today.strftime("%I:%M %p on %A, %B %d, %Y (%Z)")
        await ctx.send(f'{ctx.author.mention}, the current time is {printable_format}')

    @commands.command(name='devserver', help='Responds with an invite link to the development server. Useful for '
                                             'getting assistance with a bug, or requesting a new feature!')
    async def dev_server(self, ctx: 'Context') -> None:
        """
        A method to output a link to the DreamBot development server.

        Parameters:
            ctx (Context): The invocation context.

        Output:
            A link to the development server.

        Returns:
            None.
        """

        await ctx.send('_Need help with bugs or want to request a feature? Join the Discord!_'
                       '\nhttps://discord.gg/fgHEWdt')

    @commands.command(name='uptime', help='Returns current bot uptime.')
    async def uptime(self, ctx: 'Context') -> None:
        """
        A method that outputs the uptime of the bot.

        Parameters:
            ctx (Context): The invocation context.

        Output:
            The date and time the bot was started, as well as the duration the bot has been online.

        Returns:
            None.
        """

        await ctx.send(format_dt(self.bot.uptime, 'R'))

    @commands.guild_only()
    @commands.command(name='userinfo', aliases=['ui'],
                      help='Generates an embed detailing information about the specified user')
    async def user_info(self, ctx: 'Context', user: Member = commands.Author) -> None:
        """
        A method that outputs user information.

        Parameters:
            ctx (Context): The invocation context.
            user (Optional[discord.Member]): The member to generate information about. Defaults to command invoker.

        Output:
            Information about the specified user, including creation and join date.

        Returns:
            None.
        """

        assert ctx.guild is not None

        alias = user.nick or user.global_name

        embed = Embed(title=f'{str(user)}\'s User Information', color=0x1dcaff)
        if alias is not None:
            embed.description = f'Known as **{alias}** round\' these parts'
        if user.avatar is not None:
            embed.set_thumbnail(url=user.avatar.url)
        embed.add_field(name='Account Created', value=format_dt(user.created_at, 'R'))
        embed.add_field(name='Joined Server', value=format_dt(user.joined_at, 'R')) if user.joined_at else 'Unknown'
        members = sorted(ctx.guild.members, key=lambda x: x.joined_at or utils.utcnow())
        embed.add_field(name='Join Position', value=str(members.index(user)))
        embed.add_field(name='User ID', value=str(user.id), inline=False)
        embed.add_field(name='User Flags', value=readable_flags(user.public_flags), inline=False)
        roles = ', '.join(str(x) for x in (user.roles[::-1])[:-1])
        embed.add_field(name='Roles', value=roles if roles else 'None', inline=False)
        embed.set_footer(text="Please report any issues to my owner!")

        await ctx.send(embed=embed)

    @commands.command(name='unicodeemoji', aliases=['ue', 'eu'])
    async def unicode_emoji(self, ctx: 'Context', emoji: str) -> None:
        """
        A method to convert emojis to their respective unicode string.

        Parameters:
            ctx (Context): The invocation context.
            emoji (str): The emoji to encode.

        Output:
            The unicode string representing the emoji.

        Returns:
            None.
        """

        await ctx.send(f"`{emoji.encode('unicode-escape').decode('ASCII')}`")

    @commands.has_guild_permissions(manage_emojis=True)
    @commands.bot_has_guild_permissions(manage_emojis=True)
    @dynamic_cooldown()
    @commands.command(name='raw_yoink', aliases=['rawyoink'], help='Yoinks an emoji based on its id.')
    async def raw_yoink_emoji(
            self, ctx: 'Context', source: int, name: Optional[str] = None, animated: bool = False
    ) -> None:
        """
        A method to "yoink" an emoji. Retrieves the emoji as an asset and uploads it to the current guild.

        Parameters:
            ctx (Context): The invocation context.
            source (int): The ID of the emoji.
            name (Optional[str]): The name of the emoji.
            animated (Optional[bool]): Whether the emoji is animated.

        Returns:
            None.
        """

        emoji = EmojiComponent(
            animated=animated,
            name=name if name else str(source),
            id=source
        )

        await create_emojis(self.bot, ctx, emoji)

    @commands.has_guild_permissions(manage_emojis=True)
    @commands.bot_has_guild_permissions(manage_emojis=True)
    @dynamic_cooldown()
    @commands.command(name='yoink', help='Yoinks emojis from the specified message.')
    async def yoink_emoji(self, ctx: 'Context', source: Message = MessageReply) -> None:
        """
        A method to "yoink" an emoji. Retrieves the emoji as an asset and uploads it to the current guild.

        Parameters:
            ctx (Context): The invocation context.
            source (discord.Message): The message to extract emojis from. Can be (and defaults to) a MessageReply.

        Returns:
            None.
        """

        default = EmojiComponent()  # create a default to reference absent regex values from
        raw_emojis = findall(r'<(?P<animated>a?):(?P<name>[a-zA-Z0-9_]{2,32}):(?P<id>[0-9]{18,22})>', source.content)

        emojis = [
            EmojiComponent(
                animated=bool(x[0] or default.animated),
                name=x[1] or default.name,
                id=int(x[2]) or default.id
            ) for x in raw_emojis
        ]

        await create_emojis(self.bot, ctx, emojis)


async def create_emojis(bot: 'DreamBot', ctx: 'Context', emojis: Union[EmojiComponent, List[EmojiComponent]]) -> None:
    """
    Instantiates an EmojiManager instance, executes the driver `yoink` method, and handles resulting cases.

    Parameters:
        bot (DreamBot): The bot.
        ctx (Context): The invocation context.
        emojis (Union[EmojiComponent, List[EmojiComponent]]): The EmojiComponent(s) to yoink.

    Returns:
        None.
    """

    assert ctx.guild is not None

    emoji_manager = EmojiManager(ctx.guild, emojis)

    try:
        await emoji_manager.yoink(ctx, bot.network_client)
    except NoRemainingEmojiSlots:
        await ctx.send('You have no remaining emoji slots - cannot yoink any more emojis!')
        return
    except NoEmojisFound:
        await ctx.send('I could not find any emojis in the specified message!')
        return
    except NoViableEmoji as e:
        # this is currently the only exception that may be raised with a networking stage
        if e.stage == FailureStage.NETWORKING:
            bot.report_command_failure(ctx)
    else:
        bot.reset_dynamic_cooldown(ctx)

    await ctx.send(emoji_manager.status_message())


async def setup(bot: 'DreamBot') -> None:
    """
    A setup function that allows the cog to be treated as an extension.

    Parameters:
        bot (DreamBot): The bot the cog should be added to.

    Returns:
        None.
    """

    await bot.add_cog(Utility(bot))
    bot_logger.info('Completed Setup for Cog: UtilityFunctions')
