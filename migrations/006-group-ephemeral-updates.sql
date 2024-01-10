-- Revises: 006
-- Creation Date: 2024-01-10 03:40:40 UTC
-- Reason: Add EphemeralUpdates Column to Groups

ALTER TABLE "GROUPS" ADD COLUMN "EPHEMERAL_UPDATES" INT NOT NULL DEFAULT 1;

PRAGMA user_version = 6;