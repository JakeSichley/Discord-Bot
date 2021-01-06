# Discord-Bot (DreamBot)
A Python-based bot for Discord utilizing [Rapptz's Discord Wrapper](https://github.com/Rapptz/discord.py).

#### Versions
**Python**: 3.8.1

**discord.py**: 1.5.1

# Overview
This bot is designed for personal use in Discord servers that I somehow have power in.

I originally created this bot in order to learn how to create a bot in Python - though it actually has _some_ useful functionalities
now.

# Cogs
Each cog contains specialized methods the bot can perform.

## Admin
The `Admin` cog contains administration functions that directly impact the execution of the bot. Allows for hot-reloading
of any cog in addition to an eval command.

## DDO
The `DDO` cog contains methods specifically related to Dungeons & Dragons Online. Functionality includes simulated die rolling 
and item information pull from the DDOWiki.

Thanks to [DDO Audit](https://www.playeraudit.com/), LFM data is also available!

## Exceptions
The `Exceptions` cog provides centralized handling for any errors that may arise during execution of the bot.

## MemeCoin
The `MemeCoin` cog contains methods related to the fictitious currency created for the Guild's 'Memes' channel. Users can award 
or revoke 'Meme Coins' at will by reacting to a message with a :heavy_check_mark: or :x: respectively.

## Moderation
The `Moderation` cog contains methods related to the moderation of a Discord server. Supports advanced logging, such as 
message edit and deletion events.

## Utility
The `Utility` cog contains various unrelated methods, such as the current time in a specified timezone, an invite to the
development server, and setting a guild-specific command prefix.

## Music
The `Music` cog implements a fully-functional music player. Back-end is driven by a 
[Lavalink Wrapper](https://github.com/PythonistaGuild/Wavelink) client, while the front-end is a modified version of the 
[PythonistaGuild's](https://github.com/PythonistaGuild/Wavelink/blob/master/examples/advanced.py) advanced 
implementation.

## Images
The `Images` cog implements a number of image manipulation commands supported by Pillow.

## Reactions
The `Reactions` cog implements the concept of 'Reaction Roles'. Users can react to specified messages to receive 
corresponding roles within the guild.

## Voice Roles
The `VoiceRoles` cog implements the concept of 'Voice Roles'. Users will automatically be assigned a specified role when
they join a channel and subsequently have the role revoked when leaving.