"""
MIT License

Copyright (c) 2019-2022 Jake Sichley

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from asyncio import Condition
from dataclasses import dataclass
from enum import Enum
from typing import List

import discord
from aiosqlite import Error as aiosqliteError
from discord.ext import commands, menus

from dreambot import DreamBot
from utils.context import Context
from utils.database.helpers import execute_query, typed_retrieve_query, DatabaseDataclass
from utils.logging_formatter import bot_logger


@dataclass
class PartialLoggingAction(DatabaseDataclass):
    """
    A DatabaseDataclass that stores the logging channel_id and bits for a guild.

    Attributes:
        channel_id (int): The logging channel id for the guild.
        bits (int): The logging bits for the guild.
    """

    channel_id: int
    bits: int


class Audit(commands.Cog):
    """
    A Cogs class that contains commands and functionality for auditing actions taken in a guild.

    Attributes:
        bot (DreamBot): The Discord bot class.
    """

    def __init__(self, bot: DreamBot) -> None:
        """
        The constructor for the Audit class.

        Parameters:
            bot (DreamBot): The Discord bot.
        """

        self.bot = bot

    async def cog_check(self, ctx: Context) -> bool:  # type: ignore[override]
        """
        A method that registers a cog-wide check.
        Requires these commands be used in a guild only.

        Parameters:
            ctx (Context): The invocation context.

        Returns:
            (bool): Whether the command was invoked in a guild.
        """

        return ctx.guild is not None

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        """
        A commands.Cog listener event that is called whenever a new user joins a guild.

        Functionality:
            If logging is enabled, logs the new member joining to the specified channel.

        Parameters:
            member (discord.Member): The member that joined the guild.

        Returns:
            None.
        """

        # retrieve logging information
        if logging_info := (await typed_retrieve_query(
                self.bot.connection,
                PartialLoggingAction,
                'SELECT CHANNEL_ID, BITS FROM LOGGING WHERE GUILD_ID=?',
                (member.guild.id,))
        ):
            await log_to_channel(
                self.bot,
                LoggingActions.USER_JOINED,
                logging_info[0].bits,
                logging_info[0].channel_id,
                f'**{str(member)}** joined the guild.'
            )

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
        if logging_info := (await typed_retrieve_query(
                self.bot.connection,
                PartialLoggingAction,
                'SELECT CHANNEL_ID, BITS FROM LOGGING WHERE GUILD_ID=?',
                (member.guild.id,))
        ):
            await log_to_channel(
                self.bot,
                LoggingActions.USER_LEFT,
                logging_info[0].bits,
                logging_info[0].channel_id,
                f'**{str(member)}** left the guild.'
            )

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
        if logging_info := (await typed_retrieve_query(
                self.bot.connection,
                PartialLoggingAction,
                'SELECT CHANNEL_ID, BITS FROM LOGGING WHERE GUILD_ID=?',
                (guild.id,))
        ):
            await log_to_channel(
                self.bot,
                LoggingActions.USER_BANNED,
                logging_info[0].bits,
                logging_info[0].channel_id,
                f'**{str(member)}** was banned from the guild.'
            )

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
        if logging_info := (await typed_retrieve_query(
                self.bot.connection,
                PartialLoggingAction,
                'SELECT CHANNEL_ID, BITS FROM LOGGING WHERE GUILD_ID=?',
                (guild.id,))
        ):
            await log_to_channel(
                self.bot,
                LoggingActions.USER_UNBANNED,
                logging_info[0].bits,
                logging_info[0].channel_id,
                f'**{str(member)}** was unbanned from the guild.'
            )

    @commands.group(name='auditaction', aliases=['aa', 'auditactions'])
    async def audit_actions(self, ctx: Context) -> None:
        """
        Parent command that handles the audit actions commands.

        Parameters:
            ctx (Context): The invocation context.

        Returns:
            None.
        """

        if ctx.invoked_subcommand is None:
            await ctx.send_help('auditaction')

    @commands.has_guild_permissions(manage_guild=True, view_audit_log=True)  # type: ignore[arg-type]
    @audit_actions.command(name='viewactions', aliases=['va'],
                           help='Generates an embed detailing the currently enabled and disabled logging actions for'
                                'this guild.')
    async def view_audit_actions(self, ctx: Context) -> None:
        """
        A method to view the currently enabled audit (logging) actions (if any) for the guild.

        Parameters:
            ctx (Context): The invocation context.

        Returns:
            None.
        """

        assert ctx.guild is not None  # handle by `cog_check`

        if logging_info := (await typed_retrieve_query(
                self.bot.connection,
                int,
                'SELECT BITS FROM LOGGING WHERE GUILD_ID=?',
                (ctx.guild.id,))
        ):
            await ctx.send(embed=build_actions_embed(LoggingActions.all_enabled_actions((logging_info[0]))))
        else:
            await ctx.send('You must first set an audit channel before viewing audit actions.'
                           '\n_See `auditactions setchannel` for more information._')

    @commands.max_concurrency(1, commands.BucketType.guild)  # type: ignore[arg-type]
    @commands.has_guild_permissions(manage_guild=True, view_audit_log=True)
    @audit_actions.command(name='changeactions', aliases=['ca'],
                           help='Sets the enabled (or disabled) actions you want logged for this guild. To enable or '
                                'disable an action, react with the corresponding reaction. Once you are satisfied '
                                'with the current settings, you can submit them.\nNote: If the cancel reaction is '
                                'selected, changes will be discarded. Changes are also discarded after 5 minutes of '
                                'inactivity.')
    async def change_audit_actions(self, ctx: Context) -> None:
        """
        A method to change the audit (logging) actions for the guild.
        This is implemented via a discord.ext.menus interface.
            For a more detailed description of how the menu works, see the ActionBitMenu class.

        Parameters:
            ctx (Context): The invocation context.

        Returns:
            None.
        """

        assert ctx.guild is not None  # handle by `cog_check`

        if logging_info := (await typed_retrieve_query(
                self.bot.connection,
                PartialLoggingAction,
                'SELECT CHANNEL_ID, BITS FROM LOGGING WHERE GUILD_ID=?',
                (ctx.guild.id,))
        ):
            # create an asyncio.Condition to allow for concurrency checking
            condition = Condition()

            # start the menu
            menu = ActionBitMenu(
                LoggingActions.all_enabled_actions(logging_info[0].bits), logging_info[0].bits, condition
            )
            await menu.start(ctx)

            # while the menu is active, this method is active
            # the condition notifies on menu termination (either via success, cancellation, or timeout)
            async with condition:
                await condition.wait()
        else:
            await ctx.send('You must first set an audit channel before changing audit actions.'
                           '\n_See `auditactions setchannel` for more information._')

    @commands.has_guild_permissions(manage_guild=True, view_audit_log=True)  # type: ignore[arg-type]
    @audit_actions.command(name='setchannel', aliases=['sc'],
                           help='Sets the Audit Log channel for this guild. Once set, any enabled Logging Actions will '
                                'be sent to this channel.\n\nNote: attempts to search for the specified channel by: '
                                '(1) ID, (2) mention, (3) name.')
    async def set_audit_channel(self, ctx: Context, channel: discord.TextChannel) -> None:
        """
        A method to set (or change) the logging channel for the guild.

        Parameters:
            ctx (Context): The invocation context.
            channel (discord.TextChannel): The new logging channel for the guild.

        Returns:
            None.
        """

        assert ctx.guild is not None  # handle by `cog_check`

        try:
            await execute_query(
                self.bot.connection,
                'INSERT INTO LOGGING (GUILD_ID, CHANNEL_ID, BITS) VALUES (?, ?, ?) '
                'ON CONFLICT(GUILD_ID) DO UPDATE SET CHANNEL_ID=EXCLUDED.CHANNEL_ID',
                (ctx.guild.id, channel.id, 0)
            )
            await ctx.send(f'Updated the logging channel to {channel.mention}.')

        except aiosqliteError:
            await ctx.send('Failed to update the logging channel.')


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

    @staticmethod
    def all_action_names() -> List[str]:
        """
        A class method for returning a list of all LoggingAction names.

        Parameters:
            None.

        Returns:
            (List[str]): A list of the names of the LoggingActions.
        """

        return list(map(lambda c: c.name, LoggingActions))

    @staticmethod
    def has_action(action: 'LoggingActions', action_bits: int) -> bool:
        """
        A class method for checking whether an action flag is enabled.

        Parameters:
            action (Enum): The action to check for.
            action_bits (int): The integer containing the action bits.

        Returns:
            (bool): Whether the action flag is enabled.
        """

        return bool(action.value & action_bits)

    @staticmethod
    def all_enabled_actions(action_bits: int) -> List['LoggingActions']:
        """
        A class method for parsing action bits, returning all enabled actions.

        Parameters:
            action_bits (int): The integer containing the action bits.

        Returns:
            ([Enum]): All logging actions that are enabled.
        """

        return [action for action in LoggingActions if action.value & action_bits]

    @staticmethod
    def add_actions_to_bits(actions: List['LoggingActions'], action_bits: int = 0) -> int:
        """
         A class method for constructing the action bits for the specified actions.

        Parameters:
            actions ([Enum]): The actions to enable.
            action_bits (int): The existing action bits to add further actions to. Default: 0.

        Returns:
            action_bits (int): The integer containing the updated action bits.
        """

        for action in actions:
            action_bits |= action.value

        return action_bits

    @staticmethod
    def remove_actions_from_bits(actions: List['LoggingActions'], action_bits: int) -> int:
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
                action_bits -= action.value

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

    async def send_initial_message(self, ctx: Context, channel: discord.TextChannel) -> discord.Message:
        """
        Sends the initial menu message.

        Parameters:
            ctx (Context): The context to send the initial message with.
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

        await execute_query(self.bot.connection, 'UPDATE LOGGING SET BITS=? WHERE GUILD_ID=?',
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

        await self.stop()

    async def update_embed(self) -> None:
        """
        Updates the menu's embed to reflect any pending changes to the AuditActions.

        Parameters:
            None.

        Returns:
            None.
        """

        self.embed = build_actions_embed(LoggingActions.all_enabled_actions(self.bits))
        await self.message.edit(embed=self.embed)

    async def finalize(self, timed_out: bool) -> None:
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
            await self.stop()

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
    for index, action in enumerate(LoggingActions.all_action_names()):
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


async def log_to_channel(bot: commands.Bot, action: LoggingActions, bits: int, channel_id: int, message: str) -> None:
    """
    A method for performing the various checks necessary to log an action for a guild.

    Parameters:
        bot (commands.Bot): The Discord bot.
        action (Enum): The action to be logged/checked for.
        bits (int): The permissions integer to check the action against.
        channel_id (int): The id of the logging channel.
        message (str): The message to log to the channel.

    Returns:
        None.
    """

    if LoggingActions.has_action(action, bits):
        if channel := bot.get_channel(channel_id):
            if not isinstance(channel, discord.abc.Messageable):
                return

            try:
                await channel.send(message)
            except discord.HTTPException:
                pass


async def setup(bot: DreamBot) -> None:
    """
    A setup function that allows the cog to be treated as an extension.

    Parameters:
        bot (DreamBot): The bot the cog should be added to.

    Returns:
        None.
    """

    await bot.add_cog(Audit(bot))
    bot_logger.info('Completed Setup for Cog: Audit')
