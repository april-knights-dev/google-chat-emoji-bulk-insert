#!/usr/bin/env python3
"""
One-time script to organize failed upload files based on previous upload log.
"""

import shutil
from pathlib import Path

# Failed emojis from the upload log (42 total)
FAILED_EMOJIS = {
    # Invalid payload (GIF encoding issue)
    "invalid_payload": [
        "abby_freeze",
        "among_us_space_float",
        "apex_bronze2",
        "apex_diamond2",
        "apex_gold2",
        "apex_master2",
        "apex_platinum2",
        "apex_predator2",
        "apex_silver2",
        "cattyping",
        "confused_dog",
        "dogrun1",
        "dogrun2",
        "dogrun3",
    ],
    # Reserved or blocked names - 10 files
    "reserved_name": [
        "atom",
        "baka",
        "biohazard",
        "jojo",
        "korona",
        "skip",
        "sanka",
        "oko",
        "ooi",
        "ui",
    ],
    # Name too long - 1 file
    "name_too_long": [
        "babababababaeowioi-bebebebebebebebebeebeeeebeebebebee",
    ],
    # Invalid name (trailing special chars, single letter) - 10 files
    "invalid_name_api": [
        "are-_",
        "kaneda-_",
        "suge-_",
        "dareda__",
        "e",
        "n",
        "p",
        "s",
        "w",
        "y",
    ],
}

# Category descriptions
DESCRIPTIONS = {
    "invalid_payload": "Invalid payload (GIF encoding issue)",
    "reserved_name": "Reserved or blocked name",
    "name_too_long": "Name too long",
    "invalid_name_api": "Invalid name (API rejected)",
}


def main():
    emoji_dir = Path("emojis")
    output_dir = Path("errors/upload_errors")
    output_dir.mkdir(parents=True, exist_ok=True)

    total_copied = 0

    for category, emoji_names in FAILED_EMOJIS.items():
        category_dir = output_dir / category
        category_dir.mkdir(exist_ok=True)

        copied = 0
        for name in emoji_names:
            # Try different extensions
            for ext in [".gif", ".png", ".jpg", ".jpeg"]:
                src = emoji_dir / f"{name}{ext}"
                if src.exists():
                    dst = category_dir / src.name
                    if not dst.exists():
                        shutil.copy2(src, dst)
                        copied += 1
                        total_copied += 1
                    break
            else:
                print(f"Warning: File not found for {name}")

        desc = DESCRIPTIONS.get(category, category)
        print(f"{category}/ ({copied} files) - {desc}")

    print(f"\nTotal: {total_copied} files organized into {output_dir}")


if __name__ == "__main__":
    main()
