from discord.ext import commands
from discord import User

# todo: Add automatic role joining
# todo: not this cog, reaction roles
# todo: set logging channel (table: guild_id -> channel_id, permissions)
# todo: implement logging bit permissions


class Moderation(commands.Cog):
    """
    A Cogs class that contains commands for moderating a guild.

    Attributes:
        bot (commands.Bot): The Discord bot class.
    """

    def __init__(self, bot):
        """
        The constructor for the Moderation class.

        Parameters:
            bot (DreamBot): The Discord bot class.
        """

        self.bot = bot

    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True, read_message_history=True)
    @commands.command(name='purge', help='Purges n+1 messages from the current channel. If a user is supplied, the bot '
                                         'will purge any message from that user in the last n messages.')
    async def purge(self, ctx, limit: int = 0, user: User = None):
        """
        A method to purge messages from a channel.
        Should a user ID be supplied, any messages from that user in the last (limit) messages will be deleted.

        Checks:
            has_permissions(manage_messages): Whether or not the invoking user can manage messages.
            bot_has_permissions(manage_messages, read_message_history): Whether or not the bot can manage messages
                and read the message history of a channel, both of which are required for the deletion of messages.

        Parameters:
            ctx (commands.Context): The invocation context.
            limit (int): The number of messages to purge. Default: 0.
            user (discord.User): The User to delete messages from. Default: None.

        Output:
            None.

        Returns:
            None.
        """

        if user is None:
            await ctx.channel.purge(limit=limit + 1)
        else:
            def purge_check(message):
                return message.author.id == user.id
            await ctx.channel.purge(limit=limit + 1, check=purge_check)


def setup(bot):
    """
    A setup function that allows the cog to be treated as an extension.

    Parameters:
        bot (DreamBot): The bot the cog should be added to.

    Returns:
        None.
    """

    bot.add_cog(Moderation(bot))
    print('Completed Setup for Cog: Moderation')
