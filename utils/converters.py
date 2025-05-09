"""
MIT License

Copyright (c) 2019-Present Jake Sichley

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

import re
from typing import Optional, Union, Callable

import discord
import parsedatetime  # type: ignore[import-untyped]
from discord.ext import commands

from dreambot import DreamBot
from utils.context import Context

ForbiddenCharacterSet = set('_~#/\`><@*')


class ForbiddenCharacters(commands.BadArgument):
    def __init__(self) -> None:
        super().__init__(f'Input contained one or more Forbidden Characters: {", ".join(ForbiddenCharacterSet)}')


def check_for_forbidden_characters(string: str) -> None:
    """
    Checks if the provided string contains any of the forbidden characters.

    Parameters:
        string (str): The string to check for forbidden characters.

    Raises:
        ForbiddenCharacters: Whether the string contains any of the forbidden characters.

    Returns:
        None.
    """

    if set(string).intersection(ForbiddenCharacterSet):
        raise ForbiddenCharacters


class DefaultMemberConverter(commands.MemberConverter):
    """
    Converts an argument to a discord.Member object.

    All lookups are via the local guild. If in a DM context, then the lookup is done by the global cache.

    The lookup strategy is as follows (in order):

    1. Lookup by ID.
    2. Lookup by mention.
    3. Lookup by name#discriminator
    4. Lookup by name
    5. Lookup by nickname

    When processing a bulk-batch of members via a variadic method, this converter attempts to fix whitespace errors to
    help lookup via name#discriminator. If the member conversion still fails, this function returns the original
    parameter, rather than raising a MemberNotFound exception. This ensures the remaining members are still processed,
    rather than the command failing.
    """

    async def convert(self, ctx: Context, argument: str) -> Union[discord.Member, str]:  # type: ignore[override]
        """
        Attempts to convert the argument into a discord.Member object.

        Parameters:
            ctx (Context): The invocation context.
            argument (Any): The arg to be converted.

        Returns:
            (Union[discord.Member, str]): The resulting discord.Member. If conversion fails, returns the argument.
        """

        argument = re.sub(r'\s+#', '#', argument)

        try:
            return await super().convert(ctx, argument)
        except commands.MemberNotFound:
            return argument


class AggressiveDefaultMemberConverter(commands.IDConverter[Union[discord.Member, str]]):
    """
    Converts an argument to a discord.Member object.

    All lookups are via the local guild.

    The lookup strategy is as follows (in order):

    1. Lookup by ID.
    2. Lookup by mention.
    3. Lookup by name#discriminator
    4. Lookup by name
    5. Lookup by nickname

    When processing a bulk-batch of members via a variadic method, this converter attempts to aggressively match
    arguments, ignoring case when applicable. Unlike `DefaultMemberConverter`, this implementation assumes arguments
    have already been processed (such as extraneous whitespace stripping).
    If the member conversion still fails, this function returns the original
    parameter, rather than raising a MemberNotFound exception. This ensures the remaining members are still processed,
    rather than the command failing.

    This is nearly identical to the base implementation of commands.IDConverter, with more aggressive matching criteria.
    """

    @staticmethod
    def _guild_get_member_named(guild: discord.Guild, name: str) -> Optional[discord.Member]:
        """
        Returns the first member found that matches the name or (nickname) provided.

        Parameters:
            guild (discord.Guild): The guild to perform the query with.
            name (str): The (nick)name of the member.

        Returns:
            result (Optional[discord.Member]): The resulting member, if any.
        """

        members = guild.members
        if len(name) > 5 and name[-5] == '#':
            # The 5 length is checking to see if #0000 is in the string,
            # as a#0000 has a length of 6, the minimum for a potential
            # discriminator lookup.
            # do the actual lookup and return if found
            # if it isn't found then we'll do a full name lookup below.

            result = next((member for member in members if str(member).lower() == name.lower()), None)

            if result is not None:
                return result

        def pred(m: discord.Member) -> bool:
            """
            The predicate check to use while searching for the potential member.

            Parameters:
                m (discord.Member): The current argument to check the predicate against.

            Returns:
                (bool): Whether the current argument matches our criteria.
            """

            if m.nick:
                return m.nick.lower() == name.lower() or m.name.lower() == name.lower()
            else:
                return m.name.lower() == name.lower()

        return discord.utils.find(pred, members)

    @staticmethod
    async def _query_member_named(guild: discord.Guild, argument: str) -> Optional[discord.Member]:
        """
        Attempts to query a member based on their name (or nickname) from the current guild.

        Parameters:
            guild (discord.Guild): The guild to perform the query with.
            argument (str): The (nick)name of the member.

        Returns:
            result (Optional[discord.Member]): The resulting member, if any.
        """

        cache = guild._state.member_cache_flags.joined
        if len(argument) > 5 and argument[-5] == '#':
            username, _, discriminator = argument.rpartition('#')
            members = await guild.query_members(username, limit=100, cache=cache)
            return discord.utils.get(members, name=username, discriminator=discriminator)
        else:
            members = await guild.query_members(argument, limit=100, cache=cache)
            return discord.utils.find(lambda m: m.name == argument or m.nick == argument, members)

    @staticmethod
    async def _query_member_by_id(bot: DreamBot, guild: discord.Guild, user_id: int) -> Optional[discord.Member]:
        """
        Attempts to query a member based on their ID from the current guild.

        Parameters:
            bot (DreamBot): The Discord bot.
            guild (discord.Guild): The guild to perform the query with.
            user_id (int): The ID of the user.

        Returns:
            result (Optional[discord.Member]): The resulting member, if any.
        """

        ws = bot._get_websocket(shard_id=guild.shard_id)
        cache = guild._state.member_cache_flags.joined
        if ws.is_ratelimited():
            # If we're being rate limited on the WS, then fall back to using the HTTP API
            # So we don't have to wait ~60 seconds for the query to finish
            try:
                member = await guild.fetch_member(user_id)
            except discord.HTTPException:
                return None

            if cache:
                guild._add_member(member)
            return member

        # If we're not being rate limited then we can use the websocket to actually query
        members = await guild.query_members(limit=1, user_ids=[user_id], cache=cache)
        if not members:
            return None
        return members[0]

    async def convert(self, ctx: Context, argument: str) -> Union[discord.Member, str]:  # type: ignore[override]
        """
        Attempts to aggressively convert the argument into a discord.Member object.

        Parameters:
            ctx (Context): The invocation context.
            argument (Any): The arg to be converted.

        Returns:
            (Union[discord.Member, str]): The resulting discord.Member. If conversion fails, returns the argument.
        """

        bot = ctx.bot
        match = self._get_id_match(argument) or re.match(r'<@!?([0-9]+)>$', argument)  # type: ignore[no-untyped-call]
        guild = ctx.guild
        result: Optional[Union[discord.Member, discord.User]] = None
        user_id = None
        if match is None:
            if guild:
                result = self._guild_get_member_named(guild, argument)
        else:
            user_id = int(match.group(1))
            if guild:
                result = guild.get_member(user_id) or discord.utils.get(ctx.message.mentions, id=user_id)

        if result is None:
            if guild is None:
                return argument

            if user_id is not None:
                result = await self._query_member_by_id(bot, guild, user_id)
            else:
                result = await self._query_member_named(guild, argument)

            if not result:
                return argument

        return result if isinstance(result, discord.Member) else argument


class StringConverter(commands.Converter[str]):
    """
    Converts an argument to a string and applies the specified mutation.

    While this converter does little actual conversion, it is designed to help synchronize argument formats across
    groups or cogs when this behavior is desirable.
    """

    # TODO: Failure Support
    """
    Add parameter to allow human description of constraint where applicable
    Example:
        TagName = StringConverter(
            mutator=lambda x: x.strip().lower(),
            constraint=lambda x: x is not None and 2 <= len(x) <= 100 and x not in ReservedTags,
            description: Must be between 2 and 100 characters. Cannot be {Reserved Tag}. Cannot be {ForbiddenCharacters}
        )
    """

    def __init__(
            self,
            *,
            mutator: Optional[Callable[[str], str]] = None,
            constraint: Optional[Callable[[str], bool]] = None,
            allow_forbidden_characters: bool = False
    ) -> None:
        """
        The constructor for the StringConverter class.

        Parameters:
            mutator (Optional[Callable[[str], str]]): The mutation to apply during conversions.
            constraint (Optional[Callable[[str], bool]]): The constraint to apply to the converted argument.
            allow_forbidden_characters (bool): Whether `ForbiddenCharacterSet` elements are allowed in the argument.
        """

        self.mutator = mutator
        self.constraint = constraint
        self.allow_forbidden_characters = allow_forbidden_characters

    async def convert(self, ctx: Context, argument: str) -> str:  # type: ignore[override]
        """
        Attempts to convert the argument to a string. If successful, attempts to apply to specified mutator.

        Parameters:
            ctx (Context): The invocation context.
            argument (Any): The arg to be converted.

        Returns:
            (str): The mutated string.
        """

        try:
            result = self.mutator(str(argument)) if self.mutator else str(argument)

            if not self.allow_forbidden_characters:
                # raises `ForbiddenCharacter`
                check_for_forbidden_characters(result)

            if not self.constraint or (self.constraint is not None and self.constraint(result)):
                return result
            else:
                raise commands.BadArgument(f'{result} failed constraint.')

        except AttributeError:
            raise commands.BadArgument(f'Could not coerce {argument} to string.')
