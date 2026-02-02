# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

**Types of Changes**
- Added (New external facing functionality)
- Removed (Removed external facing functionality)
- Internal (Added or removed, generally architecture or infrastructure)
- Issues (internal or external)
- Security (internal)

## Unreleased
### Added
### Removed
### Internal
- Bump Python version to `3.14.2`
- Update CHANGELOG types
### Issues
### Security

## 2.19.0
### Features
- `Runescape`
  - Enhance autocomplete descriptions for user-provided values
  - Update `RunescapeHerbComparison` to include Huasca
  - Update user-facing instances to properly capitalize 'RuneScape'
- `GuildFeature`
  - Add support for alternative Twitter embeds (via 'fixupx.com')
  - Improve modification dialogue output and make output non-ephemeral
### Internal
- Autocomplete
  - Switch from `fuzzywuzzy` to `RapidFuzz` for increased performance
  - Improve match quality by prioritizing `token_set` > `partial_token_sort` > `QRatio`, followed by string length delta
  - Further improve autocomplete performance for `Runescape` by storing previously computed autocomplete results
- Add `ScopedDebugFilter` to allow for toggleable debug logs
- Network Client
  - Create `NetworkClient` to allow for centralized error handling, ratelimiting, and more accurate typing
  - Migrate existing `network_request` usages to `NetworkClient`
- Overhaul imports to only import types used for type-hinting when type checking
### Issues
- Fix `RunescapeHerbComparison` using grimy values for min/max comparisons instead of grimy and clean
- Update `Admin::exec` to strip non-printable characters from `Message.content` (thanks Discord)

## 2.18.5
### Internal
- Refactor `Runescape::query_mapping_data` to handle mapping exceptions at the individual item level, rather than query level

## 2.18.4
### Internal
- Bump discord.py to `2.5.2` (discord.Member.MemberFlags.guest)
### Issues
- Prevent `VoiceRoles::on_voice_state_update` from attempting to add voice roles to guests

## 2.18.3
### Internal
- Enhance `Bot::on_error` logging to include traceback information where available
- Update `Admin` cog private event notifications to use `on_message` to avoid `Forbidden (error code: 40058)` issues with `on_thread_create`

## 2.18.2
### Internal
- Add private event notifications to `Admin` cog

## 2.18.1
### Internal
- `Admin`
  - Allow forbidden characters in `StringConverter::ExtensionName`
  - Add `cog_unload` to clean up `logging_line_break` on reload
- Suppress `ExtensionError` from production error reporting
- Add additional context to `VoiceRoles::on_voice_state_update::Forbidden`

## 2.18.0
### Features
- Enhance `Group` autocomplete descriptions with owner name and member count
### Internal
- Create `mypy` GitHub workflow
- Miscellaneous spelling fixes

## 2.17.0
### Features
- `Group` group names are now case-insensitive
- `Utility::UserInfo` now considers whether the user has a global name
### Internal
- `Tags` and `Groups` now reject problematic (Discord) characters in their names
- Improved logging for existing `Admin` commands
- Autocomplete fuzzy matching now uses `casefolded` strings instead of `lowered` strings

## 2.16.2
### Issues
- `Moderation::Purge`
  - Prevent edge case where a confirmation prompt coroutine was created and never used
  - Prevent zero or negative limit values

## 2.16.1
### Features
* `Runescape`
  - Increase default herb patches for Varlamore 
  - Dramatically increase max herb patches on herb profitability calculation

## 2.16.0
### Features
* Add Herb Profitability Comparison to `Runescape` Cog

## 2.15.3
### Internal
* Adjust `FileLoggingFormatter` to strip unwanted information post-format

## 2.15.2
### Issues
* Restore `cog_load` for `Groups`

## 2.15.1
### Internal
* Dump context information during file logging
### Issues
* Include traceback information during file logging

## 2.15.0
### Features
* Remove `Audit` cog
### Internal
* `Groups`
  - Checks
    - Refactor common checks into reusable functions
    - Switch to `InvocationCheckFailure` where appropriate
  - Implement immediate group updates during listeners; remove synchronization task
* mypy
  - Bump version to `1.8.0`
  - Support `--strict` type checking
* Replace license format to avoid future updates
* Remove tracebacks from reconnect errors from stream logging handlers

## 2.14.1
### Issues
* Fix `Groups::kick` removing invoker from cache rather than kickee

## 2.14.0
### Features
* `Groups` Cog v2
  - Added `ephemeral` group updates
  - Added `kick` and `transfer` commands
  - Added support for member `on_join` and `on_leave`
### Internal
* Confirmation for mutating SQL statements in PROD
* Expand list of core updates that prevent automatic reloading
### Issues
* Handle `TimeoutError` in fetch tasks

## 2.13.0
### Features
* Add `Groups` Cog
### Internal
* Internally limit autocomplete choice lists to 25

## 2.12.3
### Internal
* Bump Pillow to `10.1.0` (CVE-2023-44271)

## 2.12.2
### Features
* Add `all` option to `Moderation::Purge`
* Add hardcoded `Howrse::Horsemen` commands until embed support is added to `Tags`
### Internal
* Add custom `guild_only` check with guild_id allowances

## 2.12.1
### Features
* Add hardcoded `Howrse::Silverwood` commands until embed support is added to `Tags`

## 2.12.0
### Features
* Add `GuildFeature::TAG_DIRECT_INVOKE`
* Reduce minimum `Tag` name length to 2 characters, down from 3

### Internal
* Default existing `Tags` to `AllowedMentions::None`
* Add internal support for more granular `AllowedMentions` for `Tags` in the future

## 2.11.0
### Features
* Add `GuildFeatures` Cog

### Internal
* Bump mypy version to 1.3.0

## 2.10.4
### Internal
* Bump discord.py version to 2.3.1

# 2.10.3
### Features
* Improve descriptors for default and current parameters for `Runescape` commands

# 2.10.2
### Issues
* Fix autocomplete for duplicate parameters in `Runescape` Cog

# 2.10.1
### Features
* Full autocomplete support for `Runescape` commands

# 2.10.0
### Features
* Add Grand Exchange Market Alerts to `Runescape` Cog

### Internal
* Add custom implementation for Expiring Dictionary; drop untyped third-party dependency

### Issues
* Add `VoiceRoles::on_voice_state_update` permissions check for role updates

# 2.9.1
### Issues
* Check for `manage_roles` permission in `VoiceRoles::on_voice_state_update`

# 2.9.0
### Internal
* Cache Frequently Accessed Database Tables in Memory
* Reduce `VoiceRoles::on_voice_state_update` role update API calls to 1 with `Member.edit`

# 2.8.2
### Internal
* Add Fuzzy Autocomplete Searching

# 2.8.1
### Internal
* Revert Global Database Connection

# 2.8.0
### Internal
* Report exceptions intercepted via `Client::on_error` to Reporting Dashboard
* Add `Runescape` Cog

# 2.7.0
### Internal
* Add mypy type checking to the project

# 2.6.3
### Issues
* Fix prefix iteration for Raspberry Pi

## 2.6.2
### Internal
* Add typing to database retrieval queries

### Issues
* Fix several `VoiceRole` prompts

## 2.6.1
### Internal
* Bump Pillow to `9.2.0` (CVE-2022-45198)

## 2.6.0
### Internal
* Replace manual datetime localization with Discord-native datetime markdown

## 2.5.0
### Internal
* Add Dynamic Cooldowns to commands with network requests

## 2.4.2
### Internal
* Reduce NetworkRequest exception logging

## 2.4.1
### Internal
* Refactor Firebase Error Reporting to be accessible globally

## 2.4.0
### Features
* Overhaul `Yoink` commands to use a new `EmojiManager` class

### Internal
* Insert logging line break at the start of every day
* Bump discord.py version to `2.1.0`

### Issues
* Fix `avatar_url` -> `avatar.url` in Utility::UserInfo

## 2.3.2
### Issues
* Calculate actual limits for animated and static emojis during yoink commands

## 2.3.1
### Internal
* Implement Exponential Backoff for DDOAudit Network Requests

## 2.3.0
### Features
* Convert `LostArk::Split` to AppCommand

## 2.2.2
### Issues
* Add NoResumeFilter to discord.py's StreamHandler during setup instead of logger after setup

## 2.2.1
### Internal
* Swap discord.py and DreamBot logging colors
* Add RESUMED filter to discord.py logger

## 2.2.0
### Internal
* Remove only 'held' roles in `on_voice_state_update` rather than all possible roles

## 2.1.0
### Internal
* Add file logging handlers

## 2.0.1
### Issues
* Fix `Admin::git_pull` not utilizing `safe_send`

## 2.0.0
### Internal
* Utilize SQL migrations for database management
* Utilize context managers for aiohttp sessions and aiosqlite connections
* Bump Python version to `3.9.2`
* Separate discord.py and bot logging
* Bump discord.py version to `2.0.1`

## 1.0.0
* Base `discord.ext.commands` Bot