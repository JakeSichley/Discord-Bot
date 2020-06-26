# Discord-Bot (DreamBot)
A Python-based bot for Discord utilizing [Rapptz's Discord Wrapper](https://github.com/Rapptz/discord.py)

# Overview
This bot is designed for personal use in Discord servers that I somehow have power in.

I originally created this bot in order to learn how to create a bot in Python - though it actually has _some_ useful functionalities
now.

# Cogs
Each cog contains specialized methods the bot can perform.

## Admin
The `Admin` cog contains admistration functions that directly impact the execution of the bot. Allows for hot-reloading
of any cog in addition to an eval command.

## DDO
The `DDO` cog contains methods specifically related to Dungeons & Dragons Online. Functionality includes simulated die rolling 
and item information pull from the DDOWiki.

Thanks to [DDO Audit](https://www.playeraudit.com/), LFM data is also available!

## Exceptions
The `Exceptions` cog provides centralized handling for any errors that may arise during execution of the bot.

## MemeCoin
The `MemeCoin` cog contains methods related to the ficticious currency created for the Guild's 'Memes' channel. Users can award 
or revoke 'Meme Coins' at will by reacting to a message with a :heavy_check_mark: or :x: respectively.

## Moderation
The `Moderation` cog contains methods related to the moderation of a Discord server.

## Utility
The `Utility` cog contains various unrelated methods, such as the current time in a specified timezone, an invite to the
development server, and setting a guild-specific command prefix.

