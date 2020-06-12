from discord.ext import commands
from discord import TextChannel, User, Emoji, HTTPException
import datetime
import pytz


class UtilityFunctions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='time', help='Responds with the current time. Can be supplied with a timezone.\nFor a full '
                      'list of supported timezones, see https://en.wikipedia.org/wiki/List_of_tz_database_time_zones')
    async def current_time(self, ctx, timezone='UTC'):
        if timezone not in pytz.all_timezones:
            timezone = 'UTC'
        today = datetime.datetime.now(pytz.timezone(timezone))
        printable_format = today.strftime('%I:%M%p on %A, %B %d, %Y (%Z)')
        await ctx.send(f'{ctx.author.mention}, the current time is {printable_format}')

    @commands.command(name='devserver', help='Responds with an invite link to the development server. Useful for '
                      'getting assistance with a bug, or requesting a new feature!')
    async def devserver(self, ctx):
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
    async def countemoji(self, ctx, user: User, emoji: Emoji):
        total = 0

        async with ctx.channel.typing():
            for channel in ctx.guild.text_channels:
                async for message in channel.history(limit=None):
                    if message.author.id == user.id:
                        if str(emoji) in message.content:
                            total += 1

        await ctx.send(f'User `{str(user)}` has sent {str(emoji)} {total} times in guild `{ctx.guild.name}`.')

    @countemoji.error
    async def countemoji_error(self, ctx, error):
        await ctx.send(f'Command `countemoji` failed with error: `{error.__cause__}`')

    @commands.is_owner()
    @commands.command(name='archive', help='Archives a channel.', hidden=True)
    # async def archive(self, ctx, start: TextChannel, end: TextChannel):
    async def archive(self, ctx, start, end):
        print('Invoked')
        begin = self.bot.get_channel(int(start))
        print(begin)
        destination = self.bot.get_channel(int(end))
        print(destination)

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


def setup(bot):
    bot.add_cog(UtilityFunctions(bot))
    print('Completed Setup for Cog: UtilityFunctions')
