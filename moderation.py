from discord.ext import commands
from discord import User


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.delete_id = None

    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True, read_message_history=True)
    @commands.command(name='purge', help='Purges n+1 messages from the current channel. If a user is supplied, the bot '
                                         'will purge any message from that user in the last n messages.')
    async def purge(self, ctx, limit: int = 0, user: User = None):
        if user is None:
            self.delete_id = None
        else:
            self.delete_id = user.id

        await ctx.channel.purge(limit=limit + 1, check=self.purgecheck)

    def purgecheck(self, message):
        if self.delete_id is None:
            return True
        else:
            return message.author.id == self.delete_id
