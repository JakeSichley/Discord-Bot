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
from utils.database_utils import execute_query, retrieve_query
from utils.context import Context
from dreambot import DreamBot
from aiosqlite import Error as aiosqliteError
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Optional, List
from utils.utils import cleanup, valid_content
from utils.prompts import prompt_user_for_content
from utils.converters import StringConverter
import logging
import discord

ReservedTags = (
    'tag', 'create', 'add', 'get', 'fetch', 'edit', 'alias', 'random',
    'delete', 'del', 'remove', 'info', 'search', 'list',
    'r', 'g', 'a', 'e', 'i', 'f', 's', 'l', 'd'
)

TagName = StringConverter(
    mutator=lambda x: x.strip().lower(),
    constraint=lambda x: x and 3 <= len(x) <= 100 and x not in ReservedTags
)


# noinspection PyUnresolvedReferences
@dataclass
class Tag:
    """
    A dataclass that represents the internal structure of a Tag.

    Attributes:
        name (str): The name of the tag.
        content (str): The tag's content.
        guild_id (int): The guild this tag belongs to.
        owner_id (int): The user that created this tag.
        uses (int): The number of times this tag has been used.
        created (datetime): The time this tag was created.

    """

    name: str
    content: str
    guild_id: int
    owner_id: int
    uses: int
    created: datetime


class Tags(commands.Cog):
    """
    A Cogs class that contains tags commands for the bot.

    Attributes:
        bot (DreamBot): The Discord bot class.
    """

    def __init__(self, bot: DreamBot) -> None:
        """
        The constructor for the Tags class.

        Parameters:
           bot (DreamBot): The Discord bot.
        """

        self.bot = bot

    @commands.guild_only()
    @commands.group(name='tag', aliases=['tags'], invoke_without_command=True)
    async def tag(self, ctx: Context, *, tag_name: TagName = None) -> None:
        """
        Parent command that handles tag related commands.

        Parameters:
            ctx (Context): The invocation context.
            tag_name (str): Optionally, the name of the tag.

        Returns:
            None.
        """

        if ctx.invoked_subcommand is None and tag_name:
            await ctx.invoke(self.get_tag, tag_name=tag_name)
        elif ctx.invoked_subcommand is None:
            await ctx.send_help('tag')

    @tag.command(
        name='create', aliases=['add'], help='Tag names must be 3-100 characters long and cannot be a reserved tag.'
    )
    async def create_tag(self, ctx: Context, *, tag_name: TagName) -> None:
        """
        Attempts to create a tag with the specified name.

        Parameters:
            ctx (Context): The invocation context.
            tag_name (str): The name of the tag.

        Returns:
            None.
        """

        tag = await fetch_tag(self.bot.database, ctx.guild.id, tag_name)

        if tag:
            await ctx.send(f'Tag `{tag_name}` already exists.')
            return

        await ctx.message.reply(f'`{tag_name}` needs some content. What\'ll it be?', mention_author=False)

        prompts, content = await prompt_user_for_content(self.bot, ctx)
        await cleanup(prompts, ctx.channel)

        content = content.strip()

        if valid_content(content):
            try:
                await execute_query(
                    self.bot.database,
                    'INSERT INTO TAGS (NAME, CONTENT, GUILD_ID, OWNER_ID, USES, CREATED) VALUES (?, ?, ?, ?, ?, ?)',
                    (
                        tag_name, content, ctx.guild.id, ctx.author.id, 0,
                        int(datetime.now(tz=timezone.utc).timestamp())
                    )
                )
            except aiosqliteError:
                await ctx.send('Failed to create tag.')
            else:
                await ctx.send(f'Successfully created tag `{tag_name}`.')
        else:
            await ctx.send('Tag content cannot be empty - please restart the command.')

    @tag.command(name='edit', aliases=['e'])
    async def edit_tag(self, ctx: Context, *, tag_name: TagName) -> None:
        """
        Attempts to edit an existing tag.
        A user must either own the tag or have the ability to manage messages (guild-wide) to edit the tag.

        Parameters:
            ctx (Context): The invocation context.
            tag_name (str): The name of the tag.

        Returns:
            None.
        """

        tag = await fetch_tag(self.bot.database, ctx.guild.id, tag_name)

        if not tag:
            await ctx.send(f'Tag `{tag_name}` does not exists.')
            return

        if not (tag.owner_id == ctx.author.id or ctx.author.guild_permissions.manage_messages):
            await ctx.send('You either do not own this tag or cannot manage messages.')
            return

        await ctx.message.reply(f'What should the new content for `{tag_name}` be?', mention_author=False)

        prompts, content = await prompt_user_for_content(self.bot, ctx)
        await cleanup(prompts, ctx.channel)

        content = content.strip()

        if valid_content(content):
            try:
                await execute_query(
                    self.bot.database,
                    'UPDATE TAGS SET CONTENT=? WHERE NAME=? AND GUILD_ID=?',
                    (content, tag.name, tag.guild_id)
                )
            except aiosqliteError:
                await ctx.send('Failed to edit tag.')
            else:
                await ctx.send(f'Successfully updated tag `{tag_name}`.')
        else:
            await ctx.send('Tag content cannot be empty - please restart the command.')

    @tag.command(name='get', aliases=['fetch'])
    async def get_tag(self, ctx: Context, *, tag_name: TagName) -> None:
        """
        Attempts to fetch a tag with the specified name.

        Parameters:
            ctx (Context): The invocation context.
            tag_name (str): The name of the tag.

        Returns:
            None.
        """

        tag = await fetch_tag(self.bot.database, ctx.guild.id, tag_name)

        if tag:
            await ctx.send(tag.content)
            await increment_tag_count(self.bot.database, tag_name, ctx.guild.id)
            return

        potential_tags = await search_tags(self.bot.database, ctx.guild.id, tag_name)

        if potential_tags:
            formatted_results = '\n'.join(x.name for x in potential_tags)
            await ctx.send(f'Did you mean... \n{formatted_results}')
        else:
            await ctx.send(f'Tag `{tag_name}` does not exist.')

    @tag.command(name='search', aliases=['s'])
    async def search_tags(self, ctx: Context, *, tag_name: TagName) -> None:
        """
        Attempts to search for tags with the specified name.

        Parameters:
            ctx (Context): The invocation context.
            tag_name (str): The name of the tag.

        Returns:
            None.
        """

        potential_tags = await search_tags(self.bot.database, ctx.guild.id, tag_name)

        if potential_tags:
            formatted_results = '\n'.join(x.name for x in potential_tags)
            await ctx.send(f'Found the following tags... \n{formatted_results}')
        else:
            await ctx.send(f'No tags found with name `{tag_name}`.')

    @tag.command(name='info', aliases=['i'])
    async def tag_info(self, ctx: Context, *, tag_name: TagName) -> None:
        """
        Attempts to fetch information about a tag.

        Parameters:
            ctx (Context): The invocation context.
            tag_name (str): The name of the tag.

        Returns:
            None.
        """

        tag = await fetch_tag(self.bot.database, ctx.guild.id, tag_name)

        if tag:
            author = await commands.MemberConverter().convert(ctx, str(tag.owner_id))

            embed = discord.Embed(title='Tag Info', color=0x95fc98)
            embed.add_field(name='Name', value=tag.name)
            embed.add_field(name='Author', value=f'{author.mention if author else tag.owner_id}')
            embed.add_field(name='Uses', value=str(tag.uses))
            embed.add_field(name='Created', value=f'<t:{tag.created}:F>')
            embed.add_field(name='Content', value=tag.content, inline=False)
            embed.set_footer(text="Please report any issues to my owner!")

            await ctx.send(embed=embed)
        else:
            await ctx.send(f'Tag `{tag_name}` does not exist.')

    @tag.command(name='random', aliases=['r'])
    async def get_random_tag(self, ctx: Context) -> None:
        """
        Attempts to fetch a random tag. Does not increase usage count.

        Parameters:
            ctx (Context): The invocation context.

        Returns:
            None.
        """

        tag = await fetch_tag(self.bot.database, ctx.guild.id)

        if tag:
            await ctx.send(f'**Tag `{tag.name}`**\n{tag.content}', safe_send=True)
        else:
            await ctx.send(f'No tags exist for this guild.')

    @tag.command(name='delete', aliases=['remove', 'del'])
    async def delete_tag(self, ctx: Context, *, tag_name: TagName) -> None:
        """
        Attempts to delete a tag with the specified name.
        A user must either own the tag or have the ability to manage messages (guild-wide) to delete the tag.

        Parameters:
            ctx (Context): The invocation context.
            tag_name (str): The name of the tag.

        Returns:
            None.
        """

        tag = await fetch_tag(self.bot.database, ctx.guild.id, tag_name)

        if not tag:
            await ctx.send(f'Tag `{tag_name}` does not exist.')
            return

        if tag.owner_id == ctx.author.id or ctx.author.guild_permissions.manage_messages:
            try:
                await execute_query(
                    self.bot.database,
                    'DELETE FROM TAGS WHERE NAME=? AND GUILD_ID=?',
                    (tag_name, ctx.guild.id)
                )
            except aiosqliteError:
                await ctx.send(f'Failed to delete tag `{tag_name}`.')
            else:
                await ctx.send(f'Deleted tag `{tag_name}`.')
        else:
            await ctx.send('You either do not own this tag or cannot manage messages.')


async def fetch_tag(database: str, guild_id: int, tag_name: str = None) -> Optional[Tag]:
    """
    Attempts to fetch a tag from the database. If successful, attempts to convert raw tag data to a Tag.
        Note: Can fetch a random tag if tag_name is None.

    Parameters:
        database (str): The name of the database to fetch from.
        guild_id (int): The guild id.
        tag_name (str): The name of the tag.

    Returns:
        (Optional[Tag]).
    """

    if tag_name:
        query = 'SELECT * FROM TAGS WHERE NAME=? AND GUILD_ID=? LIMIT 1'
        params = (tag_name, guild_id)
    else:
        query = 'SELECT * FROM TAGS WHERE GUILD_ID=? ORDER BY RANDOM() LIMIT 1'
        params = (guild_id,)

    result = await retrieve_query(database, query, params)

    if not result:
        return None

    return Tag(*result[0])


async def search_tags(database: str, guild_id: int, tag_name: str) -> Optional[List[Tag]]:
    """
    Attempts to search for tags with the specified name.

    Parameters:
        database (str): The name of the database to fetch from.
        guild_id (int): The guild id.
        tag_name (str): The name of the tag.

    Returns:
        (Optional[List[Tag]]).
    """

    try:
        result = await retrieve_query(
            database,
            'SELECT * FROM TAGS WHERE NAME LIKE ? AND GUILD_ID=? LIMIT 5',
            (f'%{tag_name}%', guild_id)
        )
    except aiosqliteError:
        return None
    else:
        return [Tag(*x) for x in result]


async def increment_tag_count(database: str, tag_name: str, guild_id: int) -> None:
    """
    Attempts to increment the usage count of a tag.

    Parameters:
        database (str): The name of the database to fetch from.
        tag_name (str): The name of the tag.
        guild_id (int): The guild id.

    Returns:
        (Optional[Tag]).
    """

    try:
        await execute_query(
            database,
            'UPDATE TAGS SET USES=USES+1 WHERE NAME=? AND GUILD_ID=?',
            (tag_name, guild_id)
        )
    except aiosqliteError:
        pass


def setup(bot: DreamBot) -> None:
    """
    A setup function that allows the cog to be treated as an extension.

    Parameters:
        bot (DreamBot): The bot the cog should be added to.

    Returns:
        None.
    """

    bot.add_cog(Tags(bot))
    logging.info('Completed Setup for Cog: Tags')
