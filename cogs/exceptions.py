from discord.ext import commands
from discord import HTTPException
from sys import stderr
from traceback import print_exception


class Exceptions(commands.Cog):
    """
    A Cogs class that provides centralized exception handling for the bot.

    Attributes:
        bot (commands.Bot): The Discord bot.
    """

    def __init__(self, bot):
        """
        The constructor for the Exceptions class.

        Parameters:
            bot (commands.Bot): The Discord bot.
        """

        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """
        A listener method that is called whenever a command encounters an error.
        Most user-facing exceptions output a message detailing why the command invocation failed.
        Other exceptions are either handled silently or logged.

        Parameters:
            ctx (commands.Context): The invocation context.
            error (Exception): The encountered error.

        Output:
            (Not Guaranteed): The status of the error, should the user require context.

        Returns:
            None.
        """

        # Prevent any commands with local handlers being handled
        if hasattr(ctx.command, 'on_error'):
            return

        ignored = (commands.CommandNotFound, commands.UserInputError)
        permissions = (commands.NotOwner, commands.MissingPermissions)
        # Allows us to check for original exceptions raised and sent to CommandInvokeError
        # If nothing is found, keep the exception passed in
        error = getattr(error, 'original', error)

        # Anything in ignored will return without any additional handling
        if isinstance(error, ignored):
            return

        elif isinstance(error, commands.DisabledCommand):
            await ctx.send(f'{ctx.command} has been disabled.')
            return

        elif isinstance(error, commands.NoPrivateMessage):
            try:
                await ctx.author.send(f'{ctx.command} can not be used in Private Messages.')
                return
            except HTTPException as e:
                print(f'Commands Error Handler Error: (NoPrivateMessage) {e}')

        # Check where the command came from
        elif isinstance(error, commands.BadArgument):
            # Check if the command being invoked is 'tag list'
            if ctx.command.qualified_name == 'tag list':
                await ctx.send('I could not find that member. Please try again.')
                return

        # Using the permissions tuple allows us to handle multiple errors of similar types
        # Errors where the user does not have the authority to execute the command
        elif isinstance(error, permissions):
            await ctx.send(f'{ctx.message.author.mention}, you do not have permission to use this command!')
            return

        # Calling a command currently on cooldown
        elif isinstance(error, commands.CommandOnCooldown):
            if ctx.author.id == self.bot.owner_id:
                await ctx.reinvoke()
            else:
                await ctx.send(f'{ctx.message.author.mention}, please wait {int(error.retry_after)} seconds '
                               f'before calling this command again!')
                return

        # Bot cannot execute command due to insufficient permissions
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send(f'{ctx.message.author.mention}, I lack the {error}\n{error.__dict__}'
                           f' permissions for this command')
            return

        # All other errors not returned come here. Print the default traceback
        print('Ignoring exception in command {}:'.format(ctx.command), file=stderr)
        print_exception(type(error), error, error.__traceback__, file=stderr)


def setup(bot):
    """
    A setup function that allows the cog to be treated as an extension.

    Parameters:
        bot (commands.Bot): The bot the cog should be added to.

    Returns:
        None.
    """

    bot.add_cog(Exceptions(bot))
    print('Completed Setup for Cog: Exceptions')
