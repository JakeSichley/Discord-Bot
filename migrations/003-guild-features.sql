-- Revises: 002
-- Creation Date: 2023-07-14 02:42:09 UTC
-- Reason: Add Guild Features

CREATE TABLE IF NOT EXISTS "GUILD_FEATURES" (
    "GUILD_ID"          INTEGER NOT NULL,
    "FEATURES"          INTEGER NOT NULL,
    PRIMARY KEY("GUILD_ID")
);

PRAGMA user_version = 3;