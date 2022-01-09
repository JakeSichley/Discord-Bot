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

from os import getenv
from discord.ext import commands
from google.cloud.firestore import AsyncClient, ArrayUnion
from google.oauth2 import service_account
from datetime import datetime
from dreambot import DreamBot
import discord
import logging
# noinspection PyTypeChecker


class Firestore(commands.Cog):
    """
    A Cogs class that supports Firestore logging.

    Attributes:
        bot (DreamBot): The Discord bot class.
        firestore (AsyncClient): The async Google Firestore client.

    """

    def __init__(self, bot: DreamBot) -> None:
        """
        The constructor for the Moderation class.

        Parameters:
            bot (DreamBot): The Discord bot class.
        """

        self.bot = bot

        credentials = service_account.Credentials.from_service_account_file('firebase-auth.json')
        project = getenv('FIRESTORE_PROJECT')
        self.firestore = AsyncClient(project=project, credentials=credentials)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """
        A listener method that is called whenever a message is sent.

        Parameters:
            message (discord.Message): The message that was sent.

        Returns:
            None.
        """

        doc = self.firestore.document(f'guilds/{message.guild.id}/channels/{message.channel.id}/messages/{message.id}')

        await doc.set({
            'auth-name': str(message.author),
            'auth-id': message.author.id,
            'created': message.created_at,
            'id': message.id,
            'content': message.clean_content,
        })

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload: discord.RawMessageUpdateEvent) -> None:
        """
        A listener method that is called whenever a message is updated.
        'raw' events fire regardless of whether a message is cached.

        Parameters:
           payload (discord.RawMessageUpdateEvent): Represents a payload for a raw message update event.

        Returns:
           None.
        """

        if guild_id := payload.data.get('guild_id'):
            doc = self.firestore.document(
                f'guilds/{guild_id}/channels/{payload.channel_id}/messages/{payload.message_id}'
            )

            await doc.update({
                'edits': ArrayUnion([{
                    'time': datetime.fromisoformat(payload.data.get('timestamp', datetime.now().isoformat())),
                    'content': payload.data.get('content')
                }])
            })

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent) -> None:
        """
        A listener method that is called whenever a message is deleted.
        'raw' events fire regardless of whether a message is cached.

        Parameters:
           payload (discord.RawMessageDeleteEvent): Represents a payload for a raw message deletion event.

        Returns:
           None.
        """

        doc = self.firestore.document(
            f'guilds/{payload.guild_id}/channels/{payload.channel_id}/messages/{payload.message_id}'
        )

        await doc.update({
            'deleted': datetime.now()
        })


def setup(bot: DreamBot) -> None:
    """
    A setup function that allows the cog to be treated as an extension.

    Parameters:
        bot (DreamBot): The bot the cog should be added to.

    Returns:
        None.
    """

    bot.add_cog(Firestore(bot))
    logging.info('Completed Setup for Cog: Firestore')
