# Discord-Bot (Willump Bot)
A Python-based bot for Discord utilizing [Rapptz's Discord Wrapper](https://github.com/Rapptz/discord.py).

#### Versions
**Python**: 3.9.2

**discord.py**: 2.5.2

# Overview
I created this bot as a way to learn how to use Python. Since then, Willump Bot (formerly DreamBot) has evolved from a 
learning project into a powerful bot that supports various unique features.

Willump Bot currently serves the CSU Fullerton League of Legends club, Twitch community Discords, and Lost Ark 
community Discords.

# Cogs
Each cog contains specialized methods the bot can perform.

## Admin
The `Admin` cog contains administration functions that directly impact the execution of the bot. Allows for 
hot-reloading of any cog, SQL statement execution, and Python code-block execution.

## DDO
The `DDO` cog contains methods specifically related to Dungeons & Dragons Online. Functionality includes simulated die 
rolling and item information fetching from the DDOWiki.

Thanks to [DDO Audit](https://www.playeraudit.com/), LFM data is also available!

## Exceptions
The `Exceptions` cog provides centralized handling for errors during the bot's execution.

## Groups
The `Groups` cog provides an interface for managing, well, groups.

## Guild Features
The `Guild Features` cog provides an interface for managing special behaviors at the guild level.

## Howrse
The `Howrse` cog provides specific user-requested commands that represent a lack of capability in the current tag system.

## Images
The `Images` cog implements several image manipulation commands supported by Pillow.

## Lost Ark
The `Lost Ark` cog implements a quick-reference item auction calculator.

## Moderation
The `Moderation` cog contains methods related to the moderation of a Discord server. Supports advanced logging, such as 
message edit and deletion events.

## Reactions
The `Reactions` cog implements the concept of 'Reaction Roles.' Users can react to specified messages to receive 
corresponding roles within the guild.

## Runescape
The (Old School) `Runescape` cog implements commands related to fetching item market data and creating alerts for item 
price thresholds. 

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
The `Firestore` cog utilizes Google's Firestore database to log messages.

## MemeCoin
#### Deprecated: MemeCoin is no longer utilized. A better currency system may be implemented in the future.
The `MemeCoin` cog contains methods related to the fictitious currency created for the guild's 'Memes' channel. Users 
can award or revoke 'Meme Coins' at will by reacting to a message with a :heavy_check_mark: or :x: respectively.

## Music
#### Deprecated: Music will require a rewrite utilizing Wavelink >= 1.0.
The `Music` cog implements a fully-functional music player. The backend is driven by a 
[Lavalink Wrapper](https://github.com/PythonistaGuild/Wavelink) client, while the frontend is a modified version of the 
[PythonistaGuild's](https://github.com/PythonistaGuild/Wavelink/blob/master/examples/advanced.py) advanced 
implementation.

## Twitch
#### Deprecated: Twitch will require a rewrite utilizing TwitchIO >= 2.0.
The `Twitch` cog builds a Twitch chatbot into the main Discord bot and allows for executing Twitch commands from 
Discord.

## Audit
#### Deprecated: Audits needs a total overhaul and should be rewritten with the use Discord Components in mind.
The `Audit` cog contains methods for logging specified server events.

# Note
The addition of [mypy](http://mypy-lang.org/) for static type checking has introduced numerous `assert` statements into 
the codebase. Functionally, these asserts are used to narrow or influence types that are narrowed elsewhere, generally 
in areas that are more difficult to connect. A prime example is the `@guild_only()` decorator - ensuring that 
`ctx.guild` is never `None`, even if mypy can't detect that. While `assert` does have certain performance implications, 
since we're only asserting statements that should _always_ be true, these can be optimized away in production with the 
`-O` compiler flag.

mypy should be invoked with the following flags: `--explicit-package-bases --strict`