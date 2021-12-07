from discord.ext import commands as discord_commands
from twitchio.ext import commands as twitch_commands
from os import getenv
from time import time
from random import shuffle
from dreambot import DreamBot
import asyncio
import twitchio

# https://github.com/TwitchIO/TwitchIO/issues/130


class Twitch(discord_commands.Cog):
    def __init__(self, bot: DreamBot) -> None:
        self.discord_bot = bot
        self.bot = twitch_commands.Bot(irc_token=getenv('TWITCH_TOKEN'), client_id=getenv('TWITCH_ID'),
                                       nick=getenv('TWITCH_NICK'), prefix=getenv('PREFIX'),
                                       initial_channels=['#csuflol'])
        self.discord_bot.loop.create_task(self.bot.start())
        self.bot.command(name="giveaway")(self.twitch_giveaway)
        self.bot.listen("event_message")(self.event_message)
        self.active_chatters = {}

    async def event_message(self, message: twitchio.Message):
        """
        A twitchio listener event that is called whenever a message is sent.

        Parameters:
           message (twitchio.Message): The message sent.

        Returns:
            None.
        """

        self.active_chatters[message.author.name] = int(time())
        self.active_chatters.pop('csuflol', None)

    async def twitch_giveaway(self, ctx: twitchio.Context, interval: int = None, remove: bool = False):
        """
        A twitch.Command to invoke a giveaway in the designated Twitch channel.

        Parameters:
            ctx (twitchio.Context): The invocation context.
            interval (int): The time interval in minutes to consider users eligible for a giveaway.
            remove (bool): Whether or not the winner should be removed form list of eligible users.

        Returns:
            None.
        """

        if not ctx.author.is_mod or interval is None:
            return

        try:
            interval = int(interval)
            remove = bool(remove)
        except TypeError:
            return

        current_time = int(time())
        eligible_users = [user for user, timestamp in self.active_chatters.items()
                          if timestamp > (current_time - (interval * 60))]

        if len(eligible_users) > 0:
            shuffle(eligible_users)
            winner = eligible_users[0]
            await ctx.send(f'@{winner} has won the giveaway!')

            if remove:
                self.active_chatters.pop(winner)

        else:
            await ctx.send('No users are eligible for the giveaway.')

    @discord_commands.has_role('Community Stream')
    @discord_commands.command(name='twitchgiveaway', aliases=['tg'])
    async def discord_command(self, ctx: discord_commands.Context, interval: int, remove=True):
        """
        A discord_commands.Command to invoke the method `twitch_giveaway` in the designated Twitch channel.

        Parameters:
            ctx (discord_commands.Context): The invocation context.
            interval (int): The time interval in minutes to consider users eligible for a giveaway.
            remove (bool): Whether or not the winner should be removed form list of eligible users.

        Returns:
            None.
        """

        channel = self.bot.get_channel('csuflol')

        current_time = int(time())
        eligible_users = [user for user, timestamp in self.active_chatters.items()
                          if timestamp > (current_time - (interval * 60))]

        if len(eligible_users) > 0:
            shuffle(eligible_users)
            winner = eligible_users[0]
            await channel.send(f'@{winner} has won the giveaway!')
            await ctx.send(f'@{winner} has won the giveaway!')

            if remove:
                self.active_chatters.pop(winner)
        else:
            await channel.send('No users are eligible for the giveaway.')
            await ctx.send('No users are eligible for the giveaway.')

    def cog_unload(self):
        """
        A method detailing custom extension unloading procedures.
        Clears internal caches and immediately and forcefully exits any discord.ext.tasks.

        Parameters:
            None.

        Output:
            None.

        Returns:
            None.
        """

        asyncio.run_coroutine_threadsafe(self.bot.stop(), self.discord_bot.loop)
        print('Completed Unload for Cog: Twitch')


def setup(bot: DreamBot):
    """
    A setup function that allows the cog to be treated as an extension.

    Parameters:
        bot (DreamBot): The bot the cog should be added to.

    Returns:
        None.
    """

    bot.add_cog(Twitch(bot))
    print('Completed Setup for Cog: Twitch')
