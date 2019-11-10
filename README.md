# Discord-Bot (DreamBot)
A Python-based bot for Discord utilizing [Rapptz's Discord Wrapper](https://github.com/Rapptz/discord.py)

# Overview
This bot is designed for the Dungeons & Dragons Online Guild 'Lava Divers'.
The primary purpose of this bot was to learn how to create a bot in Python as well as gain experience with popular libraries.

# Cogs
Each cog contains specialized methods related to various operators the bot can perform.
## Utility
The `Utility` cog contains somewhat unrelated methods, such as the current time and an invite to the development server.
## DDO
The `DDO` cog contains methods specifically related to Dungeons & Dragons Online. Functionality includes simulated die rolling 
and item information pull from the DDOWiki.
## MemeCoin
The `MemeCoin` cog contains methods related to the ficticious currency created for the Guild's 'Memes' channel. Users can award 
or revoke 'Meme Coins' at will by reacting to a message with a :heavy_check_mark: or :x: respectively.'
## Exceptions
The `Exceptions` cog provides centralized handling for an errors that may arise during execution of the bot.
