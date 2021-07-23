import discord
from os import getenv
from discord.ext import commands
from google.cloud.firestore import AsyncClient, ArrayUnion
from google.oauth2 import service_account
from datetime import datetime
# noinspection PyTypeChecker


class Firestore(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        """
        The constructor for the Moderation class.

        Parameters:
            bot (commands.Bot): The Discord bot class.
        """

        credentials = service_account.Credentials.from_service_account_file('firebase-auth.json')
        project = getenv('FIRESTORE_PROJECT')
        self.firestore = AsyncClient(project=project, credentials=credentials)
        self.bot = bot

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
        'raw' events fire regardless of whether or not a message is cached.

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
        'raw' events fire regardless of whether or not a message is cached.

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


def setup(bot: commands.Bot) -> None:
    """
    A setup function that allows the cog to be treated as an extension.

    Parameters:
        bot (commands.Bot): The bot the cog should be added to.

    Returns:
        None.
    """

    bot.add_cog(Firestore(bot))
    print('Completed Setup for Cog: Firestore')
