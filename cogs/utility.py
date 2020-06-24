from discord.ext import commands
from discord import TextChannel, User, Emoji, HTTPException
import datetime
import pytz
import aiosqlite


class UtilityFunctions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='time', help='Responds with the current time. Can be supplied with a timezone.\nFor a full '
                      'list of supported timezones, see https://en.wikipedia.org/wiki/List_of_tz_database_time_zones')
    async def current_time(self, ctx, timezone='UTC'):
        if timezone not in pytz.all_timezones:
            timezone = 'UTC'
        today = datetime.datetime.now(pytz.timezone(timezone))
        printable_format = today.strftime("%I:%M %p on %A, %B %d, %Y (%Z)")
        await ctx.send(f'{ctx.author.mention}, the current time is {printable_format}')

    @commands.command(name='devserver', help='Responds with an invite link to the development server. Useful for '
                      'getting assistance with a bug, or requesting a new feature!')
    async def dev_server(self, ctx):
        message = '_Need help with bugs or want to request a feature? Join the Discord!_'\
                  '\nhttps://discord.gg/fgHEWdt'
        await ctx.send(message)

    @commands.is_owner()
    @commands.command(name='length', help='Returns the number of messages sent to a specified channel.', hidden=True)
    async def length(self, ctx, channel: TextChannel):
        async with ctx.channel.typing():
            await ctx.send(f'The length of `#{channel}` in guild `{ctx.guild.name}` is'
                           f' {len(await channel.history(limit=None).flatten())} messages.')

    @length.error
    async def length_error(self, ctx, error):
        await ctx.send(f'Command `length` failed with error: `{error.__cause__}`')

    @commands.is_owner()
    @commands.command(name='countemoji', help='Returns the number of times an emoji was by a user.', hidden=True)
    async def count_emoji(self, ctx, user: User, emoji: Emoji):
        total = 0

        async with ctx.channel.typing():
            for channel in ctx.guild.text_channels:
                async for message in channel.history(limit=None):
                    if message.author.id == user.id:
                        if str(emoji) in message.content:
                            total += 1

        await ctx.send(f'User `{str(user)}` has sent {str(emoji)} {total} times in guild `{ctx.guild.name}`.')

    @count_emoji.error
    async def count_emoji_error(self, ctx, error):
        await ctx.send(f'Command `countemoji` failed with error: `{error.__cause__}`')

    @commands.is_owner()
    @commands.command(name='archive', help='Archives a channel.', hidden=True)
    async def archive(self, ctx, start, end):
        begin = self.bot.get_channel(int(start))
        destination = self.bot.get_channel(int(end))

        if begin is None or destination is None:
            await ctx.send('Could not fetch one or more channels.')

        else:
            async with destination.typing():
                async for message in begin.history(limit=None, oldest_first=True):
                    if len(message.attachments) > 0:
                        try:
                            files = []
                            for attachment in message.attachments:
                                files.append(await attachment.to_file())
                        except HTTPException:
                            pass

                        if len(message.clean_content) > 1800:
                            await destination.send(f'**{message.author} - '
                                                   f'{message.created_at.strftime("%I:%M%p on %A, %B %d, %Y")}**'
                                                   f'\n{message.clean_content[:1000]}')
                            await destination.send(f'**{message.author} - '
                                                   f'{message.created_at.strftime("%I:%M%p on %A, %B %d, %Y")}**'
                                                   f'\n{message.clean_content[1000:]}', files=files)
                        else:
                            await destination.send(f'**{message.author} - '
                                                   f'{message.created_at.strftime("%I:%M%p on %A, %B %d, %Y")}**'
                                                   f'\n{message.clean_content}', files=files)
                    else:
                        if len(message.clean_content) > 1800:
                            await destination.send(f'**{message.author} - '
                                                   f'{message.created_at.strftime("%I:%M%p on %A, %B %d, %Y")}**'
                                                   f'\n{message.clean_content[:1000]}')
                            await destination.send(f'**{message.author} - '
                                                   f'{message.created_at.strftime("%I:%M%p on %A, %B %d, %Y")}**'
                                                   f'\n{message.clean_content[1000:]}')
                        else:
                            await destination.send(f'**{message.author} - '
                                                   f'{message.created_at.strftime("%I:%M%p on %A, %B %d, %Y")}**'
                                                   f'\n{message.clean_content}')

    @archive.error
    async def archive_error(self, ctx, error):
        await ctx.send(f'Command `archive` failed with error: `{error.__cause__}`')

    @commands.cooldown(1, 600, commands.BucketType.guild)
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    @commands.command(name='setprefix', help='Sets the bot\'s prefix for this guild. Administrator use only.')
    async def set_prefix(self, ctx, pre):
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
        try:
            async with aiosqlite.connect(self.bot.DATABASE_NAME) as db:
                async with db.execute('SELECT PREFIX FROM PREFIXES WHERE GUILD_ID=?', (ctx.guild.id,)) as cursor:
                    result = await cursor.fetchone()
                    if result is None:
                        return await ctx.send(self.bot.DEFAULT_PREFIX)
                    else:
                        return await ctx.send(f'Prefix: `{result[0]}`')
        except aiosqlite.Error as e:
            await ctx.send('Could not retrieve the guild\'s prefix.')
            print(f'Set Prefix SQLite Error: {e}')

    @commands.command(name='uptime', help='Returns current bot uptime.')
    async def uptime(self, ctx):
        time = datetime.datetime.now() - self.bot.uptime
        hours, remainder = divmod(time.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        await ctx.send(f'Bot Epoch: {self.bot.uptime.strftime("%I:%M %p on %A, %B %d, %Y")}'
                       f'\nBot Uptime: {time.days} Days, {hours} Hours, {minutes} Minutes, {seconds} Seconds')


def setup(bot):
    bot.add_cog(UtilityFunctions(bot))
    print('Completed Setup for Cog: UtilityFunctions')
