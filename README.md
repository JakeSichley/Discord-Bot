# Discord-Bot (DreamBot)
A Python-based bot for Discord utilizing [Rapptz's Discord Wrapper](https://github.com/Rapptz/discord.py).

#### Versions
**Python**: 3.9.2

**discord.py**: 2.0.1

# Overview
I created this bot as a way to learn how to use Python - what was originally a simple Discord bot
has evolved into a powerful bot that supports a variety of features.

DreamBot currently serves the CSU Fullerton League of Legends club, several Twitch community Discords, and several Lost Ark community Discords.

# Cogs
Each cog contains specialized methods the bot can perform.

## Admin
The `Admin` cog contains administration functions that directly impact the execution of the bot. Allows for hot-reloading
of any cog, SQL statement execution, and Python code-block execution.

## Audit
The `Audit` cog contains methods that allow for logging specified server events.

## DDO
The `DDO` cog contains methods specifically related to Dungeons & Dragons Online. Functionality includes simulated die rolling 
and item information fetching from the DDOWiki.

Thanks to [DDO Audit](https://www.playeraudit.com/), LFM data is also available!

## Exceptions
The `Exceptions` cog provides centralized handling for any errors during the bot's execution.

## Images
The `Images` cog implements several image manipulation commands supported by Pillow.

## Moderation
The `Moderation` cog contains methods related to the moderation of a Discord server. Supports advanced logging, such as 
message edit and deletion events.

## Reactions
The `Reactions` cog implements the concept of 'Reaction Roles'. Users can react to specified messages to receive 
corresponding roles within the guild.

## Tags
The `Tags` cog allows you to save content under a tag name and retrieve it later.

## Utility
The `Utility` cog contains various unrelated methods, such as the current time in a specified timezone, an invite to the
development server, and setting a guild-specific command prefix.

## Voice Roles
The `VoiceRoles` cog implements the concept of 'Voice Roles.' Users will automatically be assigned a specified role when
they join a channel and subsequently have the role revoked when leaving.

# Deprecated Cogs

## Firestore
#### Deprecated: Message logging is now implemented in the `Audit` cog.
The `Firestore` cog utilizes Google's Firestore database to provide message logging.

## MemeCoin
#### Deprecated: MemeCoin is no longer utilized. A better currency system may be implemented in the future.
The `MemeCoin` cog contains methods related to the fictitious currency created for the guild's 'Memes' channel. Users can award 
or revoke 'Meme Coins' at will by reacting to a message with a :heavy_check_mark: or :x: respectively.

## Music
#### Deprecated: Music will require a rewrite utilizing Wavelink >= 1.0.
The `Music` cog implements a fully-functional music player. The backend is driven by a 
[Lavalink Wrapper](https://github.com/PythonistaGuild/Wavelink) client, while the front-end is a modified version of the 
[PythonistaGuild's](https://github.com/PythonistaGuild/Wavelink/blob/master/examples/advanced.py) advanced 
implementation.

## Twitch
#### Deprecated: Twitch will require a rewrite utilizing TwitchIO >= 2.0.
The `Twitch` cog builds a Twitch chatbot into the main Discord bot and allows for the execution of Twitch commands from Discord.