import traceback
import sys
from discord.ext import commands


class Exceptions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        # This prevents any commands with local handlers being handled
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
            return await ctx.send(f'{ctx.command} has been disabled.')

        elif isinstance(error, commands.NoPrivateMessage):
            try:
                return await ctx.author.send(f'{ctx.command} can not be used in Private Messages.')
            except:
                pass

        # Check where the command came from
        elif isinstance(error, commands.BadArgument):
            if ctx.command.qualified_name == 'tag list':  # Check if the command being invoked is 'tag list'
                return await ctx.send('I could not find that member. Please try again.')

        # Using the permissions tuple allows us to handle multiple errors of similar types
        # Errors where the using does not have the authority to execute the command
        elif isinstance(error, permissions):
            return await ctx.send(f'{ctx.message.author.mention}, you do not have permission to use this command!')

        # Calling a command currently on cooldown
        elif isinstance(error, commands.CommandOnCooldown):
            return await ctx.send(f'{ctx.message.author.mention}, please wait {int(error.retry_after)} seconds before'
                                  f' calling this command again!')

        # Bot cannot execute command due to insufficient permissions
        elif isinstance(error, commands.MissingPermissions):
            return await ctx.send(f'{ctx.message.author.mention}, I lack the {error}\n{error.__dict__} permissions for this command')

        # All other errors not returned come here. Print the default traceback
        print('Ignoring exception in command {}:'.format(ctx.command), file=sys.stderr)
        traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)
