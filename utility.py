from discord.ext import commands
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
