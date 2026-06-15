import re

filenames = [
    "www.1TamilMV.cards - The Deep (1977) BluRay - 1080p .mkv.002",
    "Movie_Name_2023_MSub-VegaMovies.mkv",
    "Movie_Name_2023_@SomeGroup.mkv",
]

clean_regex = r"(?i)(?:\[?www\.[a-zA-Z0-9-]+\.[a-zA-Z]+\]?(?: - | )?)|(?:-?[a-zA-Z0-9]*movies\b)|(?:@[a-zA-Z0-9_]+)"

for f in filenames:
    print(f"Original: {f}")

    cleaned = re.sub(clean_regex, "", f).strip(" -_")

    # Fix .mkv.001 to .part001.mkv
    match = re.search(r"(\.[a-zA-Z0-9]+)\.([0-9]+)$", cleaned)
    if match:
        ext = match.group(1)
        part = match.group(2)
        cleaned = re.sub(r"(\.[a-zA-Z0-9]+)\.([0-9]+)$", f".part{part}{ext}", cleaned)

    print(f"Cleaned:  {cleaned}\n")
