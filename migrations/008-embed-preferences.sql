-- Revises: 007
-- Creation Date: 2026-05-12 08:38:43 UTC
-- Reason: Add Original Embed Deletion Preference Support

CREATE TABLE IF NOT EXISTS "EMBED_PREFERENCES" (
    "GUILD_ID"              INTEGER NOT NULL,
    "MEMBER_ID"             INTEGER NOT NULL,
    "DELETE_ORIGINAL"       INTEGER NOT NULL,  -- Boolean
    PRIMARY KEY("GUILD_ID", "MEMBER_ID")
);

PRAGMA user_version = 8;