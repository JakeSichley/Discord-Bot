from discord.ext import commands, menus
from utils import execute_query, retrieve_query, exists_query
from enum import Enum
from typing import List
from asyncio import Condition
import discord


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
            bot (commands.Bot): The Discord bot.
        """

        self.bot = bot

    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True, read_message_history=True)
    @commands.command(name='purge', help='Purges n+1 messages from the current channel. If a user is supplied, the bot '
                                         'will purge any message from that user in the last n messages.')
    async def purge(self, ctx, limit: int = 0, user: discord.Member = None):
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
    async def on_member_join(self, member: discord.Member) -> None:
        """
        A commands.Cog listener event that is called whenever a new user joins a guild.

        Functionality:
            (1) If logging is enabled, logs the new member joining to the specified channel.
            (2) If a default role is set, add the default role to the new member.

        Parameters:
            member (discord.Member): The member that joined the guild.

        Returns:
            None.
        """

        # retrieve logging information
        if logging := (await retrieve_query(self.bot.DATABASE_NAME,
                                            'SELECT CHANNEL_ID, BITS FROM LOGGING WHERE GUILD_ID=?',
                                            (member.guild.id,))):
            await log_to_channel(self.bot, LoggingActions.USER_JOINED, logging[0][1], logging[0][0],
                                 f'**{str(member)}** joined the guild.')

        # retrieve role information
        if role := (await retrieve_query(self.bot.DATABASE_NAME, 'SELECT ROLE_ID FROM DEFAULT_ROLES WHERE GUILD_ID=?',
                                         (member.guild.id,))):
            role = member.guild.get_role(role[0][0])

            try:
                await member.add_roles(role, reason='Default Role Assignment', atomic=True)
            except discord.Forbidden:
                await log_to_channel(self.bot, LoggingActions.ACTION_FAILED, logging[0][1], logging[0][0],
                                     'Default Role Error (Forbidden). Default Role has been cleared.')
                await execute_query(self.bot.DATABASE_NAME, 'DELETE FROM DEFAULT_ROLES WHERE GUILD_ID=?',
                                    (member.guild.id,))
            except discord.HTTPException:
                await log_to_channel(self.bot, LoggingActions.ACTION_FAILED, logging[0][1], logging[0][0],
                                     'Default Role Error (Generic Exception). Default Role has been cleared.')
                await execute_query(self.bot.DATABASE_NAME, 'DELETE FROM DEFAULT_ROLES WHERE GUILD_ID=?',
                                    (member.guild.id,))

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        """
        A commands.Cog listener event that is called whenever a member leaves or is removed from a guild.

        Functionality:
            If logging is enabled, logs the member removal to the specified channel.

        Parameters:
            member (discord.Member): The member that left or was removed from the guild.

        Returns:
            None.
        """

        # retrieve logging information
        if logging := (await retrieve_query(self.bot.DATABASE_NAME,
                                            'SELECT CHANNEL_ID, BITS FROM LOGGING WHERE GUILD_ID=?',
                                            (member.guild.id,))):
            await log_to_channel(self.bot, LoggingActions.USER_LEFT, logging[0][1], logging[0][0],
                                 f'**{str(member)}** left the guild.')

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, member: discord.Member) -> None:
        """
        A commands.Cog listener event that is called whenever a member is banned from a guild.

        Functionality:
            If logging is enabled, logs the member ban to the specified channel.

        Parameters:
            guild (discord.Guild): The guild from which the member was banned.
            member (discord.Member): The member that banned from the guild.

        Returns:
            None.
        """

        # retrieve logging information
        if logging := (await retrieve_query(self.bot.DATABASE_NAME,
                                            'SELECT CHANNEL_ID, BITS FROM LOGGING WHERE GUILD_ID=?',
                                            (guild.id,))):
            await log_to_channel(self.bot, LoggingActions.USER_BANNED, logging[0][1], logging[0][0],
                                 f'**{str(member)}** was banned from the guild.')

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, member: discord.Member) -> None:
        """
        A commands.Cog listener event that is called whenever a member is unbanned from a guild.

        Functionality:
            If logging is enabled, logs the member unban to the specified channel.

        Parameters:
            guild (discord.Guild): The guild from which the member was unbanned.
            member (discord.Member): The member that unbanned from the guild.

        Returns:
            None.
        """

        # retrieve logging information
        if logging := (await retrieve_query(self.bot.DATABASE_NAME,
                                            'SELECT CHANNEL_ID, BITS FROM LOGGING WHERE GUILD_ID=?',
                                            (guild.id,))):
            await log_to_channel(self.bot, LoggingActions.USER_UNBANNED, logging[0][1], logging[0][0],
                                 f'**{str(member)}** was unbanned from the guild.')

    @commands.group(name='auditaction', aliases=['aa', 'auditactions'])
    async def audit_actions(self, ctx: commands.Context) -> None:
        """
        Parent command that handles the audit actions commands.

        Parameters:
            ctx (commands.Context): The invocation context.

        Returns:
            None.
        """

        if ctx.invoked_subcommand is None:
            await ctx.send_help('auditaction')

    @commands.has_guild_permissions(manage_guild=True, view_audit_log=True)
    @audit_actions.command(name='viewactions', aliases=['va'],
                           help='Generates an embed detailing the currently enabled and disabled logging actions for'
                                'this guild.')
    async def view_audit_actions(self, ctx: commands.Context) -> None:
        """
        A method to view the currently enabled audit (logging) actions (if any) for the guild.

        Parameters:
            ctx (commands.Context): The invocation context.

        Returns:
            None.
        """

        if logging := (await retrieve_query(self.bot.DATABASE_NAME,
                                            'SELECT BITS FROM LOGGING WHERE GUILD_ID=?',
                                            (ctx.guild.id,))):
            await ctx.send(embed=build_actions_embed(LoggingActions.all_actions((logging[0][0]))))
        else:
            await ctx.send('You must first set an audit channel before viewing audit actions.'
                           '\n_See `auditactions setchannel` for more information._')

    @commands.max_concurrency(1, commands.BucketType.guild)
    @commands.has_guild_permissions(manage_guild=True, view_audit_log=True)
    @audit_actions.command(name='changeactions', aliases=['ca'],
                           help='Sets the enabled (or disabled) actions you want logged for this guild. To enable or '
                                'disable an action, react with the corresponding reaction. Once you are satisfied '
                                'with the current settings, you can submit them.\nNote: If the cancel reaction is '
                                'selected, changes will be discarded. Changes are also discarded after 5 minutes of '
                                'inactivity.')
    async def change_audit_actions(self, ctx: commands.Context) -> None:
        """
        A method to change the audit (logging) actions for the guild.
        This is implemented via a discord.ext.menus interface.
            For a more detailed description of how the menu works, see the ActionBitMenu class.

        Parameters:
            ctx (commands.Context): The invocation context.

        Returns:
            None.
        """

        if logging := (await retrieve_query(self.bot.DATABASE_NAME,
                                            'SELECT CHANNEL_ID, BITS FROM LOGGING WHERE GUILD_ID=?',
                                            (ctx.guild.id,))):
            bits = int(logging[0][1])

            # create a asyncio.Condition to allow for concurrency checking
            condition = Condition()

            # start the menu
            menu = ActionBitMenu(LoggingActions.all_actions(bits), bits, condition)
            await menu.start(ctx)

            # while the menu is active, this method is active
            # the condition notifies on menu termination (either via success, cancellation, or timeout)
            async with condition:
                await condition.wait()
        else:
            await ctx.send('You must first set an audit channel before changing audit actions.'
                           '\n_See `auditactions setchannel` for more information._')

    @commands.has_guild_permissions(manage_guild=True, view_audit_log=True)
    @audit_actions.command(name='setchannel', aliases=['sc'],
                           help='Sets the Audit Log channel for this guild. Once set, any enabled Logging Actions will '
                                'be sent to this channel.\n\nNote: attempts to search for the specified channel by: '
                                '(1) ID, (2) mention, (3) name.')
    async def set_audit_channel(self, ctx: commands.Context, channel: discord.TextChannel) -> None:
        """
        A method to set (or change) the logging channel for the guild.

        Parameters:
            ctx (commands.Context): The invocation context.
            channel (discord.TextChannel): The new logging channel for the guild.

        Returns:
            None.
        """

        # perform an EXISTS query first since pi doesn't support ON_CONFLICT
        if (await exists_query(self.bot.DATABASE_NAME, 'SELECT EXISTS(SELECT 1 FROM LOGGING WHERE GUILD_ID=?)',
                               (ctx.guild.id,))):
            await execute_query(self.bot.DATABASE_NAME,
                                'UPDATE LOGGING SET CHANNEL_ID=? WHERE GUILD_ID=?',
                                (channel.id, ctx.guild.id))
            await ctx.send(f'Updated the logging channel to {channel.mention}.')
        else:
            await execute_query(self.bot.DATABASE_NAME,
                                'INSERT INTO LOGGING (GUILD_ID, CHANNEL_ID, BITS) VALUES (?, ?, ?)',
                                (ctx.guild.id, channel.id, 0))
            await ctx.send(f'Set the logging channel to {channel.mention}.')


class LoggingActions(Enum):
    """
    An Enum class that contains Logging Action values and methods.
    """

    ACTION_FAILED = 1
    USER_JOINED = 2
    USER_LEFT = 4
    USER_BANNED = 8
    USER_UNBANNED = 16
    MESSAGE_EDIT = 32
    MESSAGE_DELETE = 64

    @classmethod
    def list(cls):
        """
        A class method for returning a list of all LoggingAction names.

        Parameters:
            None.

        Returns:
            (List[LoggingAction.name]): A list of the names of the LoggingActions.
        """

        return list(map(lambda c: c.name, cls))

    @classmethod
    def has_action(cls, action: Enum, action_bits: int) -> bool:
        """
        A class method for checking whether or not an action flag is enabled.

        Parameters:
            action (Enum): The action to check for.
            action_bits (int): The integer containing the action bits.

        Returns:
            (bool): Whether or not the action flag is enabled.
        """

        return bool(action.value & action_bits)

    @classmethod
    def all_actions(cls, action_bits: int) -> [Enum]:
        """
        A class method for parsing action bits, returning all enabled actions.

        Parameters:
            action_bits (int): The integer containing the action bits.

        Returns:
            ([Enum]): All logging actions that are enabled.
        """

        return [action.name for action in LoggingActions if action.value & action_bits]

    @classmethod
    def add_actions_to_bits(cls, actions: [Enum], action_bits: int = 0) -> int:
        """
         A class method for constructing the action bits for the specified actions.

        Parameters:
            actions ([Enum]): The actions to enable.
            action_bits (int): The existing action bits to add further actions to. Default: 0.

        Returns:
            action_bits (int): The integer containing the updated action bits.
        """

        for action in actions:
            action_bits = action_bits | action.value

        return action_bits

    @classmethod
    def remove_actions_from_bits(cls, actions: [Enum], action_bits: int) -> int:
        """
         A class method for removing the action bits for the specified actions.

        Parameters:
            actions ([Enum]): The actions to disable.
            action_bits (int): The existing action bits to remove further actions to.

        Returns:
            action_bits (int): The integer containing the updated action bits.
        """

        for action in actions:
            if action_bits & action.value:
                action_bits = action_bits - action.value

        return action_bits


# noinspection PyUnusedLocal
class ActionBitMenu(menus.Menu):
    """
    The AuditAction's interactive controller menu class.

    Attributes:
        embed (discord.Embed): The embed of the menu.
        bits (int): The LoggingActions bitwise value.
        condition (asyncio.Condition): The invoking command's condition (used for concurrency -> notify).
    """

    def __init__(self, actions: List[LoggingActions], bits: int, condition: Condition) -> None:
        """
        The constructor for the Menu class.

        Parameters:
            actions (List[LoggingActions]): A list of currently toggled LoggingActions names.
            bits (int): The LoggingActions bitwise value.
            condition (asyncio.Condition): The invoking command's condition (used for concurrency -> notify).
        """

        super().__init__(timeout=300, delete_message_after=True, clear_reactions_after=True)
        self.embed = build_actions_embed(actions)
        self.bits = bits
        self.condition = condition

    async def send_initial_message(self, ctx: commands.Context, channel: discord.TextChannel) -> discord.Message:
        """
        Sends the initial menu message.

        Parameters:
            ctx (commands.Context): The context to send the initial message with.
            channel (discord.TextChannel): The channel to send the initial message to.

        Returns:
            (discord.Message): The sent message.
        """

        return await channel.send(embed=self.embed)

    @menus.button(emoji='0\N{variation selector-16}\N{combining enclosing keycap}')
    async def action_failed_button(self, payload: discord.RawReactionActionEvent) -> None:
        """
        The menu's LoggingActions.ACTION_FAILED button.

        Parameters:
            payload (discord.RawReactionActionEvent): The reaction event's details.

        Returns:
            None.
        """

        self.bits = flip_action_bits(LoggingActions.ACTION_FAILED, self.bits)
        await self.update_embed()

    @menus.button(emoji='1\N{variation selector-16}\N{combining enclosing keycap}')
    async def user_joined_button(self, payload: discord.RawReactionActionEvent) -> None:
        """
        The menu's LoggingActions.USER_JOINED button.

        Parameters:
            payload (discord.RawReactionActionEvent): The reaction event's details.

        Returns:
            None.
        """

        self.bits = flip_action_bits(LoggingActions.USER_JOINED, self.bits)
        await self.update_embed()

    @menus.button(emoji='2\N{variation selector-16}\N{combining enclosing keycap}')
    async def user_left_button(self, payload: discord.RawReactionActionEvent) -> None:
        """
        The menu's LoggingActions.USER_LEFT button.

        Parameters:
            payload (discord.RawReactionActionEvent): The reaction event's details.

        Returns:
            None.
        """

        self.bits = flip_action_bits(LoggingActions.USER_LEFT, self.bits)
        await self.update_embed()

    @menus.button(emoji='3\N{variation selector-16}\N{combining enclosing keycap}')
    async def user_banned_button(self, payload: discord.RawReactionActionEvent) -> None:
        """
        The menu's LoggingActions.USER_BANNED button.

        Parameters:
            payload (discord.RawReactionActionEvent): The reaction event's details.

        Returns:
            None.
        """

        self.bits = flip_action_bits(LoggingActions.USER_BANNED, self.bits)
        await self.update_embed()

    @menus.button(emoji='4\N{variation selector-16}\N{combining enclosing keycap}')
    async def user_unbanned_button(self, payload: discord.RawReactionActionEvent) -> None:
        """
        The menu's LoggingActions.USER_UNBANNED button.

        Parameters:
            payload (discord.RawReactionActionEvent): The reaction event's details.

        Returns:
            None.
        """

        self.bits = flip_action_bits(LoggingActions.USER_UNBANNED, self.bits)
        await self.update_embed()

    @menus.button(emoji='5\N{variation selector-16}\N{combining enclosing keycap}')
    async def message_edit_button(self, payload: discord.RawReactionActionEvent) -> None:
        """
        The menu's LoggingActions.MESSAGE_EDIT button.

        Parameters:
            payload (discord.RawReactionActionEvent): The reaction event's details.

        Returns:
            None.
        """

        self.bits = flip_action_bits(LoggingActions.MESSAGE_EDIT, self.bits)
        await self.update_embed()

    @menus.button(emoji='6\N{variation selector-16}\N{combining enclosing keycap}')
    async def message_delete_button(self, payload: discord.RawReactionActionEvent) -> None:
        """
        The menu's LoggingActions.MESSAGE_DELETE button.

        Parameters:
            payload (discord.RawReactionActionEvent): The reaction event's details.

        Returns:
            None.
        """

        self.bits = flip_action_bits(LoggingActions.MESSAGE_DELETE, self.bits)
        await self.update_embed()

    @menus.button(emoji='\u2705')
    async def update_actions(self, payload: discord.RawReactionActionEvent) -> None:
        """
        The menu's finish button. Update's the guild's AuditActions to the selected LoggingActions.

        Parameters:
            payload (discord.RawReactionActionEvent): The reaction event's details.

        Returns:
            None.
        """

        await execute_query(self.bot.DATABASE_NAME, 'UPDATE LOGGING SET BITS=? WHERE GUILD_ID=?',
                            (self.bits, self.ctx.guild.id))
        await self.stop('Updated Audit Actions.')

    @menus.button(emoji='\u274C')
    async def stop_menu(self, payload: discord.RawReactionActionEvent) -> None:
        """
        The menu's stop button. Discards any pending changes to the guild's AuditActions.

        Parameters:
            payload (discord.RawReactionActionEvent): The reaction event's details.

        Returns:
            None.
        """

        await self.stop('Discarded Audit Actions Changes.')

    async def update_embed(self) -> None:
        """
        Updates the menu's embed to reflect any pending changes to the AuditActions.

        Parameters:
            None.

        Returns:
            None.
        """

        self.embed = build_actions_embed(LoggingActions.all_actions(self.bits))
        await self.message.edit(embed=self.embed)

    async def finalize(self, timed_out) -> None:
        """
        A method that is called when the menu loop is closed.

        Parameters:
            timed_out (bool): Whether the menu completed due to timing out.

        Returns:
            None.
        """

        async with self.condition:
            self.condition.notify()

        if timed_out:
            await self.stop('Discarded Audit Actions Changes.')

    async def stop(self, message: str = 'Discarded Audit Actions Changes.') -> None:
        """
        A method that stops the menu's internal loop.

        Parameters:
            message (str): The message to send when stopping the menu.

        Returns:
            None.
        """

        await self.ctx.send(message)
        super().stop()


def build_actions_embed(actions: List[LoggingActions]) -> discord.Embed:
    """
    A method that generates an embed detailing with LoggingActions are currently enabled.

    Parameters:
        actions (List[LoggingActions]): A list of currently enabled logging actions.

    Returns:
        embed (discord.Embed): The generated embed.
    """

    embed = discord.Embed(title='Logging Actions', color=0x00bbff)
    for index, action in enumerate(LoggingActions.list()):
        embed.add_field(name=f'{index}: {action}', value='✅ Enabled' if action in actions else '❌ Disabled',
                        inline=False)
    embed.set_footer(text='Please report any issues to my owner!')

    return embed


def flip_action_bits(action: LoggingActions, bits: int) -> int:
    """
    A method to toggle (flip) a specific action for a given set of bits.

    Parameters:
        action (LoggingActions): The LoggingAction to flip the corresponding bit for.
        bits (int): The LoggingActions bits to modify.

    Returns:
        (int): The modified LoggingActions bits.
    """

    if LoggingActions.has_action(action, bits):
        return LoggingActions.remove_actions_from_bits([action], bits)
    else:
        return LoggingActions.add_actions_to_bits([action], bits)


async def log_to_channel(bot: commands.Bot, action: Enum, bits: int, channel: int, message: str) -> None:
    """
    A method for performing the various checks necessary to log an action for a guild.

    Parameters:
        bot (commands.Bot): The Discord bot.
        action (Enum): The action to be logged/checked for.
        bits (int): The permissions integer to check the action against.
        channel (int): The id of the logging channel.
        message (str): The message to log to the channel.

    Returns:
        None.
    """

    if LoggingActions.has_action(action, bits):
        if channel := bot.get_channel(channel):
            try:
                await channel.send(message)
            except discord.HTTPException:
                pass


def setup(bot):
    """
    A setup function that allows the cog to be treated as an extension.

    Parameters:
        bot (commands.Bot): The bot the cog should be added to.

    Returns:
        None.
    """

    bot.add_cog(Moderation(bot))
    print('Completed Setup for Cog: Moderation')
