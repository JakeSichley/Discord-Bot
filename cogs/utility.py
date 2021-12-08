from discord.ext import commands
from discord import Member, Embed, PublicUserFlags
from utils.utils import localize_time
from utils.converters import MessageOrMessageReplyConverter
from utils.network_utils import network_request, NetworkReturnType
from typing import Optional
from re import findall
from inspect import Parameter
from dreambot import DreamBot
import datetime
import pytz
import aiosqlite
import discord


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
                      'list of supported timezones, see https://en.wikipedia.org/wiki/List_of_tz_database_time_zones')
    async def current_time(self, ctx: commands.Context, timezone: str = 'UTC') -> None:
        """
        A method to output the current time in a specified timezone.

        Parameters:
            ctx (commands.Context): The invocation context.
            timezone (str): A support pytz timezone. Default: 'UTC'.

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
    async def dev_server(self, ctx: commands.Context) -> None:
        """
        A method to output a link to the DreamBot development server.

        Parameters:
            ctx (commands.Context): The invocation context.

        Output:
            A link to the development server.

        Returns:
            None.
        """

        await ctx.send('_Need help with bugs or want to request a feature? Join the Discord!_'
                       '\nhttps://discord.gg/fgHEWdt')

    @commands.cooldown(1, 600, commands.BucketType.guild)
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    @commands.command(name='setprefix', help='Sets the bot\'s prefix for this guild. Administrator use only.')
    async def set_prefix(self, ctx: commands.Context, pre: str) -> None:
        """
        A method to change the command prefix for a guild. Only usable by a guild's administrators.

        Checks:
            cooldown(): Whether or not the command is on cooldown. Can be used (1) time per (10) minutes per (Guild).
            has_permissions(administrator): Whether or not the invoking user is an administrator.
            guild_only(): Whether or not the command was invoked from a guild. No direct messages.

        Parameters:
            ctx (commands.Context): The invocation context.
            pre (str): The new prefix to use.

        Output:
            Success: Confirmation that the prefix changed.
            Failure: An error noting the change was not completed.

        Returns:
            None.
        """

        try:
            async with aiosqlite.connect(self.bot.database) as db:
                async with db.execute('SELECT EXISTS(SELECT 1 FROM PREFIXES WHERE GUILD_ID=?)',
                                      (ctx.guild.id,)) as cursor:
                    if (await cursor.fetchone())[0] == 1:
                        await db.execute('UPDATE PREFIXES SET PREFIX=? WHERE GUILD_ID=?', (pre, ctx.guild.id))
                        await db.commit()
                        await ctx.send(f'Updated the prefix to `{pre}`.')
                    else:
                        await db.execute('INSERT INTO PREFIXES (GUILD_ID, PREFIX) VALUES (?, ?)', (ctx.guild.id, pre))
                        await db.commit()
                        await ctx.send(f'Changed the prefix to `{pre}`.')
                    self.bot.prefixes[ctx.guild.id] = pre

        except aiosqlite.Error as e:
            await ctx.send('Failed to change the guild\'s prefix.')
            print(f'Set Prefix SQLite Error: {e}')

    @commands.guild_only()
    @commands.command(name='getprefix', aliases=['prefix'], help='Gets the bot\'s prefix for this guild.')
    async def get_prefix(self, ctx: commands.Context) -> None:
        """
        A method that outputs the command prefix for a guild.

        Checks:
            guild_only(): Whether or not the command was invoked from a guild. No direct messages.

        Parameters:
            ctx (commands.Context): The invocation context.

        Output:
            Success: The prefix assigned to the guild.
            Failure: An error noting the prefix could not be fetched.

        Returns:
            None.
        """

        try:
            async with aiosqlite.connect(self.bot.database) as db:
                async with db.execute('SELECT PREFIX FROM PREFIXES WHERE GUILD_ID=?', (ctx.guild.id,)) as cursor:
                    result = await cursor.fetchone()
                    if result is None:
                        await ctx.send(self.bot.default_prefix)
                    else:
                        await ctx.send(f'Prefix: `{result[0]}`')

        except aiosqlite.Error as e:
            await ctx.send('Could not retrieve the guild\'s prefix.')
            print(f'Set Prefix SQLite Error: {e}')

    @commands.command(name='uptime', help='Returns current bot uptime.')
    async def uptime(self, ctx: commands.Context) -> None:
        """
        A method that outputs the uptime of the bot.

        Parameters:
            ctx (commands.Context): The invocation context.

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

    @commands.command(name='userinfo', aliases=['ui'],
                      help='Generates an embed detailing information about the specified user')
    async def user_info(self, ctx: commands.Context, user: Member) -> None:
        """
        A method that outputs user information.

        Parameters:
            ctx (commands.Context): The invocation context.
            user (discord.Member): The member to generate information about.

        Output:
            Information about the specified user, including creation and join date.

        Returns:
            None.
        """

        embed = Embed(title=f'{str(user)}\'s User Information', color=0x1dcaff)
        if user.nick:
            embed.description = f'Known as **{user.nick}** round\' these parts'
        embed.set_thumbnail(url=user.avatar_url)
        embed.add_field(name='Account Created', value=localize_time(user.created_at))
        embed.add_field(name='Joined Server', value=localize_time(user.joined_at))
        members = sorted(ctx.guild.members, key=lambda x: x.joined_at)
        embed.add_field(name='Join Position', value=str(members.index(user)))
        embed.add_field(name='User ID', value=str(user.id), inline=False)
        embed.add_field(name='User Flags', value=await readable_flags(user.public_flags), inline=False)
        roles = ', '.join(str(x) for x in (user.roles[::-1])[:-1])
        embed.add_field(name='Roles', value=roles if roles else 'None', inline=False)
        embed.set_footer(text="Please report any issues to my owner!")

        await ctx.send(embed=embed)

    @commands.guild_only()
    @commands.command(name='sync')
    async def sync_permissions(self, ctx: commands.Context):
        """
        A method that re-syncs permissions with the channel's parent category.

        Parameters:
            ctx (commands.Context): The invocation context.

        Output:
            Command state information.

        Returns:
            None.
        """

        if not ctx.channel.category:
            # await ctx.send('This channel does not belong to a category.')
            return
        if ctx.channel.permissions_synced:
            # await ctx.send('Permissions for this channel are already synced')
            return

        author_can_edit = ctx.channel.category.permissions_for(ctx.author).manage_channels

        if not author_can_edit:
            # await ctx.send('You do not have permission to sync this channel.')
            return

        await ctx.channel.edit(sync_permissions=True)
        await ctx.send('Successfully synced permissions.')

    @commands.command(name='unicodeemoji', aliases=['ue', 'eu'])
    async def unicode_emoji(self, ctx: commands.Context, emoji: str):
        """
        A method to convert emojis to their respective unicode string.

        Parameters:
            ctx (commands.Context): The invocation context.
            emoji (str): The emoji to encode.

        Output:
            The unicode string representing the emoji.

        Returns:
            None.
        """

        await ctx.send(f"`{emoji.encode('unicode-escape').decode('ASCII')}`")

    @commands.has_guild_permissions(manage_emojis=True)
    @commands.bot_has_guild_permissions(manage_emojis=True)
    @commands.command(name='raw_yoink', aliases=['rawyoink'], help='Yoinks an emoji based on it\'s id.')
    async def raw_yoink_emoji(self, ctx: commands.Context,  source: int, name: Optional[str] = None,
                              animated: Optional[bool] = False) -> None:
        """
        A method to "yoink" an emoji. Retrieves the emoji as an asset and uploads it to the current guild.

        Parameters:
            ctx (commands.Context): The invocation context.
            source (Optional[discord.Message]): The message to extract emojis from.
            animated (Optional[bool]): Whether or not the emoji is animated.
            name (Optional[str]): The name of the emoji.

        Output:
            Command state information.

        Returns:
            None.
        """

        name = name if name else str(source)

        try:
            extension = 'gif' if animated else 'png'
            emoji_asset = await network_request(f'https://cdn.discordapp.com/emojis/{source}.{extension}?size=96')
        except discord.HTTPException as e:
            await ctx.send(f'**{name}** failed with `{e.text}`')
            return

        try:
            await ctx.guild.create_custom_emoji(name=name, image=emoji_asset, reason=f'Yoink\'d by {ctx.author}')
        except discord.HTTPException as e:
            await ctx.send(f'**{name}** failed with `{e.text}`')
            return

        await ctx.send(f'Successfully yoink\'d the following emoji:\n```{name}```')

    @commands.has_guild_permissions(manage_emojis=True)
    @commands.bot_has_guild_permissions(manage_emojis=True)
    @commands.command(name='yoink', help='Yoinks emojis from the specified message.')
    async def yoink_emoji(self, ctx: commands.Context, source: Optional[MessageOrMessageReplyConverter]) -> None:
        """
        A method to "yoink" an emoji. Retrieves the emoji as an asset and uploads it to the current guild.

        Parameters:
            ctx (commands.Context): The invocation context.
            source (Optional[discord.Message]): The message to extract emojis from.

        Output:
            Command state information.

        Returns:
            None.
        """

        if not isinstance(source, discord.Message):
            raise commands.MissingRequiredArgument(Parameter('message_source', Parameter.POSITIONAL_ONLY))

        emojis = findall(r'<(?P<animated>a?):(?P<name>[a-zA-Z0-9_]{2,32}):(?P<id>[0-9]{18,22})>', source.content)

        if not emojis:
            await ctx.send('Failed to extract any emojis from the specified message.')
            return

        guild_emoji_names = [x.name for x in ctx.guild.emojis]
        guild_emoji_ids = [x.id for x in ctx.guild.emojis]

        unique_emojis = []
        non_unique_emoji = []

        for emoji in emojis:
            if int(emoji[2]) in guild_emoji_ids:
                non_unique_emoji.append(f'_{emoji[1]}_ failed with `AlreadyAdded`')
            elif emoji[1] in guild_emoji_names:
                non_unique_emoji.append(f'_{emoji[1]}_ failed with `DuplicateName`')
            else:
                unique_emojis.append(emoji)

        if not unique_emojis:
            await ctx.send(f'No unique emojis found. The potential emoji are either from this server or have the '
                           f'same name as an existing emoji.\n\n**Failure Reasons:**\n{", ".join(non_unique_emoji)}')
            return

        if ctx.guild.emoji_limit < len(ctx.guild.emojis) + len(unique_emojis):
            await ctx.send(f'You do not have enough emoji slots to upload all of these emojis. '
                           f'You have {ctx.guild.emoji_limit - len(ctx.guild.emojis)} remaining slots.')
            return

        success, failed = [], []

        for emoji in unique_emojis:
            try:
                extension = 'gif' if emoji[0] else 'png'
                emoji_asset = await network_request(
                    f'https://cdn.discordapp.com/emojis/{emoji[2]}.{extension}?size=96',
                    return_type=NetworkReturnType.BYTES
                )
            except discord.HTTPException as e:
                failed.append(f'**{emoji[1]}** failed with `{e.text}`')
                continue

            try:
                await ctx.guild.create_custom_emoji(
                    name=emoji[1], image=emoji_asset, reason=f'Yoink\'d by {ctx.author}'
                )
            except discord.HTTPException as e:
                failed.append(f'**{emoji[1]}** failed with `{e.text}`')
                continue

            success.append(emoji[1])

        response = f'Successfully yoink\'d the following emoji:\n' \
                   f'```{", ".join(success) if success else "None"}```'

        if failed:
            response += f'\nFailed to yoink the following emoji:\n' \
                        f'```{", ".join(failed) if failed else "None"}```'

        await ctx.send(response)


async def readable_flags(flags: PublicUserFlags) -> str:
    """
    A method that converts PublicUserFlag enums to usable strings.

    Parameters:
        flags (PublicUserFlags): The public user flags for a given user.

    Returns:
        (str): An embed-ready string detailing the user's flags.
    """

    flag_strings = [' '.join(x.capitalize() for x in flag[0].split('_')) for flag in flags if flag[1]]

    if flag_strings:
        return ', '.join(flag_strings)
    else:
        return 'None'


def setup(bot: DreamBot) -> None:
    """
    A setup function that allows the cog to be treated as an extension.

    Parameters:
        bot (DreamBot): The bot the cog should be added to.

    Returns:
        None.
    """

    bot.add_cog(Utility(bot))
    print('Completed Setup for Cog: UtilityFunctions')
