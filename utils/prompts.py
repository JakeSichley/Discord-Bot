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

from asyncio import TimeoutError
from typing import List, Tuple, Optional

import discord
from discord.ext import commands

from dreambot import DreamBot
from utils.context import Context


async def prompt_user_for_voice_channel(
        bot: DreamBot, ctx: Context, initial_prompt: Optional[str] = None
) -> Tuple[List[discord.Message], Optional[discord.VoiceChannel]]:
    """
    A method to fetch a discord.VoiceChannel from a user.

    Parameters:
        bot (DreamBot): The discord bot.
        ctx (Context): The invocation context.
        initial_prompt (Optional[str]): The initial message to send during the prompt.

    Output:
        Command State Information.

    Returns:
        Tuple[List[discord.Message], Optional[discord.VoiceChannel]]
    """

    sent_messages = [await ctx.send(initial_prompt)] if initial_prompt else []

    # wrap the entire operation in a try -> break this with timeout
    try:
        # give the user multiple attempts to pass a valid argument
        while True:
            # wait for them to respond
            response = await bot.wait_for(
                'message', timeout=30.0, check=lambda m: m.author == ctx.author and m.channel == ctx.channel
            )
            # try to convert their response to a VoiceChannel object
            try:
                channel = await commands.VoiceChannelConverter().convert(ctx, response.content)
                return sent_messages, channel
            except (commands.CommandError, commands.BadArgument):
                sent_messages.append(
                    await ctx.send("I wasn't able to extract a channel from your response. Please try again!")
                )
    except TimeoutError:
        await ctx.send("Didn't receive a response in time. You can restart the command whenever you're ready!")
        return sent_messages, None


async def prompt_user_for_role(
        bot: DreamBot, ctx: Context, bot_role: discord.Role, author_role: discord.Role,
        initial_prompt: Optional[str] = None
) -> Tuple[List[discord.Message], Optional[discord.Role]]:
    """
    A method to fetch a discord.Role from a user.

    Parameters:
        bot (DreamBot): The discord bot.
        ctx (Context): The invocation context.
        bot_role (commands.Role): The bot's role in the invocation server.
        author_role (commands.Role): The author's role in the invocation server.
        initial_prompt (Optional[str]): The initial message to send during the prompt.

    Output:
        Command State Information.

    Returns:
        Tuple[List[discord.Message], Optional[discord.Role]].
    """

    sent_messages = [await ctx.send(initial_prompt)] if initial_prompt else []

    # wrap the entire operation in a try -> break this with timeout
    try:
        # give the user multiple attempts to pass a valid argument
        while True:
            # wait for them to respond
            response = await bot.wait_for(
                'message', timeout=30.0, check=lambda m: m.author == ctx.author and m.channel == ctx.channel
            )
            # try to convert their response to a role object
            try:
                role = await commands.RoleConverter().convert(ctx, response.content)
                if role >= bot_role or role >= author_role or role.is_default():
                    raise commands.UserInputError
                else:
                    return sent_messages, role
            except commands.BadArgument:
                sent_messages.append(
                    await ctx.send("I wasn't able to extract a role from your response. Please try again!")
                )
            except commands.UserInputError:
                sent_messages.append(
                    await ctx.send("You cannot specify a role higher than or equal to mine or your top role! "
                                   "Please specify another role!")
                )
            except commands.CommandError:
                sent_messages.append(
                    await ctx.send("I wasn't able to extract a role from your response. Please try again!")
                )
    except TimeoutError:
        await ctx.send("Didn't receive a response in time. You can restart the command whenever you're ready!")
        return sent_messages, None


async def prompt_user_for_discord_message(
        bot: DreamBot, ctx: Context, initial_prompt: Optional[str] = None
) -> Tuple[List[discord.Message], Optional[discord.Message]]:
    """
    A method to fetch a discord.Message from a user.

    Parameters:
        bot (DreamBot): The discord bot.
        ctx (Context): The invocation context.
        initial_prompt (Optional[str]): The initial message to send during the prompt.

    Output:
        Command State Information.

    Returns:
        Tuple[List[discord.Message], Optional[discord.Message]]
    """

    sent_messages = [await ctx.send(initial_prompt)] if initial_prompt else []

    # wrap the entire operation in a try -> break this with timeout
    try:
        # give the user multiple attempts to pass a valid argument
        while True:
            # wait for them to respond
            response = await bot.wait_for(
                'message', timeout=30.0, check=lambda m: m.author == ctx.author and m.channel == ctx.channel
            )
            # try to convert their response to a message object
            try:
                message = await commands.MessageConverter().convert(ctx, response.content)
                return sent_messages, message
            except (commands.CommandError, commands.BadArgument):
                sent_messages.append(
                    await ctx.send("I wasn't able to extract a message from your response. Please try again!")
                )
    except TimeoutError:
        await ctx.send("Didn't receive a response in time. You can restart the command whenever you're ready!")
        return sent_messages, None


async def prompt_user_for_content(
        bot: DreamBot, ctx: Context, initial_prompt: Optional[str] = None
) -> Tuple[List[discord.Message], Optional[str]]:
    """
    A method to fetch message content from a user.

    Parameters:
        bot (DreamBot): The discord bot.
        ctx (Context): The invocation context.
        initial_prompt (Optional[str]): The initial message to send during the prompt.

    Output:
        Command State Information.

    Returns:
        Tuple[List[discord.Message], Optional[discord.Message]]
    """

    sent_messages = [await ctx.send(initial_prompt)] if initial_prompt else []

    # wrap the entire operation in a try -> break this with timeout
    try:
        # give the user multiple attempts to pass a valid argument
        while True:
            # wait for them to respond
            response = await bot.wait_for(
                'message', timeout=30.0, check=lambda m: m.author == ctx.author and m.channel == ctx.channel
            )
            # try to convert their response to a message object
            try:
                if response.content:
                    return sent_messages, response.content
                else:
                    raise commands.BadArgument
            except (commands.CommandError, commands.BadArgument):
                sent_messages.append(
                    await ctx.send("I wasn't able to extract message content from your response. Please try again!")
                )
    except TimeoutError:
        await ctx.send("Didn't receive a response in time. You can restart the command whenever you're ready!")
        return sent_messages, None
