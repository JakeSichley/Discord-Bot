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