from discord.ext import commands


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='purge', help='Purges n+1 messages from the current channel. A user ID can be supplied to '
                      'only delete messages from that user.')
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def purge(self, ctx, limit: int = 0):
        await ctx.channel.purge(limit=limit + 1)
