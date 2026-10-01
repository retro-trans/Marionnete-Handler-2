"""Stable translation order: 560 menu records, then 233 other game records."""
import json
from inspect_disc_text import ROOT


def game_rows():
    inventory = json.loads((ROOT / 'work/ui/text_inventory.json').read_text(encoding='utf-8'))
    rows = [row for row in inventory['entries'] if row['file'] == '/1ST_READ.BIN']
    menus = sorted((row for row in rows if row['category'] == 'menus_prompts_help_and_descriptions'),
                   key=lambda row: row['file_offset'])
    other = sorted((row for row in rows if row['category'] != 'menus_prompts_help_and_descriptions'),
                   key=lambda row: row['file_offset'])
    assert len(menus) == 560 and len(other) == 233
    return menus + other
