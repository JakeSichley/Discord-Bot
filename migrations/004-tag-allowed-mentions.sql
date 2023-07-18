-- Revises: 003
-- Creation Date: 2023-07-17 23:07:27 UTC
-- Reason: Add Guild Features

ALTER TABLE "TAGS" ADD COLUMN "ALLOWED_MENTIONS" INT NOT NULL DEFAULT 0;

PRAGMA user_version = 4;