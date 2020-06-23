#!/usr/bin/env python3
# vim: set expandtab tabstop=4 shiftwidth=4:

# Copyright (c) 2020 CJ Kucera (cj@apocalyptech.com)
# 
# This software is provided 'as-is', without any express or implied warranty.
# In no event will the authors be held liable for any damages arising from
# the use of this software.
# 
# Permission is granted to anyone to use this software for any purpose,
# including commercial applications, and to alter it and redistribute it
# freely, subject to the following restrictions:
# 
# 1. The origin of this software must not be misrepresented; you must not
#    claim that you wrote the original software. If you use this software in a
#    product, an acknowledgment in the product documentation would be
#    appreciated but is not required.
# 
# 2. Altered source versions must be plainly marked as such, and must not be
#    misrepresented as being the original software.
# 
# 3. This notice may not be removed or altered from any source distribution.

import bl3save
import argparse
import itertools
from bl3save.bl3profile import BL3Profile

def main():

    # Arguments
    parser = argparse.ArgumentParser(
            description='Borderlands 3 Profile Info Dumper v{}'.format(bl3save.__version__),
            )

    parser.add_argument('-V', '--version',
            action='version',
            version='BL3 CLI SaveEdit v{}'.format(bl3save.__version__),
            )

    parser.add_argument('-v', '--verbose',
            action='store_true',
            help='Show all available information',
            )

    parser.add_argument('-i', '--items',
            action='store_true',
            help='Show inventory items',
            )

    parser.add_argument('filename',
            help='Filename to process',
            )

    args = parser.parse_args()

    # Load the profile
    prof = BL3Profile(args.filename)

    # Golden Keys
    print('Golden Keys: {}'.format(prof.get_golden_keys()))

    # Guardian Rank
    print('Guardian Rank: {}'.format(prof.get_guardian_rank()))
    print('Available GR Tokens: {}'.format(prof.get_guardian_rank_tokens()))

    # SDUs
    sdus = prof.get_sdus_with_max(True)
    if len(sdus) == 0:
        print('No SDUs Purchased')
    else:
        print('SDUs:')
        for sdu, (count, max_sdus) in sdus.items():
            print(' - {}: {}/{}'.format(sdu, count, max_sdus))

    # Bank Items
    bank_items = prof.get_bank_items()
    print('Items in bank: {}'.format(len(bank_items)))
    if args.verbose or args.items:
        to_report = []
        for item in bank_items:
            if item.eng_name:
                to_report.append(' - {} ({}): {}'.format(item.eng_name, item.get_level_eng(), item.get_serial_base64()))
            else:
                to_report.append(' - unknown item: {}'.format(item.get_serial_base64()))
        for line in sorted(to_report):
            print(line)

    # Lost Loot Items
    lostloot_items = prof.get_lostloot_items()
    print('Items in Lost Loot machine: {}'.format(len(lostloot_items)))
    if args.verbose or args.items:
        to_report = []
        for item in lostloot_items:
            if item.eng_name:
                to_report.append(' - {} ({}): {}'.format(item.eng_name, item.get_level_eng(), item.get_serial_base64()))
            else:
                to_report.append(' - unknown item: {}'.format(item.get_serial_base64()))
        for line in sorted(to_report):
            print(line)

    # Various customizations
    for (label, current, maxcount) in [
            ('Character Skins', prof.get_char_skins(), prof.get_char_skins_total()),
            ('Character Heads', prof.get_char_heads(), prof.get_char_heads_total()),
            ('ECHO Themes', prof.get_echo_themes(), prof.get_echo_themes_total()),
            ('Emotes', prof.get_emotes(), prof.get_emotes_total()),
            ('Room Decorations', prof.get_room_decos(), prof.get_room_decos_total()),
            ('Weapon Skins', prof.get_weapon_skins(), prof.get_weapon_skins_total()),
            ('Weapon Trinkets', prof.get_weapon_trinkets(), prof.get_weapon_trinkets_total()),
            ]:
        print('{} Unlocked: {}/{}'.format(label, len(current), maxcount))

if __name__ == '__main__':
    main()
