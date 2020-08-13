from discord.ext import commands
from utils import execute_query, retrieve_query
import discord

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
    async def purge(self, ctx, limit: int = 0, user: discord.User = None):
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

    @commands.has_guild_permissions(manage_guild=True)
    @commands.command(name='getdefaultrole', aliases=['gdr'],
                      help='Displays the role (if any) users are auto-granted on joining the guild.')
    async def get_default_role(self, ctx: commands.Context) -> None:
        """
        A method for checking which role (if any) will be auto-granted to new users joining the guild.

        Checks:
            has_guild_permissions(manage_guild): Whether or not the invoking user can manage the guild.

        Parameters:
            ctx (commands.Context): The invocation context.

        Output:
            A message detailing the default role for the guild.

        Returns:
            None.
        """

        if role := (await retrieve_query(self.bot.DATABASE_NAME, 'SELECT ROLE_ID FROM DEFAULT_ROLES WHERE GUILD_ID=?',
                                         (ctx.guild.id,))):
            role = ctx.guild.get_role(role[0][0])
            await ctx.send(f'The default role for the server is **{role.name}**')
        else:
            await ctx.send(f'There is no default role set for the server.')

    @commands.cooldown(1, 600, commands.BucketType.guild)
    @commands.has_guild_permissions(manage_guild=True, manage_roles=True)
    @commands.bot_has_guild_permissions(manage_roles=True)
    @commands.command(name='setdefaultrole', aliases=['sdr'],
                      help='Sets the role users are auto-granted on joining.'
                           '\nTo remove the default role, simply call this command without passing a role.'
                           '\nNote: The role selected must be lower than the bot\'s role and lower than your role.')
    async def set_default_role(self, ctx: commands.Context, role: discord.Role = None) -> None:
        """
        A method for checking which role (if any) will be auto-granted to new users joining the guild.

        Checks:
            cooldown(): Whether or not the command is on cooldown. Can be used (1) time per (10) minutes per (Guild).
            has_guild_permissions(manage_guild, manage_roles):
                Whether or not the invoking user can manage the guild and roles.

        Parameters:
            ctx (commands.Context): The invocation context.
            role (discord.Role): The role to set as the default role. Could be None.

        Output:
            Success: A confirmation message detailing the new default role.
            Failure: An error message detailing why the command failed.

        Returns:
            None.
        """

        bot_role = ctx.me.top_role
        invoker_role = ctx.author.top_role

        # todo: rewrite all sends to use logging channel if available

        if not role:
            await execute_query(self.bot.DATABASE_NAME, 'DELETE FROM DEFAULT_ROLES WHERE GUILD_ID=?', (ctx.guild.id,))
            await ctx.send('Cleared the default role for the guild.')
            return
        # ensure all roles are fetched
        elif all((role, bot_role, invoker_role)):
            # ensure both the bot and the initializing user have the ability to set the role
            if role >= bot_role or role >= invoker_role:
                await ctx.send('Cannot set a default role higher than or equal to the bot\'s or your highest role.')
                return
            else:
                await execute_query(self.bot.DATABASE_NAME,
                                    'INSERT INTO DEFAULT_ROLES (GUILD_ID, ROLE_ID) VALUES (?, ?) ON CONFLICT(GUILD_ID) '
                                    'DO UPDATE SET ROLE_ID=EXCLUDED.ROLE_ID', (ctx.guild.id, role.id))
                await ctx.send(f'Updated the default role to **{role.name}**')
                return
        else:
            await ctx.send('Failed to set the default role for the guild.')

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if role := (await retrieve_query(self.bot.DATABASE_NAME, 'SELECT ROLE_ID FROM DEFAULT_ROLES WHERE GUILD_ID=?',
                                         (member.guild.id,))):
            role = member.guild.get_role(role[0][0])
            try:
                await member.add_roles(role, reason='Default Role Assignment', atomic=True)
            except discord.Forbidden:
                pass  # todo: add logging note here
            except discord.HTTPException:
                pass  # todo: add logging note here


"""
LIST OF LOG REASONS
1) Action Failed
2) User Joined
3) User Left
4) Auto-role (set/changed)
5) Message Edited
6) Message Deleted
"""


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
