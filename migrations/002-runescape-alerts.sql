-- Revises: 001
-- Creation Date: 2023-01-04 06:58:17 UTC
-- Reason: Add Runescape Alerts

-- instant buy goes below target low
-- instant sell goes above target high

CREATE TABLE IF NOT EXISTS "RUNESCAPE_ALERTS" (
    "OWNER_ID"          INTEGER NOT NULL,
    "CREATED"           INTEGER NOT NULL,
    "ITEM_ID"           INTEGER NOT NULL,
    "INITIAL_LOW"       INTEGER,
    "INITIAL_HIGH"      INTEGER,
    "TARGET_LOW"        INTEGER,
    "TARGET_HIGH"       INTEGER,
    "FREQUENCY"         INTEGER,
    "MAXIMUM_ALERTS"    INTEGER,
    "LAST_ALERT"        INTEGER,
    PRIMARY KEY("OWNER_ID", "ITEM_ID")
);

PRAGMA user_version = 2;