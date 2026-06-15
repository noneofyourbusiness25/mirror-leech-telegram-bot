import re
from os import path as ospath
from os import rename
from aiofiles.os import rename as aiorename
import asyncio

def clean_filename(filename):
    # Match common site urls in brackets or start of name, e.g., www.1TamilMV.cards -
    # Match group tags like -VegaMovies or @GroupName
    clean_regex = r"(?i)(?:\[?www\.[a-zA-Z0-9-]+\.[a-zA-Z]+\]?(?: - | )?)|(?:-?[a-zA-Z0-9]*movies\b)|(?:@[a-zA-Z0-9_]+)"
    cleaned = re.sub(clean_regex, "", filename).strip(" -_")

    # Fix .mkv.001 to .part001.mkv
    match = re.search(r"(\.[a-zA-Z0-9]+)\.([0-9]+)$", cleaned)
    if match:
        ext = match.group(1)
        part = match.group(2)
        cleaned = re.sub(r"(\.[a-zA-Z0-9]+)\.([0-9]+)$", f".part{part}{ext}", cleaned)

    return cleaned

print(clean_filename("www.1TamilMV.cards - The Deep (1977) BluRay - 1080p .mkv.002"))
