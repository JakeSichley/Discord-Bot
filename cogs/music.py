"""
The MIT License (MIT)

Copyright (c) 2019-2020 PythonistaGuild

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""

from discord.ext import commands, menus
from typing import Optional
from os import getenv
from dreambot import DreamBot
from utils.context import Context
import asyncio
import async_timeout
import copy
import datetime
import discord
import math
import random
import re
import wavelink
import tekore as tk


# URL matching REGEX
URL_REG = re.compile(r'https?://(?:www\.)?.+')
# Spotify URI matching REGEX https://regex101.com/r/tDtsTS/1
SPOTIFY_REG = re.compile(r'^(https://open.spotify.com/user/spotify/playlist/|spotify:user:spotify:playlist:|'
                         r'https://open.spotify.com/track/|spotify:track:)([a-zA-Z0-9]+)(.*)$')


class NoChannelProvided(commands.CommandError):
    """
    Error raised when no suitable voice channel was supplied.
    """

    pass


class IncorrectChannelError(commands.CommandError):
    """
    Error raised when commands are issued outside the player's session channel.
    """

    pass


class Track(wavelink.Track):
    """
    Wavelink Track object with a requester attribute.

    Attributes:
        id (str): The Base64 Track ID.
        info (dict): The raw track info.
        title (str): The track title.
        identifier (Optional[str]): The track's identifier. Could be None depending on track type.
        ytid (Optional[str]): The tracks YouTube ID. Could be None if ytsearch was not used.
        length (float): The duration of the track.
        duration (float): Alias to length.
        uri (Optional[str]): The tracks URI. Could be None.
        author (Optional[str]): The author of the track. Could be None
        is_stream (bool): Indicated whether the track is a stream or not.
        thumb (Optional[str]): The thumbnail URL associated with the track. Could be None.
        requester (Union[discord.User, discord.Member]): The user that requested the track.
    """

    __slots__ = ('requester', )

    def __init__(self, *args, **kwargs):
        """
        The constructor for the Track class.

        Parameters:
            args (*tuple): Positional args for the Track class.
            kwargs (**dict): Keyword args for the Track class.
        """

        super().__init__(*args)

        self.requester = kwargs.get('requester')


class Player(wavelink.Player):
    """
    Custom wavelink Player class.

    Attributes:
        bot (DreamBot): The Discord bot.
        guild_id (int): The guild ID the player is connected to.
        node (wavelink.node.Node): The node the player belongs to.
        volume (int): The players volume.
        channel_id (int): The channel the player is connected to. Could be None if the player is not connected.
        context (Context): The invocation context for the player. Could be None if the player is not connected.
        dj (Union[discord.User, discord.Member]): The user that invoked the player.
        queue (asyncio.Queue[Track]): An asynchronous queue containing the tracks.
        spotify (tekore.Spotify): The Spotify class used to query Spotify API data.
        waiting (bool): Whether the player is waiting for the next track (queue empty).
        updating (bool): Whether the player controller is updating.
        pause_votes (set[Union[discord.User, discord.Member]]): A set of users who voted towards pausing.
        resume_votes (set[Union[discord.User, discord.Member]]): A set of users who voted towards resuming.
        skip_votes (set[Union[discord.User, discord.Member]]): A set of users who voted towards skipping.
        shuffle_votes (set[Union[discord.User, discord.Member]]): A set of users who voted towards shuffling.
        stop_votes (set[Union[discord.User, discord.Member]]): A set of users who voted towards stopping.
        repeat_votes (set[Union[discord.User, discord.Member]]): A set of users who voted towards repeating.
    """

    def __init__(self, *args, **kwargs):
        """
        The constructor for the Track class.

        Parameters:
            args (*tuple): Positional args for the Player class.
            kwargs (**dict): Keyword args for the Player class.
        """

        super().__init__(*args, **kwargs)

        self.context: Context = kwargs.get('context', None)
        if self.context:
            self.dj: discord.Member = self.context.author

        self.queue = asyncio.Queue()
        self.controller = None

        # https://github.com/felix-hilden/tekore/issues/245#issuecomment-792137357
        conf = (getenv('SPOTIFY_ID'), getenv('SPOTIFY_SECRET'))
        token = tk.request_client_token(*conf[:2])
        self.spotify = tk.Spotify(token, asynchronous=True)

        self.waiting = False
        self.updating = False

        self.pause_votes = set()
        self.resume_votes = set()
        self.skip_votes = set()
        self.shuffle_votes = set()
        self.stop_votes = set()
        self.repeat_votes = set()

    async def do_next(self) -> None:
        """
        Advances the player to the next track, or waits for the next track to be queued up if the queue is empty.

        Parameters:
            None.

        Returns:
            None.
        """

        if self.is_playing or self.waiting:
            return

        # Clear the votes for a new track
        self.pause_votes.clear()
        self.resume_votes.clear()
        self.skip_votes.clear()
        self.shuffle_votes.clear()
        self.stop_votes.clear()
        self.repeat_votes.clear()

        try:
            self.waiting = True
            with async_timeout.timeout(300):
                track = await self.queue.get()
        except asyncio.TimeoutError:
            # No music has been played for 5 minutes, cleanup and disconnect
            return await self.teardown()

        await self.play(track)
        self.waiting = False

        # Invoke our player's controller
        await self.invoke_controller()

    async def invoke_controller(self) -> None:
        """
        A method which updates or sends a new player controller.

        Parameters:
            None.

        Returns:
            None.
        """

        if self.updating:
            return

        self.updating = True

        # if there isn't a controller, build a new one
        if not self.controller:
            self.controller = InteractiveController(embed=self.build_embed(), player=self)
            await self.controller.start(self.context)

        # if the controller isn't in the last 5 messages, create a new controller
        elif not await self.is_position_fresh():
            try:
                await self.controller.message.delete()
            except discord.HTTPException:
                pass

            self.controller.stop()

            self.controller = InteractiveController(embed=self.build_embed(), player=self)
            await self.controller.start(self.context)

        else:
            embed = self.build_embed()
            await self.controller.message.edit(content=None, embed=embed)

        self.updating = False

    def build_embed(self) -> Optional[discord.Embed]:
        """
        A method which builds our player's controller embed.

        Parameters:
            None.

        Returns:
            embed (Optional[discord.Embed]): The player's controller embed.
        """

        track = self.current
        if not track:
            return

        channel = self.bot.get_channel(int(self.channel_id))
        qsize = self.queue.qsize()

        embed = discord.Embed(title=f'Music Controller | {channel.name}', colour=0xebb145)
        embed.description = f'Now Playing:\n**`{track.title}`**\n\n'
        embed.set_thumbnail(url=(track.thumb if track.thumb else self.bot.user.avatar_url))
        embed.add_field(name='Duration', value=str(datetime.timedelta(milliseconds=int(track.length))))
        embed.add_field(name='Queue Length', value=str(qsize))
        embed.add_field(name='Volume', value=f'**`{self.volume}%`**')
        embed.add_field(name='Requested By', value=track.requester.mention)
        embed.add_field(name='DJ', value=self.dj.mention)
        embed.add_field(name='Video URL', value=f'[Click Here!]({track.uri})')

        return embed

    async def is_position_fresh(self) -> bool:
        """
        Method which checks whether the player controller should be remade or updated.

        Parameters:
            None.

        Returns:
            (bool): Whether the controller is one of the 5 most recent messages.
        """

        try:
            async for message in self.context.channel.history(limit=5):
                if message.id == self.controller.message.id:
                    return True
        except (discord.HTTPException, AttributeError):
            return False

        return False

    async def teardown(self):
        """
        A method to clear internal states, remove the player's controller, and disconnect.

        Parameters:
            None.

        Returns:
            None.
        """

        try:
            await self.controller.message.delete()
        except discord.HTTPException:
            pass

        self.controller.stop()

        try:
            await self.destroy()
        except KeyError:
            pass


class InteractiveController(menus.Menu):
    """
    The Player's interactive controller menu class.

    Attributes:
        embed (discord.Embed): The player's controller embed.
        player (Player): The custom player class.
    """

    def __init__(self, *, embed: discord.Embed, player: Player):
        """
        The constructor for the Track class.

        Parameters:
            embed (discord.Embed): The player's controller embed.
            player (Player): The custom player class.
        """

        super().__init__(timeout=None)

        self.embed = embed
        self.player = player

    def update_context(self, payload: discord.RawReactionActionEvent) -> Context:
        """
        A method that update our context with the user who reacted.

        Parameters:
            payload (discord.RawReactionActionEvent): The reaction payload event details.

        Returns:
            ctx (Context): The updated context with the new author.
        """

        ctx = copy.copy(self.ctx)
        ctx.author = payload.member

        return ctx

    def reaction_check(self, payload: discord.RawReactionActionEvent) -> bool:
        """
        Check to make sure the reaction added meets our criteria.

        Parameters:
            payload (discord.RawReactionActionEvent): The reaction event's details.

        Returns:
            (bool): Whether the user AND the reaction added by the user are valid.
        """

        if payload.event_type == 'REACTION_REMOVE':
            return False

        if not payload.member:
            return False
        if payload.member.bot:
            return False
        if payload.message_id != self.message.id:
            return False
        if payload.member not in self.bot.get_channel(int(self.player.channel_id)).members:
            return False

        return payload.emoji in self.buttons

    async def send_initial_message(self, ctx: Context, channel: discord.TextChannel) -> discord.Message:
        """
        Sends the initial menu message.

        Parameters:
            ctx (Context): The context to send the initial message with.
            channel (discord.TextChannel): The channel to send the initial message to.

        Returns:
            (discord.Message): The message that was sent.
        """

        return await channel.send(embed=self.embed)

    @menus.button(emoji='\u25B6')
    async def resume_command(self, payload: discord.RawReactionActionEvent) -> None:
        """
        The menu's resume button. Invokes the resume command.

        Parameters:
            payload (discord.RawReactionActionEvent): The reaction event's details.

        Returns:
            None
        """

        ctx = self.update_context(payload)

        command = self.bot.get_command('resume')
        ctx.command = command

        await self.bot.invoke(ctx)

    @menus.button(emoji='\u23F8')
    async def pause_command(self, payload: discord.RawReactionActionEvent):
        """
        The menu's pause button. Invokes the pause command.

        Parameters:
            payload (discord.RawReactionActionEvent): The reaction event's details.

        Returns:
            None
        """

        ctx = self.update_context(payload)

        command = self.bot.get_command('pause')
        ctx.command = command

        await self.bot.invoke(ctx)

    @menus.button(emoji='\u23F9')
    async def stop_command(self, payload: discord.RawReactionActionEvent) -> None:
        """
        The menu's stop button. Invokes the stop command.

        Parameters:
            payload (discord.RawReactionActionEvent): The reaction event's details.

        Returns:
            None
        """

        ctx = self.update_context(payload)

        command = self.bot.get_command('stop')
        ctx.command = command

        await self.bot.invoke(ctx)

    @menus.button(emoji='\u23ED')
    async def skip_command(self, payload: discord.RawReactionActionEvent) -> None:
        """
        The menu's skip button. Invokes the skip command.

        Parameters:
            payload (discord.RawReactionActionEvent): The reaction event's details.

        Returns:
            None
        """

        ctx = self.update_context(payload)

        command = self.bot.get_command('skip')
        ctx.command = command

        await self.bot.invoke(ctx)

    @menus.button(emoji='\U0001F500')
    async def shuffle_command(self, payload: discord.RawReactionActionEvent) -> None:
        """
        The menu's shuffle button. Invokes the shuffle command.

        Parameters:
            payload (discord.RawReactionActionEvent): The reaction event's details.

        Returns:
            None
        """

        ctx = self.update_context(payload)

        command = self.bot.get_command('shuffle')
        ctx.command = command

        await self.bot.invoke(ctx)

    @menus.button(emoji='\U0001F501')
    async def repeat_command(self, payload: discord.RawReactionActionEvent) -> None:
        """
        The menu's repeat button. Invokes the repeat command.

        Parameters:
            payload (discord.RawReactionActionEvent): The reaction event's details.

        Returns:
            None
        """

        ctx = self.update_context(payload)

        command = self.bot.get_command('repeat')
        ctx.command = command

        await self.bot.invoke(ctx)

    @menus.button(emoji='\u2795')
    async def volup_command(self, payload: discord.RawReactionActionEvent) -> None:
        """
        The menu's volume up button. Invokes the vol_up command.

        Parameters:
            payload (discord.RawReactionActionEvent): The reaction event's details.

        Returns:
            None
        """

        ctx = self.update_context(payload)

        command = self.bot.get_command('vol_up')
        ctx.command = command

        await self.bot.invoke(ctx)

    @menus.button(emoji='\u2796')
    async def voldown_command(self, payload: discord.RawReactionActionEvent) -> None:
        """
        The menu's volume down button. Invokes the vol_down command.

        Parameters:
            payload (discord.RawReactionActionEvent): The reaction event's details.

        Returns:
            None
        """

        ctx = self.update_context(payload)

        command = self.bot.get_command('vol_down')
        ctx.command = command

        await self.bot.invoke(ctx)

    @menus.button(emoji='\U0001F1F6')
    async def queue_command(self, payload: discord.RawReactionActionEvent) -> None:
        """
        The menu's queue button. Invokes the queue command.

        Parameters:
            payload (discord.RawReactionActionEvent): The reaction event's details.

        Returns:
            None
        """

        ctx = self.update_context(payload)

        command = self.bot.get_command('queue')
        ctx.command = command

        await self.bot.invoke(ctx)


class PaginatorSource(menus.ListPageSource):
    """
    Player queue paginator class.

    Attributes:
        entries (List[str]): A sequence (list) of Track titles.
        per_page (Optional[int]): The number of entries to display per page.
    """

    def __init__(self, entries, *, per_page=8) -> None:
        """
        The constructor for the Track class.

        Parameters:
            entries (List[str]): A sequence (list) of Track titles.
            per_page (Optional[int]): The number of entries to display per page.
        """

        super().__init__(entries, per_page=per_page)

    async def format_page(self, menu: menus.Menu, page):
        """
        A method that formats a specified page.

        Parameters:
            menu (menus.Menu): The menu containing the page.
            page (Page[entries]): The page containing the entries to display.

        Returns:
            embed (discord.Embed): The embed containing the formatted page data.
        """

        embed = discord.Embed(title='Coming Up...', colour=0x4f0321)
        embed.description = '\n'.join(f'`{index}. {title}`' for index, title in enumerate(page, 1))

        return embed

    def is_paginating(self):
        """
        A method that specifies Whether to embed.
        We always want to embed, even on 1 page of results.

        Parameters:
            None.

        Returns:
            (bool): Whether we're paginating. Always True.
        """

        return True


class Music(commands.Cog, wavelink.WavelinkMixin):
    """
    Music cog.

    Attributes:
        bot (DreamBot): The Discord bot class.
    """

    def __init__(self, bot: DreamBot) -> None:
        """
        The constructor for the Track class.

        Parameters:
            bot (DreamBot): The Discord bot.
        """

        self.bot = bot

        if not hasattr(bot, 'wavelink') or not bot.wavelink:
            bot.wavelink = wavelink.Client(bot=bot)

        bot.loop.create_task(self.start_nodes())

    async def start_nodes(self) -> None:
        """
        Connect and initiate nodes for the wavelink client.

        Parameters:
            None.

        Returns:
            None.
        """

        await self.bot.wait_until_ready()

        if self.bot.wavelink.nodes:
            previous = self.bot.wavelink.nodes.copy()

            for node in previous.values():
                await node.destroy()

        # noinspection HttpUrlsUsage
        nodes = {'MAIN': {'host': '127.0.0.50',
                          'port': 2333,
                          'rest_uri': 'http://127.0.0.50:2333',
                          'password': getenv('LAVALINK_TOKEN'),
                          'identifier': 'DREAM-BOT-MUSIC',
                          'region': 'us_west'
                          }}

        for n in nodes.values():
            await self.bot.wavelink.initiate_node(**n)

    @wavelink.WavelinkMixin.listener()
    async def on_node_ready(self, node: wavelink.Node) -> None:
        """
        Listener event for when a node is ready.

        Parameters:
            node (wavelink.Node): The node that is ready.

        Returns:
            None.
        """

        print(f'Node {node.identifier} is ready!')

    # noinspection PyUnusedLocal
    @wavelink.WavelinkMixin.listener('on_track_stuck')
    @wavelink.WavelinkMixin.listener('on_track_end')
    @wavelink.WavelinkMixin.listener('on_track_exception')
    async def on_player_stop(self, node: wavelink.Node, payload) -> None:
        """
        Listener event for when the player stops due to a wavelink event.

        Parameters:
            node (wavelink.Node): Not used.
            payload (Union[wavelink.TrackStuck, wavelink.TrackEnd, wavelink.TrackException]):
                Payload details for the specified wavelink event.

        Returns:
            None.
        """

        await payload.player.do_next()

    # noinspection PyUnusedLocal
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState,
                                    after: discord.VoiceState) -> None:
        """
        Listener event for when a member's voice state is updated.
        Used for updating the DJ in the event the DJ leaves before the player is stopped.

        Parameters:
            member (discord.Member): The member whose voice state was updated.
            before (discord.VoiceState): Not used.
            after (discord.VoiceState): The updated voice state for the member.

        Returns:
            None.
        """

        if member.bot:
            return

        player: Player = self.bot.wavelink.get_player(member.guild.id, cls=Player)

        # if a channel_id or context is not present for the given player, destroy the player
        if not player.channel_id or not player.context:
            player.node.players.pop(member.guild.id)
            return

        channel = self.bot.get_channel(int(player.channel_id))

        # if the current DJ left, loop through the remaining channel members and assign a new DJ
        if member == player.dj and after.channel is None:
            for m in channel.members:
                if m.bot:
                    continue
                else:
                    player.dj = m
                    return

        # if the member is in the player channel and the DJ is not present, the member becomes the DJ
        elif after.channel == channel and player.dj not in channel.members:
            player.dj = member

    async def cog_command_error(self, ctx: Context, error: Exception) -> None:
        """
        A cog-wide error handler.

        Parameters:
            ctx (Context): The invocation context that resulted in an exception.
            error: (Exception): The exception that arose.

        Returns:
            None.
        """

        if isinstance(error, IncorrectChannelError):
            return

        if isinstance(error, NoChannelProvided):
            await ctx.send('You must be in a voice channel or provide one to connect to.')
            return

    async def cog_check(self, ctx: Context) -> bool:
        """
        A cog-wide command check.
        Disables the use of commands in DMs.

        Parameters:
            ctx (Context): The invocation context.

        Returns:
            (bool): Whether the command should execute.
        """

        if not ctx.guild:
            await ctx.send('Music commands are not available in Private Messages.')
            return False

        return True

    async def cog_before_invoke(self, ctx: Context) -> None:
        """
        A cog-wide before-invoke hook.
        Mainly used to check whether the user is in the player's controller channel.

        Parameters:
            ctx (Context): The invocation context.

        Returns:
            None.
        """

        player: Player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player, context=ctx)

        # ensure the command invocation channel is the player's initial channel
        if player.context:
            if player.context.channel != ctx.channel:
                await ctx.send(f'{ctx.author.mention}, you must be in '
                               f'{player.context.channel.mention} for this session.')
                raise IncorrectChannelError

        # don't proceed with connection if there is no invocation context
        if ctx.command.name == 'connect' and not player.context:
            return
        elif self.is_privileged(ctx):
            return

        if not player.channel_id:
            return

        # if we cannot fetch the player's channel, don't execute the command
        channel = self.bot.get_channel(int(player.channel_id))
        if not channel:
            return

        # ensure voice commands are only executed in the initial channel
        if player.is_connected:
            if ctx.author not in channel.members:
                await ctx.send(f'{ctx.author.mention}, you must be in `{channel.name}` to use voice commands.')
                raise IncorrectChannelError

    async def cog_after_invoke(self, ctx: Context) -> None:
        """
        A cog-wide after-invoke hook.
        Mainly used to clear invoking messages for commands.

        Parameters:
            ctx (Context): The invocation context.

        Returns:
            None.
        """

        # allow the invoking message to persist for 15 seconds
        await asyncio.sleep(15)

        try:
            await ctx.message.delete()
        except discord.HTTPException:
            pass

    def required(self, ctx: Context) -> int:
        """
        A method which returns required votes based on amount of members in a channel.

        Parameters:
            ctx (Context): The invocation context.

        Returns:
            required (int): The required number of votes necessary for non-privileged command execution.
        """

        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)
        channel = self.bot.get_channel(int(player.channel_id))
        required = math.ceil((len(channel.members) - 1) / 2.5)

        if ctx.command.name == 'stop':
            if len(channel.members) - 1 == 2:
                required = 2

        return required

    def is_privileged(self, ctx: Context) -> bool:
        """
        A method that checks Whether the invoking user is an Admin or a DJ.

        Parameters:
            ctx (Context): The invocation context.

        Returns:
            (bool): Whether the invoking user has kick permissions or is a DJ.
        """

        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        return player.dj == ctx.author or ctx.author.guild_permissions.kick_members

    @commands.command()
    async def connect(self, ctx: Context, *, channel: discord.VoiceChannel = None) -> None:
        """
        A command that connects the player to a voice channel.

        Parameters:
            ctx (Context): The invocation context.
            channel (discord.VoiceChannel): The channel to connect to. Default: None.

        Returns:
            None.
        """

        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if player.is_connected:
            return

        channel = getattr(ctx.author.voice, 'channel', channel)
        if channel is None:
            raise NoChannelProvided

        await player.connect(channel.id)

    @commands.command()
    async def play(self, ctx: Context, *, query: str) -> None:
        """
        A command to play or queue a song with the given query.

        Parameters:
            ctx (Context): The invocation context.
            query (str): The query to play.

        Returns:
            None.
        """

        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if not player.is_connected:
            await ctx.invoke(self.connect)

        # strip 'no-embed' tags from the query
        query = query.strip('<>')
        # if the query matches a spotify specific link, retrieve details from Spotify's API
        if match := SPOTIFY_REG.search(query):
            # noinspection PyUnresolvedReferences
            result = await player.spotify.track(match.group(2))
            query = f'ytsearch:{" ".join(x.name for x in result.artists)} {result.name}'
        elif not URL_REG.match(query):
            query = f'ytsearch:{query}'

        tracks = await self.bot.wavelink.get_tracks(query)
        if not tracks:
            await ctx.send('No songs were found with that query. Please try again.', delete_after=15)
            return

        # if the user supplied a playlist, add all the tracks to the queue
        # otherwise, add the single specified track to the queue
        if isinstance(tracks, wavelink.TrackPlaylist):
            for track in tracks.tracks:
                track = Track(track.id, track.info, requester=ctx.author)
                await player.queue.put(track)

            await ctx.send(f'```ini\nAdded the playlist {tracks.data["playlistInfo"]["name"]}'
                           f' with {len(tracks.tracks)} songs to the queue.\n```', delete_after=15)
        else:
            track = Track(tracks[0].id, tracks[0].info, requester=ctx.author)
            await ctx.send(f'```ini\nAdded {track.title} to the Queue\n```', delete_after=15)
            await player.queue.put(track)

        # if the player is not active, invoke the next action (likely play)
        if not player.is_playing:
            await player.do_next()

    @commands.command()
    async def pause(self, ctx: Context) -> None:
        """
        A command to pause the current song.
        If the invoking user is not privileged, voting is required.

        Parameters:
            ctx (Context): The invocation context.

        Returns:
            None.
        """

        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if player.is_paused or not player.is_connected:
            return

        if self.is_privileged(ctx):
            await ctx.send('An admin or DJ has paused the player.', delete_after=10)
            player.pause_votes.clear()

            await player.set_pause(True)
            return

        required = self.required(ctx)
        player.pause_votes.add(ctx.author)

        if len(player.pause_votes) >= required:
            await ctx.send('Vote to pause passed. Pausing player.', delete_after=10)
            player.pause_votes.clear()
            await player.set_pause(True)
        else:
            await ctx.send(f'{ctx.author.mention} has voted to pause the player.', delete_after=15)

    @commands.command()
    async def resume(self, ctx: Context) -> None:
        """
        A command to resume the current song.
        If the invoking user is not privileged, voting is required.

        Parameters:
            ctx (Context): The invocation context.

        Returns:
            None.
        """

        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if not player.is_paused or not player.is_connected:
            return

        if self.is_privileged(ctx):
            await ctx.send('An admin or DJ has resumed the player.', delete_after=10)
            player.resume_votes.clear()

            await player.set_pause(False)
            return

        required = self.required(ctx)
        player.resume_votes.add(ctx.author)

        if len(player.resume_votes) >= required:
            await ctx.send('Vote to resume passed. Resuming player.', delete_after=10)
            player.resume_votes.clear()
            await player.set_pause(False)
        else:
            await ctx.send(f'{ctx.author.mention} has voted to resume the player.', delete_after=15)

    @commands.command()
    async def skip(self, ctx: Context) -> None:
        """
        A command to skip the current song.
        If the invoking user is not privileged, voting is required.

        Parameters:
            ctx (Context): The invocation context.

        Returns:
            None.
        """

        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if not player.is_connected:
            return

        if self.is_privileged(ctx):
            await ctx.send('An admin or DJ has skipped the song.', delete_after=10)
            player.skip_votes.clear()

            await player.stop()
            return

        if ctx.author == player.current.requester:
            await ctx.send('The song requester has skipped the song.', delete_after=10)
            player.skip_votes.clear()

            await player.stop()
            return

        required = self.required(ctx)
        player.skip_votes.add(ctx.author)

        if len(player.skip_votes) >= required:
            await ctx.send('Vote to skip passed. Skipping song.', delete_after=10)
            player.skip_votes.clear()
            await player.stop()
        else:
            await ctx.send(f'{ctx.author.mention} has voted to skip the song.', delete_after=15)

    @commands.command()
    async def stop(self, ctx: Context) -> None:
        """
        A command to stop the player and clear all internal states/caches.
        If the invoking user is not privileged, voting is required.

        Parameters:
            ctx (Context): The invocation context.

        Returns:
            None.
        """

        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if not player.is_connected:
            return

        if self.is_privileged(ctx):
            await ctx.send('An admin or DJ has stopped the player.', delete_after=10)
            await player.teardown()
            return

        required = self.required(ctx)
        player.stop_votes.add(ctx.author)

        if len(player.stop_votes) >= required:
            await ctx.send('Vote to stop passed. Stopping the player.', delete_after=10)
            await player.teardown()
        else:
            await ctx.send(f'{ctx.author.mention} has voted to stop the player.', delete_after=15)

    @commands.command(aliases=['v', 'vol'])
    async def volume(self, ctx: Context, *, vol: int) -> None:
        """
        A command to change the player's volume.
        If the invoking user is not privileged, the command will not execute.

        Parameters:
            ctx (Context): The invocation context.
            vol (int): The volume level to player should be set to.

        Returns:
            None.
        """

        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if not player.is_connected:
            return

        if not self.is_privileged(ctx):
            await ctx.send('Only the DJ or admins may change the volume.')
            return

        if not 0 < vol < 101:
            await ctx.send('Please enter a value between 1 and 100.')
            return

        await player.set_volume(vol)
        await ctx.send(f'Set the volume to **{vol}**%', delete_after=7)

    @commands.command(aliases=['loop'])
    async def repeat(self, ctx: Context) -> None:
        """
        A command to repeat the current song.
        If the invoking user is not privileged, voting is required.

        Parameters:
            ctx (Context): The invocation context.

        Returns:
            None.
        """

        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if not player.is_connected:
            return

        if player.queue.qsize() == 0:
            await ctx.send('There are no more songs in the queue.', delete_after=15)
            return

        if self.is_privileged(ctx):
            await ctx.send('An admin or DJ has repeated the current track.', delete_after=10)
            player.repeat_votes.clear()
            # noinspection PyUnresolvedReferences
            # noinspection PyProtectedMember
            await self.rebuild_queue_with_repeat(player)
            return

        required = self.required(ctx)
        player.repeat_votes.add(ctx.author)

        if len(player.repeat_votes) >= required:
            await ctx.send('Vote to repeat passed. Repeating the current track..', delete_after=10)
            player.repeat_votes.clear()
            # noinspection PyUnresolvedReferences
            # noinspection PyProtectedMember
            await self.rebuild_queue_with_repeat(player)
        else:
            await ctx.send(f'{ctx.author.mention} has voted to repeat the current track.', delete_after=15)

    @commands.command(aliases=['mix'])
    async def shuffle(self, ctx: Context) -> None:
        """
        A command to shuffle the current queue.
        If the invoking user is not privileged, voting is required.

        Parameters:
            ctx (Context): The invocation context.

        Returns:
            None.
        """

        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if not player.is_connected:
            return

        if player.queue.qsize() < 3:
            await ctx.send('Add more songs to the queue before shuffling.', delete_after=15)
            return

        if self.is_privileged(ctx):
            await ctx.send('An admin or DJ has shuffled the playlist.', delete_after=10)
            player.shuffle_votes.clear()
            # noinspection PyUnresolvedReferences
            # noinspection PyProtectedMember
            random.shuffle(player.queue._queue)
            return

        required = self.required(ctx)
        player.shuffle_votes.add(ctx.author)

        if len(player.shuffle_votes) >= required:
            await ctx.send('Vote to shuffle passed. Shuffling the playlist.', delete_after=10)
            player.shuffle_votes.clear()
            # noinspection PyUnresolvedReferences
            # noinspection PyProtectedMember
            random.shuffle(player.queue._queue)
        else:
            await ctx.send(f'{ctx.author.mention} has voted to shuffle the playlist.', delete_after=15)

    @commands.command(hidden=True)
    async def vol_up(self, ctx: Context) -> None:
        """
        A command to increase the player's volume.
        If the invoking user is not privileged, the command will not execute.

        Parameters:
            ctx (Context): The invocation context.

        Returns:
            None.
        """

        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if not player.is_connected or not self.is_privileged(ctx):
            return

        vol = int(math.ceil((player.volume + 10) / 10)) * 10

        if vol > 100:
            vol = 100
            await ctx.send('Maximum volume reached', delete_after=7)

        await player.set_volume(vol)

    @commands.command(hidden=True)
    async def vol_down(self, ctx: Context) -> None:
        """
        A command to decrease the player's volume.
        If the invoking user is not privileged, the command will not execute.

        Parameters:
            ctx (Context): The invocation context.

        Returns:
            None.
        """

        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if not player.is_connected or not self.is_privileged(ctx):
            return

        vol = int(math.ceil((player.volume - 10) / 10)) * 10

        if vol < 0:
            vol = 0
            await ctx.send('Player is currently muted', delete_after=10)

        await player.set_volume(vol)

    @commands.command(aliases=['eq'])
    async def equalizer(self, ctx: Context, *, equalizer: str) -> None:
        """
        A command to change the player's equalizer.
        If the invoking user is not privileged, the command will not execute.

        Parameters:
            ctx (Context): The invocation context.
            equalizer (str): The equalizer to change to.

        Returns:
            None.
        """

        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if not player.is_connected:
            return

        if not self.is_privileged(ctx):
            await ctx.send('Only the DJ or admins may change the equalizer.')
            return

        eqs = {'flat': wavelink.Equalizer.flat(),
               'boost': wavelink.Equalizer.boost(),
               'metal': wavelink.Equalizer.metal(),
               'piano': wavelink.Equalizer.piano()}

        eq = eqs.get(equalizer.lower(), None)

        if not eq:
            joined = "\n".join(eqs.keys())
            await ctx.send(f'Invalid EQ provided. Valid EQs:\n\n{joined}')
            return

        await ctx.send(f'Successfully changed equalizer to {equalizer}', delete_after=15)
        await player.set_eq(eq)

    @commands.command(aliases=['q', 'que'])
    async def queue(self, ctx: Context) -> None:
        """
        A command to display the player's queue of songs.

        Parameters:
            ctx (Context): The invocation context.

        Returns:
            None.
        """

        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if not player.is_connected:
            return

        if player.queue.qsize() == 0:
            await ctx.send('There are no more songs in the queue.', delete_after=15)
            return

        # noinspection PyUnresolvedReferences
        # noinspection PyProtectedMember
        entries = [track.title for track in player.queue._queue]
        pages = PaginatorSource(entries=entries)
        paginator = menus.MenuPages(source=pages, timeout=None, delete_message_after=True)

        await paginator.start(ctx)

    @commands.command(aliases=['np', 'current'])
    async def now_playing(self, ctx: Context):
        """
        A command to refresh the player's controller embed.

        Parameters:
            ctx (Context): The invocation context.

        Returns:
            None.
        """

        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if not player.is_connected:
            return

        await player.invoke_controller()

    @commands.command(aliases=['swap'])
    async def swap_dj(self, ctx: Context, *, member: discord.Member = None) -> None:
        """
        A command to swap the DJ to different member currently in the voice channel.

        Parameters:
            ctx (Context): The invocation context.
            member (discord.Member): The member to swap the DJ position to. Default: None.

        Returns:
            None.
        """

        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if not player.is_connected:
            return

        if not self.is_privileged(ctx):
            await ctx.send('Only admins and the DJ may use this command.', delete_after=15)
            return

        members = self.bot.get_channel(int(player.channel_id)).members

        if member and member not in members:
            await ctx.send(f'{member} is not currently in voice, so they cannot be a DJ.', delete_after=15)
            return

        if member and member == player.dj:
            await ctx.send('Cannot swap DJ to the current DJ... :^)', delete_after=15)
            return

        if len(members) <= 2:
            await ctx.send('No more members to swap to.', delete_after=15)
            return

        if member:
            player.dj = member
            await ctx.send(f'{member.mention} is now the DJ.')
            return

        for m in members:
            if m == player.dj or m.bot:
                continue
            else:
                player.dj = m
                await ctx.send(f'{member.mention} is now the DJ.')
            return

    async def rebuild_queue_with_repeat(self, player: Player) -> None:
        """
        A method to rebuild the queue with a repeated song.
        Executed after the repeat command is successfully invoked.

        Parameters:
            player (Player): The wavelink player containing the Track queue.

        Returns:
            None.
        """

        # grab the current track again
        tracks = await self.bot.wavelink.get_tracks(player.current.uri)
        track = Track(tracks[0].id, tracks[0].info, requester=self.bot.user)

        # build a new queue
        new_queue = asyncio.Queue()
        await new_queue.put(track)

        # pop all items from the current queue into the new queue
        # noinspection PyUnresolvedReferences
        # noinspection PyProtectedMember
        for track in player.queue._queue:
            await new_queue.put(track)

        # assign new queue to the player queue
        player.queue = new_queue

    def cog_unload(self) -> None:
        """
        A method detailing custom extension unloading procedures.
        Destroys the wavelink client.

        Parameters:
            None.

        Returns:
            None.
        """

        self.bot.wavelink = None

        print('Completed Unload for Cog: Music')


def setup(bot: DreamBot) -> None:
    """
    A setup function that allows the cog to be treated as an extension.

    Parameters:
        bot (DreamBot): The bot the cog should be added to.

    Returns:
        None.
    """

    bot.add_cog(Music(bot))
    print('Completed Setup for Cog: Music')
