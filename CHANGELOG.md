# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

**Types of Changes**
- Features
- Internal
- Issues

## Unreleased
### Features
### Internal
### Issues

# 2.7.2
### Internal
* Remove logging from `v2.7.1` -> `command` is `None` when prefix is used without a valid command name

# 2.7.1
### Internal
* Add logging to identify cases where `on_command_error->command` is `None`

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
* Bump discord.py version to 2.1.0

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
* Convert LostArk::Split to AppCommand

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
* Fix Admin -> Git Pull not utilizing `safe_send`

## 2.0.0
### Internal
* Utilize SQL migrations for database management
* Utilize context managers for aiohttp sessions and aiosqlite connections
* Bump Python version to 3.9.2
* Separate discord.py and bot logging
* Bump discord.py version to 2.0.1

## 1.0.0
* Base `discord.ext.commands` Bot