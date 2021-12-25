"""
MIT License

Copyright (c) 2021 Jake Sichley

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

from typing import Optional, Union, Any
from discord.ext import commands
import discord
import re


class GuildConverter(commands.IDConverter):
    """
    Converts an argument to a discord.Guild object.

    All lookups are via the local guild.

    The lookup strategy is as follows (in order):

    1. Lookup by ID.
    2. Lookup by name
    """

    async def convert(self, ctx, argument) -> Optional[discord.Guild]:
        """
        Attempts to convert the argument into a discord.Guild object.

        Parameters:
            ctx (commands.Context): The invocation context.
            argument (str): The arg to be converted.

        Returns:
            result (discord.Guild): The resulting discord.Guild. Could be None if conversion failed without exceptions.
        """

        match = self._get_id_match(argument)
        result = None
        guild = ctx.guild

        if match is None:
            if argument.casefold() == guild.name.casefold():
                result = ctx.guild
        else:
            guild_id = int(match.group(1))
            if guild and guild.id == guild_id:
                result = ctx.guild

        if not isinstance(result, discord.Guild):
            raise commands.BadArgument('Guild "{}" not found.'.format(argument))

        return result


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

    async def convert(self, ctx: commands.Context, argument: Any) -> Union[discord.Member, str]:
        """
        Attempts to convert the argument into a discord.Member object.

        Parameters:
            ctx (commands.Context): The invocation context.
            argument (str): The arg to be converted.

        Returns:
            (Union[discord.Member, str]): The resulting discord.Member. If conversion fails, returns the argument.
        """

        argument = re.sub(r'\s+#', '#', argument)

        try:
            return await super().convert(ctx, argument)
        except commands.MemberNotFound:
            return argument
