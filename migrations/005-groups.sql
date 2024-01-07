-- Revises: 004
-- Creation Date: 2024-01-06 20:17:05 UTC
-- Reason: Add Groups

CREATE TABLE IF NOT EXISTS "GROUPS" (
    "GUILD_ID"          INTEGER NOT NULL,
    "OWNER_ID"          INTEGER NOT NULL,
    "CREATED"           INTEGER NOT NULL,
    "GROUP_NAME"        TEXT NOT NULL,
    "MAX_MEMBERS"       INTEGER,
    PRIMARY KEY("GROUP_NAME")
);

CREATE TABLE IF NOT EXISTS "GROUP_MEMBERS" (
    "MEMBER_ID"         INTEGER NOT NULL,
    "JOINED"            INTEGER NOT NULL,
    "GROUP_NAME"        TEXT NOT NULL,
    FOREIGN KEY("GROUP_NAME") REFERENCES GROUPS("GROUP_NAME") ON DELETE CASCADE,
    PRIMARY KEY("GROUP_NAME", "MEMBER_ID")
);

PRAGMA user_version = 5;