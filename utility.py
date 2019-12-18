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

    @commands.command(name='logs', help='Pulls every message sent to a channel by the specified user. The bot then '
                      'writes the messages to a text file')
    @commands.is_owner()
    async def pullhistory(self, ctx):
        user = ctx.message.mentions[0] if len(ctx.message.mentions) > 0 else None

        if user is None:
            return await ctx.send(f'Command `logs` failed with error: `No Target User`')

        with open('Logs/' + ctx.channel.name + '-' + user.id + '.txt', 'w', encoding='utf-8') as file:
            async for message in ctx.channel.history(limit=None):
                if message.author.id == user.id:
                    file.write(f'{message.clean_content}\n')

        await ctx.send('Finished')

    @pullhistory.error
    async def pullhistory_error(self, ctx, error):
        await ctx.send(f'Command `logs` failed with error: `{error.__cause__}`')

    @commands.command(name='screenshare', help='Generates a link that allows you to screenshare in a '
                      'guild\'s voice channel.',  aliases=['ss'])
    async def screenshare(self, ctx):
        if ctx.author.voice is None:
            return

        await ctx.send(f'{ctx.author.mention}, here\'s a link to screenshare in your current voice channel: '
                       f'<http://www.discordapp.com/channels/{ctx.guild.id}/{ctx.author.voice.channel.id}>')
