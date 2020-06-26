from discord.ext import commands
import datetime
import pytz
import aiosqlite


class Utility(commands.Cog):
    """
    A Cogs class that contains utility commands for the bot.

    Attributes:
        bot (commands.Bot): The Discord bot class.
    """

    def __init__(self, bot):
        """
        The constructor for the UtilityFunctions class.

        Parameters:
           bot (DreamBot): The Discord bot class.
        """

        self.bot = bot

    @commands.command(name='time', help='Responds with the current time. Can be supplied with a timezone.\nFor a full '
                      'list of supported timezones, see https://en.wikipedia.org/wiki/List_of_tz_database_time_zones')
    async def current_time(self, ctx, timezone='UTC'):
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
    async def dev_server(self, ctx):
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
    async def set_prefix(self, ctx, pre):
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
            async with aiosqlite.connect(self.bot.DATABASE_NAME) as db:
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
    async def get_prefix(self, ctx):
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
            async with aiosqlite.connect(self.bot.DATABASE_NAME) as db:
                async with db.execute('SELECT PREFIX FROM PREFIXES WHERE GUILD_ID=?', (ctx.guild.id,)) as cursor:
                    result = await cursor.fetchone()
                    if result is None:
                        await ctx.send(self.bot.DEFAULT_PREFIX)
                    else:
                        await ctx.send(f'Prefix: `{result[0]}`')

        except aiosqlite.Error as e:
            await ctx.send('Could not retrieve the guild\'s prefix.')
            print(f'Set Prefix SQLite Error: {e}')

    @commands.command(name='uptime', help='Returns current bot uptime.')
    async def uptime(self, ctx):
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
        hours, remainder = divmod(time.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        await ctx.send(f'Bot Epoch: {self.bot.uptime.strftime("%I:%M %p on %A, %B %d, %Y")}'
                       f'\nBot Uptime: {time.days} Days, {hours} Hours, {minutes} Minutes, {seconds} Seconds')


def setup(bot):
    """
    A setup function that allows the cog to be treated as an extension.

    Parameters:
        bot (DreamBot): The bot the cog should be added to.

    Returns:
        None.
    """

    bot.add_cog(Utility(bot))
    print('Completed Setup for Cog: UtilityFunctions')
