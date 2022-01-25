"""
MIT License

Copyright (c) 2019-2022 Jake Sichley

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

from discord.ext import commands
from utils.utils import localize_time, readable_flags
from utils.defaults import MessageReply
from utils.network_utils import network_request, NetworkReturnType
from utils.context import Context
from typing import Optional
from re import findall
from dreambot import DreamBot
from aiohttp import ClientResponseError
from discord.ext.commands.default import Author
import datetime
import pytz
import discord
import logging


class Utility(commands.Cog):
    """
    A Cogs class that contains utility commands for the bot.

    Attributes:
        bot (DreamBot): The Discord bot class.
    """

    def __init__(self, bot: DreamBot) -> None:
        """
        The constructor for the UtilityFunctions class.

        Parameters:
           bot (DreamBot): The Discord bot.
        """

        self.bot = bot

    @commands.command(name='time', help='Responds with the current time. Can be supplied with a timezone.\nFor a full '
                                        'list of supported timezones, see '
                                        'https://en.wikipedia.org/wiki/List_of_tz_database_time_zones')
    async def current_time(self, ctx: Context, timezone: str = 'UTC') -> None:
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
    async def dev_server(self, ctx: Context) -> None:
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
    async def uptime(self, ctx: Context) -> None:
        """
        A method that outputs the uptime of the bot.

        Parameters:
            ctx (Context): The invocation context.

        Output:
            The date and time the bot was started, as well as the duration the bot has been online.

        Returns:
            None.
        """

        time = datetime.datetime.now() - self.bot.uptime
        days = time.days % 7
        weeks = int(time.days / 7)
        hours, remainder = divmod(time.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        await ctx.send(f'Bot Epoch: {self.bot.uptime.strftime("%I:%M %p on %A, %B %d, %Y")}'
                       f'\nBot Uptime: {weeks} Weeks, {days} Days, {hours} Hours, {minutes} Minutes, {seconds} Seconds')

    @commands.guild_only()
    @commands.command(name='userinfo', aliases=['ui'],
                      help='Generates an embed detailing information about the specified user')
    async def user_info(self, ctx: Context, user: discord.Member = Author) -> None:
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

        embed = discord.Embed(title=f'{str(user)}\'s User Information', color=0x1dcaff)
        if user.nick:
            embed.description = f'Known as **{user.nick}** round\' these parts'
        embed.set_thumbnail(url=user.avatar_url)
        embed.add_field(name='Account Created', value=localize_time(user.created_at))
        embed.add_field(name='Joined Server', value=localize_time(user.joined_at))
        members = sorted(ctx.guild.members, key=lambda x: x.joined_at)
        embed.add_field(name='Join Position', value=str(members.index(user)))
        embed.add_field(name='User ID', value=str(user.id), inline=False)
        embed.add_field(name='User Flags', value=readable_flags(user.public_flags), inline=False)
        roles = ', '.join(str(x) for x in (user.roles[::-1])[:-1])
        embed.add_field(name='Roles', value=roles if roles else 'None', inline=False)
        embed.set_footer(text="Please report any issues to my owner!")

        await ctx.send(embed=embed)

    @commands.command(name='unicodeemoji', aliases=['ue', 'eu'])
    async def unicode_emoji(self, ctx: Context, emoji: str):
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
    @commands.command(name='raw_yoink', aliases=['rawyoink'], help='Yoinks an emoji based on its id.')
    async def raw_yoink_emoji(self, ctx: Context, source: int, name: Optional[str] = None,
                              animated: Optional[bool] = False) -> None:
        """
        A method to "yoink" an emoji. Retrieves the emoji as an asset and uploads it to the current guild.

        Parameters:
            ctx (Context): The invocation context.
            source (int): The ID of the emoji.
            name (Optional[str]): The name of the emoji.
            animated (Optional[bool]): Whether the emoji is animated.

        Output:
            Command state information.

        Returns:
            None.
        """

        extension = 'gif' if animated else 'png'
        emoji_asset = await network_request(
            f'https://cdn.discordapp.com/emojis/{source}.{extension}?size=96', return_type=NetworkReturnType.BYTES
        )

        name = name if name else str(source)

        try:
            created_emoji = await ctx.guild.create_custom_emoji(
                name=name, image=emoji_asset, reason=f'Yoink\'d by {ctx.author}'
            )
            try:
                await ctx.react(created_emoji, raise_exceptions=True)
            except discord.HTTPException as e:
                logging.warning(f'Raw Yoink Add Reaction Error. {e.status}. {e.text}')
                await ctx.tick()
        except discord.HTTPException as e:
            logging.error(f'Raw Yoink Creation Error. {e.status}. {e.text}')
            await ctx.send(f'**{name}** failed with `{e.text}`')

    @commands.has_guild_permissions(manage_emojis=True)
    @commands.bot_has_guild_permissions(manage_emojis=True)
    @commands.command(name='yoink', help='Yoinks emojis from the specified message.')
    async def yoink_emoji(self, ctx: Context, source: discord.Message = MessageReply) -> None:
        """
        A method to "yoink" an emoji. Retrieves the emoji as an asset and uploads it to the current guild.

        Parameters:
            ctx (Context): The invocation context.
            source (Optional[discord.Message]): The message to extract emojis from (can be a message reply).

        Output:
            Command state information.

        Returns:
            None.
        """

        emojis = findall(r'<(?P<animated>a?):(?P<name>[a-zA-Z0-9_]{2,32}):(?P<id>[0-9]{18,22})>', source.content)

        if not emojis:
            await ctx.send('Failed to extract any emojis from the specified message.')
            return

        guild_emoji_names = [x.name for x in ctx.guild.emojis]
        guild_emoji_ids = [x.id for x in ctx.guild.emojis]

        unique_emoji, non_unique_emoji = [], []

        for emoji in emojis:
            if int(emoji[2]) in guild_emoji_ids:
                non_unique_emoji.append(f'_{emoji[1]}_ failed with `AlreadyAdded`')
            elif emoji[1] in guild_emoji_names:
                non_unique_emoji.append(f'_{emoji[1]}_ failed with `DuplicateName`')
            else:
                unique_emoji.append(emoji)

        if not unique_emoji:
            await ctx.send(f'No unique emojis found. The potential emoji are either from this server or have the '
                           f'same name as an existing emoji.\n\n**Failure Reasons:**\n{", ".join(non_unique_emoji)}')
            return

        if ctx.guild.emoji_limit < len(ctx.guild.emojis) + len(unique_emoji):
            await ctx.send(f'You do not have enough emoji slots to upload all of these emojis. '
                           f'You have {ctx.guild.emoji_limit - len(ctx.guild.emojis)} remaining slots.')
            return

        success, failed = [], []

        for emoji in unique_emoji:
            extension = 'gif' if emoji[0] else 'png'

            try:
                emoji_asset = await network_request(
                    f'https://cdn.discordapp.com/emojis/{emoji[2]}.{extension}?size=96',
                    return_type=NetworkReturnType.BYTES
                )
            except ClientResponseError as e:
                failed.append(f'**{emoji[1]}** failed with `{e.message}`')
                continue

            try:
                created_emoji = await ctx.guild.create_custom_emoji(
                    name=emoji[1], image=emoji_asset, reason=f'Yoink\'d by {ctx.author}'
                )
                try:
                    await ctx.react(created_emoji, raise_exceptions=True)
                except discord.HTTPException as e:
                    logging.warning(f'Yoink Add Reaction Error. {e.status}. {e.text}')
                    success.append(emoji[1])
            except discord.HTTPException as e:
                logging.error(f'Yoink Creation Error. {e.status}. {e.text}')
                failed.append(f'**{emoji[1]}** failed with `{e.text}`')

        response = ''

        if success:
            response += f'Successfully yoink\'d the following emoji:\n```{", ".join(success)}```\n'

        if failed:
            response += f'Failed to yoink the following emoji:\n```{", ".join(failed)}```'

        if response:
            await ctx.send(response)


def setup(bot: DreamBot) -> None:
    """
    A setup function that allows the cog to be treated as an extension.

    Parameters:
        bot (DreamBot): The bot the cog should be added to.

    Returns:
        None.
    """

    bot.add_cog(Utility(bot))
    logging.info('Completed Setup for Cog: UtilityFunctions')
