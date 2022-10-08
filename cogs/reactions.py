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

from discord.ext import commands
from asyncio import TimeoutError
from utils.database_utils import execute_query, retrieve_query
from utils.converters import GuildConverter
from utils.prompts import prompt_user_for_role, prompt_user_for_discord_message
from utils.utils import cleanup
from utils.context import Context
from typing import Union, Optional, List, Tuple
from math import ceil
from dreambot import DreamBot
from utils.logging_formatter import bot_logger
import discord


class ReactionRoles(commands.Cog):
    """
    A Cogs class that implements reaction roles.

    Attributes:
        bot (DreamBot): The Discord bot.
    """

    def __init__(self, bot: DreamBot) -> None:
        """
        The constructor for the ReactionRoles class.

        Parameters:
            bot (DreamBot): The Discord bot.
        """

        self.bot = bot

    @commands.group(name='reactionrole', aliases=['rr', 'reactionroles'])
    async def reaction_role(self, ctx: Context) -> None:
        """
        Parent command that handles the reaction role commands.

        Parameters:
            ctx (Context): The invocation context.

        Returns:
            None.
        """

        if ctx.invoked_subcommand is None:
            await ctx.send_help('reactionrole')

    @commands.bot_has_permissions(manage_roles=True)
    @commands.has_permissions(manage_roles=True)
    @reaction_role.command(name='add', help='Begins the process of setting up a Reaction Role.\nYou can invoke this '
                                            'command without any arguments to go through the entire setup process.\n'
                                            'Alternatively, you can pass just a message ID, or both a message ID and a '
                                            'role name or role ID. If you choose to pass a role name, you need to quote'
                                            ' the role name in order for it to be properly parsed ("my role").\nYou can'
                                            ' also use this method to change the role of an existing reaction. Specify'
                                            ' the same message and reaction and simply supply a new role!')
    async def add_reaction_role(self, ctx: Context, message: discord.Message = None,
                                role: discord.Role = None) -> None:
        """
        Adds a reaction role to a specified message.

        Parameters:
            ctx (Context): The invocation context.
            message (discord.Message): The base message for the reaction role. Could be None.
            role: (discord.Role): The role to grant/remove when a user reacts. Could be None.

        Returns:
            None.
        """

        cleanup_messages = []

        # check these properties early to try to avoid wasting the user's time
        bot_role = ctx.me.top_role
        invoker_role = ctx.author.top_role

        if not all((bot_role, invoker_role)):
            await ctx.send("Couldn't retrieve top roles for myself or you. Please try the command again.")
            return

        if not message:
            initial_message = 'Please specify the message you want to set up Reaction Roles for!\nYou can right ' \
                              'click on a message and send either the Message ID or you can also send the entire ' \
                              'Message Link!'
            cleanup_messages, message = await prompt_user_for_discord_message(self.bot, ctx, initial_message)

            if not message:
                await cleanup(cleanup_messages, ctx.channel)
                return

        # check to make sure the message is from this guild (full message link check)
        if not message:
            await ctx.send('No Message')
            return

        if message.guild.id != ctx.guild.id:
            await ctx.send("That message doesn't belong to this guild.")
            return

        # reaction role setup should have the base message. Check role properties now.
        # if the user passed in a role at the start, check the hierarchy
        if role and (role >= bot_role or role >= invoker_role):
            cleanup_messages.append(await ctx.send("You specified a role equal to or higher than mine or your top role."
                                                   " Please select a role we both have permission to add!"))
            role = None

        if not role:
            initial_message = 'Please specify the role you want to set up Reaction Roles for!\nYou can send the Role ' \
                              'Name, Role ID, or even mention the Role!'

            messages, role = await prompt_user_for_role(self.bot, ctx, bot_role, invoker_role, initial_message)
            cleanup_messages.extend(messages)

            if not role:
                await cleanup(cleanup_messages, ctx.channel)
                return

        if role.guild.id != role.guild.id:
            await ctx.send("That role doesn't belong to this guild.")
            return

        # reaction role setup should have the base message and a role
        # if the user passed in a role at the start, check the hierarchy
        reaction_message = await ctx.send('Please specify the reaction you want to set up Reaction Roles for!'
                                          '\nYou can react to this message with the reaction!')
        cleanup_messages.append(reaction_message)

        def reaction_check(pl: discord.RawReactionActionEvent):
            """
            Our check criteria to wait for.

            Return a payload if:
                (1) The reaction was to the correct message,
                and (2) The reaction was added (not removed),
                and (3) The user adding the reaction is our original author

            Parameters:
                pl (discord.RawReactionActionEvent): The payload data to check requirements against.

            Returns:
                (bool): Whether the payload meets our check criteria.
            """

            return pl.message_id == reaction_message.id and pl.member == ctx.author and pl.event_type == 'REACTION_ADD'

        # wrap the entire operation in a try -> break this with timeout
        try:
            payload = await self.bot.wait_for('raw_reaction_add', timeout=30.0, check=reaction_check)
            # try to add the reaction the base message
            try:
                await message.add_reaction(payload.emoji)
            except discord.HTTPException as e:
                bot_logger.warning(f'Reaction Role Reaction Addition Error. {e.status}. {e.text}')
                cleanup_messages.append(await ctx.send("I wasn't able to add the reaction to the base message. If you"
                                                       " have not already done so, please add the reaction for me!"))
        except TimeoutError:
            await ctx.send("Didn't receive a response in time. You can restart the command whenever you're ready!")
            return await cleanup(cleanup_messages, ctx.channel)

        # we should have all pieces for a reaction role now
        await execute_query(self.bot.database,
                            'INSERT INTO REACTION_ROLES (GUILD_ID, CHANNEL_ID, MESSAGE_ID, REACTION, ROLE_ID) '
                            'VALUES (?, ?, ?, ?, ?) '
                            'ON CONFLICT(MESSAGE_ID, REACTION) DO UPDATE SET ROLE_ID=EXCLUDED.ROLE_ID',
                            (message.guild.id, message.channel.id, message.id, str(payload.emoji), role.id))
        await ctx.send(f"Awesome! Whenever a user reacts to the message {message.jump_url} with the reaction "
                       f"{payload.emoji}, I'll assign them the **{role.name}** role!")
        await cleanup(cleanup_messages, ctx.channel)

    @commands.bot_has_permissions(manage_roles=True)
    @commands.has_permissions(manage_roles=True)
    @reaction_role.command(name='remove', help='Begins the process of removing an existing Reaction Role.\nIf you '
                                               'invoke this command without a supplying a message, you will be '
                                               'prompted for one.\nIf you wish to change the role associated with a '
                                               'specific reaction, consider using "add" instead!\nIf you wish to '
                                               'remove all reaction roles from a message, consider using "clear" '
                                               'instead!')
    async def remove_reaction_role(self, ctx: Context, message: discord.Message = None) -> None:
        """
        Removes a reaction role from a specified message.

        Parameters:
            ctx (Context): The invocation context.
            message (discord.Message): The base message for the reaction role. Could be None.

        Returns:
            None.
        """

        cleanup_messages = []

        if not message:
            initial_message = 'Please specify the message you want to set up Reaction Roles for!\nYou can right ' \
                              'click on a message and send either the Message ID or you can also send the entire ' \
                              'Message Link!'
            cleanup_messages, message = await prompt_user_for_discord_message(self.bot, ctx, initial_message)

            if not message:
                await cleanup(cleanup_messages, ctx.channel)
                return

        # check to make sure the message is from this guild (full message link check)
        if message.guild.id != ctx.guild.id:
            await ctx.send("That message doesn't belong to this guild.")
            return

        # once we have a message id, proceed with deletion confirmation
        if roles := await retrieve_query(self.bot.database,
                                         'SELECT REACTION, ROLE_ID, CHANNEL_ID FROM REACTION_ROLES '
                                         'WHERE MESSAGE_ID=?', (message.id,)):
            # roles contain reactions, roles
            # build embed
            data = [(reaction, ctx.guild.get_role(role)) for reaction, role, _, in roles]
            reaction_role_pagination = ReactionRolePagination(ctx, data)

            await reaction_role_pagination.start(message)
            cleanup_messages.append(reaction_role_pagination.message)

            def reaction_check(pl: discord.RawReactionActionEvent):
                """
                Our check criteria to wait for.

                Return a payload if:
                    (1) The reaction was to the correct message,
                    and (2) The reaction was added (not removed),
                    and (3) The user adding the reaction is our original author
                    and (4) The added reaction is one of our active reactions

                Parameters:
                    pl (discord.RawReactionActionEvent): The payload data to check requirements against.

                Returns:
                    (bool): Whether the payload meets our check criteria.
                """

                return pl.message_id == reaction_role_pagination.message.id and \
                    pl.member == ctx.author and \
                    str(pl.emoji) in reaction_role_pagination.active_reactions

            while reaction_role_pagination.active:
                try:
                    payload = await self.bot.wait_for('raw_reaction_add', timeout=30.0, check=reaction_check)

                    if str(payload.emoji) == '\u23f9\ufe0f':
                        raise TimeoutError
                    elif str(payload.emoji) == '\u23ee\ufe0f':
                        await reaction_role_pagination.adjust_page(-1)
                    elif str(payload.emoji) == '\u23ed\ufe0f':
                        await reaction_role_pagination.adjust_page(1)
                    else:
                        index = ReactionRolePagination.EMOJI_TO_INT[str(payload.emoji)] - 1
                        to_remove = data[index]
                        reaction_role_pagination.active = False

                except (commands.BadArgument, TimeoutError):
                    reaction_role_pagination.active = False
                    await ctx.send('Aborting reaction role removal.')
                    await cleanup(cleanup_messages, ctx.channel)
                    return

            try:
                # noinspection PyUnboundLocalVariable
                confirmation = await ctx.send(f'Please confirm that you want to remove the role `{to_remove[1]}` '
                                              f'paired with the reaction `{to_remove[0]}` by reacting to this message.')
                cleanup_messages.append(confirmation)
                await confirmation.add_reaction('\u2705')
                await confirmation.add_reaction('\u274c')

                # noinspection PyMissingOrEmptyDocstring
                def reaction_check(pl: discord.RawReactionActionEvent):
                    return pl.message_id == confirmation.id and \
                           pl.member == ctx.author and \
                           str(pl.emoji) in ['\u2705', '\u274c']

                # confirm that the user wants to remove the reaction role
                payload = await self.bot.wait_for('raw_reaction_add', timeout=30.0, check=reaction_check)

                if str(payload.emoji) == '\u2705':
                    await execute_query(self.bot.database,
                                        'DELETE FROM REACTION_ROLES WHERE MESSAGE_ID=? AND REACTION=?',
                                        (message.id, str(to_remove[0])))
                    # try to remove the deleted reaction
                    try:
                        await message.clear_reaction(to_remove[0])
                    except discord.HTTPException as e:
                        bot_logger.warning(f'Reaction Role Reaction Removal Error. {e.status}. {e.text}')

                    await ctx.send('Removed the specified reaction role from the message.')
                else:
                    raise commands.BadArgument

            # if the user reacts with the wrong reaction doesn't react at all, cancel the command
            except (commands.BadArgument, TimeoutError):
                await ctx.send('Aborting reaction role removal.')
        else:
            await ctx.send('Could not find any reaction roles associated with the specified message.')

        await cleanup(cleanup_messages, ctx.channel)

    @commands.bot_has_permissions(manage_roles=True)
    @commands.has_permissions(manage_roles=True)
    @reaction_role.command(name='clear', help='Begins the process of clearing all existing Reaction Roles.\nIf you'
                                              ' invoke this command without a supplying a message, you will be prompted'
                                              ' for one.\nIf you wish to remove only a single reaction role, consider'
                                              ' using "remove" instead!')
    async def clear_reaction_roles(self, ctx: Context, message: discord.Message = None) -> None:
        """
        Clears all reaction roles from a specified message.

        Parameters:
            ctx (Context): The invocation context.
            message (discord.Message): The base message for the reaction role. Could be None.

        Returns:
            None.
        """

        cleanup_messages = []

        if not message:
            initial_message = 'Please specify the message you want to set up Reaction Roles for!\nYou can right ' \
                              'click on a message and send either the Message ID or you can also send the entire ' \
                              'Message Link!'
            cleanup_messages, message = await prompt_user_for_discord_message(self.bot, ctx, initial_message)

            if not message:
                await cleanup(cleanup_messages, ctx.channel)
                return

        # check to make sure the message is from this guild (full message link check)
        if message.guild.id != ctx.guild.id:
            await ctx.send("That message doesn't belong to this guild.")
            return

        # once we have a message id, proceed with deletion confirmation
        if roles := await retrieve_query(self.bot.database,
                                         'SELECT REACTION, ROLE_ID, CHANNEL_ID FROM REACTION_ROLES '
                                         'WHERE MESSAGE_ID=?', (message.id,)):
            response = await ctx.send(f'Are you sure want to remove **{len(roles)}** reaction roles from '
                                      f'<https://discordapp.com/channels/{ctx.guild.id}/{roles[0][2]}/{message.id}>? '
                                      f'This cannot be undone. If you wish to proceed, react to this message with ✅.')
            cleanup_messages.append(response)

            # make sure the reaction is added to the correct message and the reaction is added by our author
            # noinspection PyMissingOrEmptyDocstring
            def reaction_check(pl: discord.RawReactionActionEvent):
                if pl.event_type == 'REACTION_REMOVE':
                    return
                return pl.message_id == response.id and pl.member == ctx.author

            try:
                # confirm that the user wants to remove all the reaction roles from the specified message
                await response.add_reaction('✅')
                # wait for the user to respond with the checkmark
                payload = await self.bot.wait_for('raw_reaction_add', timeout=30.0, check=reaction_check)

                if str(payload.emoji) == '✅':
                    await execute_query(
                        self.bot.database,
                        'DELETE FROM REACTION_ROLES WHERE MESSAGE_ID=?',
                        (message.id,)
                    )
                    # try to remove the respective reactions
                    for reaction in message.reactions:
                        if reaction.me:
                            try:
                                await message.remove_reaction(reaction, ctx.me)
                            except discord.HTTPException as e:
                                bot_logger.warning(f'Reaction Role Reaction Clear Error. {e.status}. {e.text}')
                    await ctx.send('Removed all reaction roles from the specified message.')
                else:
                    raise commands.BadArgument

            # if the user reacts with the wrong reaction or doesn't react at all, cancel the command
            except (commands.BadArgument, TimeoutError):
                await ctx.send('Aborting reaction role removal.')
        else:
            await ctx.send('Could not find any reaction roles associated with the specified message.')

        await cleanup(cleanup_messages, ctx.channel)

    @commands.has_permissions(manage_roles=True)
    @reaction_role.command(name='check', help='Generates a breakdown of reaction roles for the given scope. Valid '
                                              'scopes: Guild, Channel, Message.')
    async def check_reaction_roles(
            self, ctx: Context, source: Union[GuildConverter, discord.TextChannel, discord.Message]
    ) -> None:
        """
        Generates a breakdown of reaction roles for the given scope. Valid scopes: Guild, Channel, Message.
        This method defines sub-methods that generate a breakdown for their given scopes.
        Scopes higher in the hierarchy (Guild > Channel > Message) recursively call lower scopes until the entire
            specified scope has been filled out.

        Parameters:
            ctx (Context): The invocation context.
            source (Union[discord.Guild, discord.TextChannel, discord.Message]):
                The scope for which a reaction role breakdown should be generated.

        Returns:
            None.
        """

        async def message_selection(message_id: int, indent_level: int = 0) -> Optional[str]:
            """
            Generates a breakdown of reaction roles for a specified message.

            Parameters:
                message_id (int): The ID of the message to generate a breakdown for.
                indent_level (int): The amount of whitespace to pad this breakdown with. Default: 0.

            Returns:
                details (Optional[str]): Details about the reaction roles of the message if possible. Could be None.
            """

            if roles := await retrieve_query(self.bot.database,
                                             'SELECT REACTION, ROLE_ID, CHANNEL_ID FROM REACTION_ROLES '
                                             'WHERE MESSAGE_ID=?', (message_id,)):
                details = ('\t' * indent_level) + f'Reaction Roles for **Message:** <https://discordapp.com/channels/' \
                                                  f'{ctx.guild.id}/{roles[0][2]}/{message_id}>\n'

                for pair in roles:
                    role_name = ctx.guild.get_role(pair[1])
                    details += ('\t' * (indent_level + 2)) + f'{pair[0]} {role_name if role_name else "Invalid Role"}\n'

                return details
            else:
                return None

        async def channel_selection(channel_id: int, indent_level: int = 0) -> Optional[str]:
            """
            Generates a breakdown of reaction roles for a specified channel.

            Parameters:
                channel_id (int): The ID of the channel to generate a breakdown for.
                indent_level (int): The amount of whitespace to pad this breakdown with. Default: 0.

            Returns:
                details (Optional[str]): Details about the reaction roles of the channel if possible. Could be None.
            """

            if messages := await retrieve_query(self.bot.database,
                                                'SELECT DISTINCT MESSAGE_ID FROM REACTION_ROLES WHERE CHANNEL_ID=?',
                                                (channel_id,)):
                details = ('\t' * indent_level) + f'Reaction Roles for **Channel:** <#{channel_id}>\n'

                for message in messages:
                    message_details = await message_selection(message[0], indent_level + 1)
                    details += ('\t' * indent_level) + message_details + '\n' if message_details is not None else 'None'

                return details
            else:
                return None

        async def guild_selection(guild_id: int) -> Optional[str]:
            """
            Generates a breakdown of reaction roles for a specified guild.

            Parameters:
                guild_id (int): The ID of the guild to generate a breakdown for.

            Returns:
                details (Optional[str]): Details about the reaction roles of the guild if possible. Could be None.
            """

            if channels := await retrieve_query(self.bot.database,
                                                'SELECT DISTINCT CHANNEL_ID FROM REACTION_ROLES WHERE GUILD_ID=?',
                                                (guild_id,)):
                details = f'Reaction Roles for **Guild: {ctx.guild.name}**\n'

                for channel in channels:
                    channel_details = await channel_selection(channel[0], 1)
                    details += channel_details if channel_details is not None else 'None'

                return details
            else:
                return None

        source_id = source.guild.id if isinstance(source, (discord.TextChannel, discord.Message)) else source.id
        if source_id != ctx.guild.id:
            await ctx.send("That object doesn't belong to this guild.")
            return

        # invoke the proper sub-method based on our source type
        if isinstance(source, discord.Message):
            # check to make sure the message is from this guild (full message link check)
            breakdown = await message_selection(source.id)
            await ctx.send(breakdown) if breakdown else await ctx.send('No Reaction Roles for the specified message.')
        elif isinstance(source, discord.TextChannel):
            breakdown = await channel_selection(source.id)
            await ctx.send(breakdown) if breakdown else await ctx.send('No Reaction Roles for the specified channel.')
        elif isinstance(source, discord.Guild):
            breakdown = await guild_selection(source.id)
            await ctx.send(breakdown) if breakdown else await ctx.send('No Reaction Roles for the specified guild.')
        else:
            await ctx.send("Invalid object was passed - couldn't fetch reaction roles.\n"
                           "```Messages: If the message is in the channel, you can pass the Message ID. If the message "
                           "is in another channel, you can pass the Channel-Message ID (shift-click on 'Copy ID'). "
                           "Otherwise, passing the entire message link works.\n"
                           "Channels: You can pass the Channel ID, Channel Name, or mention the channel.\n"
                           "Guilds: You can pass the Guild ID or Guild Name.```")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        """
        A listener method that is called whenever a reaction is added.
        'raw' events fire regardless of whether a message is cached.

        Parameters:
            payload (discord.RawReactionActionEvent): Represents a payload for a raw reaction event.

        Output:
            None.

        Returns:
            None.
        """

        if payload.user_id == self.bot.user.id:
            return

        if role_id := await retrieve_query(self.bot.database,
                                           'SELECT ROLE_ID FROM REACTION_ROLES WHERE MESSAGE_ID=? AND REACTION=?',
                                           (payload.message_id, str(payload.emoji))):
            # if there's a role for the given message + reaction, attempt to fetch the guild
            if guild := self.bot.get_guild(payload.guild_id):
                # if we fetched the guild, try to fetch the member and the role
                role = guild.get_role(role_id[0][0])
                member = guild.get_member(payload.user_id)
                # if we fetched all our prerequisites, attempt to add the role to the member
                if role and member:
                    try:
                        await member.add_roles(
                            role, reason=f'Reaction Roles - Add [Message ID: {payload.message_id}]'
                        )
                    except discord.HTTPException as e:
                        bot_logger.error(f'Reaction Role - Role Addition Failure. {e.status}. {e.text}')

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent) -> None:
        """
        A listener method that is called whenever a reaction is removed.
        'raw' events fire regardless of whether a message is cached.

        Parameters:
            payload (discord.RawReactionActionEvent): Represents a payload for a raw reaction event.

        Returns:
            None.
        """

        if payload.user_id == self.bot.user.id:
            return

        if role_id := await retrieve_query(self.bot.database,
                                           'SELECT ROLE_ID FROM REACTION_ROLES WHERE MESSAGE_ID=? AND REACTION=?',
                                           (payload.message_id, str(payload.emoji))):
            # if there's a role for the given message + reaction, attempt to fetch the guild
            if guild := self.bot.get_guild(payload.guild_id):
                # if we fetched the guild, try to fetch the member and the role
                role = guild.get_role(role_id[0][0])
                member = guild.get_member(payload.user_id)
                # if we fetched all our prerequisites, attempt to remove the role from the member
                if role and member:
                    try:
                        await member.remove_roles(
                            role, reason=f'Reaction Roles - Remove [Message ID: {payload.message_id}]'
                        )
                    except discord.HTTPException as e:
                        bot_logger.error(f'Reaction Role - Role Removal Error. {e.status}. {e.text}')


class ReactionRolePagination:
    """
    A class to handle the pagination of ReactionRole data during removal.

    Constants:
        PAGE_SIZE (int): The number of entries to display per page.
        EMOJI_TO_INT (dict): Pairs numbered key-cap emojis to their respective integers.

    Attributes:
        ctx (Context): The invocation context.
        data (List[Tuple[str, discord.Role]]): The reaction (str) and Role data for the requested source.
        message (discord.Message): The message containing the reaction role pagination embed.
        page (int): The current page.
        max_pages (int): The maximum number of pages.
        active_reactions (List[str]): A list of valid reactions based on the current page.
        active (bool): Whether pagination has started and is active.
    """

    PAGE_SIZE = 6
    EMOJI_TO_INT = {
        u'1\ufe0f\u20e3': 1,
        u'2\ufe0f\u20e3': 2,
        u'3\ufe0f\u20e3': 3,
        u'4\ufe0f\u20e3': 4,
        u'5\ufe0f\u20e3': 5,
        u'6\ufe0f\u20e3': 6
    }

    def __init__(self, ctx: Context, data: List[Tuple[str, discord.Role]]) -> None:
        """
        The constructor for the ReactionRolePagination class.

        Parameters:
            ctx (Context): The invocation context.
            data (List[Tuple[str, discord.Role]]): The reaction (str) and Role data for the requested source.

        Returns:
            None.
        """

        self.ctx = ctx
        self.data = data
        self.message = None
        self.embed = None
        self.page = 0
        self.max_pages = ceil(len(data) / ReactionRolePagination.PAGE_SIZE) - 1
        self.active_reactions = None
        self.active = False

    async def start(self, message: discord.Message) -> None:
        """
        Starts the ReactionRolePagination modal.

        Parameters:
            message (discord.Message): The specified source message.

        Returns:
            None.
        """

        embed = discord.Embed(title=f'\U0001f6e0\ufe0f Reaction Roles for Message ID: {message.id} \U0001f6e0\ufe0f',
                              url=message.jump_url, color=0x69d7f2,
                              description="React with the corresponding reaction to remove a reaction role.")
        embed.set_footer(text='Please report any issues to my owner!')
        self.embed = embed
        await self._paginate()

    async def adjust_page(self, offset: int) -> None:
        """
        Increments or decrements the current page of the modal.

        Parameters:
            offset (int): Value and direction to offset the current page by.

        Returns:
            None.
        """

        starting_page = self.page

        self.page += offset

        if self.page < 0:
            self.page = self.max_pages

        if self.page > self.max_pages:
            self.page = 0

        if self.page != starting_page:
            await self._paginate()

    async def _paginate(self) -> None:
        """
        Updates the modal with data for the current page.

        Parameters:
            None.

        Returns:
            None.
        """

        self.embed.clear_fields()
        start = self.page * ReactionRolePagination.PAGE_SIZE
        end = start + ReactionRolePagination.PAGE_SIZE

        for i, data in enumerate(self.data[start:end]):
            self.embed.add_field(name=f'{i + 1}\ufe0f\u20e3 {data[1].name if data[1] else "N/A"}', value=data[0],
                                 inline=False)

        await self.refresh_embed()

    async def refresh_embed(self) -> None:
        """
        Updates (or sends, if necessary) the embed modal.

        Parameters:
            None.

        Returns:
            None.
        """

        if not self.message:
            self.message = await self.ctx.send(embed=self.embed)
        else:
            await self.message.edit(embed=self.embed)

        self.active = True

        await self._update_reactions()

    async def _update_reactions(self) -> None:
        """
        Updates the active and available response reactions for the current page.

        Parameters:
            None.

        Returns:
            None.
        """

        currently_active_reactions = self.active_reactions
        digit_reactions = [f'{i + 1}\ufe0f\u20e3' for i in range(len(self.embed.fields))]
        self.active_reactions = ['\u23ee\ufe0f'] + digit_reactions + ['\u23f9\ufe0f', '\u23ed\ufe0f']

        if currently_active_reactions != self.active_reactions:
            await self.message.clear_reactions()

            for reaction in self.active_reactions:
                await self.message.add_reaction(reaction)


async def setup(bot: DreamBot) -> None:
    """
    A setup function that allows the cog to be treated as an extension.

    Parameters:
        bot (DreamBot): The bot the cog should be added to.

    Returns:
        None.
    """

    await bot.add_cog(ReactionRoles(bot))
    bot_logger.info('Completed Setup for Cog: Reactions')
