# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Python CLI tool that bulk uploads Slack-exported emoji images to Google Chat using the Google Chat API with OAuth 2.0 authentication.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run with emoji directory
python main.py emojis/

# Dry run (validation only, no upload)
python main.py emojis/ --dry-run

# Custom credentials/token paths
python main.py emojis/ --credentials my-creds.json --token my-token.pickle

# Adjust upload delay for rate limiting
python main.py emojis/ --delay 1.0
```

## Architecture

```
main.py              # CLI entry point, orchestrates validation and upload flow
src/
├── auth.py          # OAuth 2.0 authentication, token caching with pickle
├── validator.py     # Image validation (size, dimensions, format, naming)
└── emoji_uploader.py # Google Chat API client, upload with retry logic
```

**Flow**: `main.py` scans directory → `validator.py` validates each image → `auth.py` authenticates → `emoji_uploader.py` uploads valid emojis.

## Google Chat Emoji Constraints

- **File size**: ≤256KB
- **Dimensions**: 64-500px square
- **Formats**: PNG, JPEG, GIF
- **Naming**: lowercase letters, numbers, hyphens, underscores only (regex: `^[a-z0-9_-]+$`)

## Key Implementation Details

- Uses `chat.customemojis` OAuth scope
- Token cached in `token.pickle` (pickle format)
- Exponential backoff retry on 5xx errors, no retry on 4xx
- Existing emojis skipped by default (use `--no-skip-existing` to override)
- File name (without extension) becomes emoji name
