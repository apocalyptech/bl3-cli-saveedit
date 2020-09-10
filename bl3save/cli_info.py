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
from bl3save.bl3save import BL3Save

def main():

    # Arguments
    parser = argparse.ArgumentParser(
            description='Borderlands 3 Savegame Info Dumper v{}'.format(bl3save.__version__),
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

    parser.add_argument('--all-missions',
            dest='all_missions',
            action='store_true',
            help='Show all missions')

    parser.add_argument('--all-challenges',
            dest='all_challenges',
            action='store_true',
            help='Show all challenges')

    parser.add_argument('--fast-travel',
            dest='fast_travel',
            action='store_true',
            help='Show all unlocked Fast Travel stations')

    parser.add_argument('filename',
            help='Filename to process',
            )

    args = parser.parse_args()

    # Load the save
    save = BL3Save(args.filename)

    # Character name
    print('Character: {}'.format(save.get_char_name()))

    # Savegame ID
    print('Savegame ID: {}'.format(save.get_savegame_id()))

    # Savegame GUID
    print('Savegame GUID: {}'.format(save.get_savegame_guid()))

    # Pet Names
    petnames = save.get_pet_names(True)
    if len(petnames) > 0:
        for (pet_type, pet_name) in petnames.items():
            print(' - {} Name: {}'.format(pet_type, pet_name))

    # Class
    print('Player Class: {}'.format(save.get_class(True)))

    # XP/Level
    print('XP: {}'.format(save.get_xp()))
    print('Level: {}'.format(save.get_level()))
    print('Guardian Rank: {}'.format(save.get_guardian_rank()))

    # Currencies
    print('Money: {}'.format(save.get_money()))
    print('Eridium: {}'.format(save.get_eridium()))

    # Playthroughs
    print('Playthroughs Completed: {}'.format(save.get_playthroughs_completed()))

    # Playthrough-specific Data
    for pt, (mayhem,
                mayhem_seed,
                mapname,
                stations,
                active_missions,
                completed_missions) in enumerate(itertools.zip_longest(
            save.get_pt_mayhem_levels(),
            save.get_pt_mayhem_seeds(),
            save.get_pt_last_maps(True),
            save.get_pt_active_ft_station_lists(),
            save.get_pt_active_mission_lists(True),
            save.get_pt_completed_mission_lists(True),
            )):

        print('Playthrough {} Info:'.format(pt+1))

        # Mayhem
        if mayhem is not None:
            print(' - Mayhem Level: {}'.format(mayhem))
        if mayhem_seed is not None:
            print(' - Mayhem Random Seed: {}'.format(mayhem_seed))

        # Map
        if mapname is not None:
            print(' - In Map: {}'.format(mapname))

        # FT Stations
        if args.verbose or args.fast_travel:
            if stations is not None:
                if len(stations) == 0:
                    print(' - No Active Fast Travel Stations')
                else:
                    print(' - Active Fast Travel Stations:'.format(pt+1))
                    for station in stations:
                        print('   - {}'.format(station))

        # Missions
        if active_missions is not None:
            if len(active_missions) == 0:
                print(' - No Active Missions')
            else:
                print(' - Active Missions:')
                for mission in sorted(active_missions):
                    print('   - {}'.format(mission))

        # Completed mission count
        if completed_missions is not None:
            print(' - Missions completed: {}'.format(len(completed_missions)))

            # Show all missions if need be
            if args.verbose or args.all_missions:
                for mission in sorted(completed_missions):
                    print('   - {}'.format(mission))

            # "Important" missions - I'm torn as to whether or not this kind of thing
            # should be in bl3save.py itself, or at least some constants in __init__.py
            mission_set = set(completed_missions)
            importants = []
            if 'Divine Retribution' in mission_set:
                importants.append('Main Game')
            if 'All Bets Off' in mission_set:
                importants.append('DLC1 - Moxxi\'s Heist of the Handsome Jackpot')
            if 'The Call of Gythian' in mission_set:
                importants.append('DLC2 - Guns, Love, and Tentacles')
            if 'Riding to Ruin' in mission_set:
                importants.append('DLC3 - Bounty of Blood')
            if 'Locus of Rage' in mission_set:
                importants.append('DLC4 - Psycho Krieg and the Fantastic Fustercluck')
            if len(importants) > 0:
                print(' - Mission Milestones:')
                for important in importants:
                    print('   - Finished: {}'.format(important))

    # Inventory Slots that we care about
    print('Unlockable Inventory Slots:')
    for slot in [bl3save.WEAPON3, bl3save.WEAPON4, bl3save.COM, bl3save.ARTIFACT]:
        print(' - {}: {}'.format(
            bl3save.slot_to_eng[slot],
            save.get_equip_slot(slot).enabled(),
            ))

    # Inventory
    if args.verbose or args.items:
        items = save.get_items()
        if len(items) == 0:
            print('Nothing in Inventory')
        else:
            print('Inventory:')
            to_report = []
            for item in items:
                if item.eng_name:
                    to_report.append(' - {} ({}): {}'.format(item.eng_name, item.get_level_eng(), item.get_serial_base64()))
                else:
                    to_report.append(' - unknown item: {}'.format(item.get_serial_base64()))
            for line in sorted(to_report):
                print(line)

    # Equipped Items
    if args.verbose or args.items:
        items = save.get_equipped_items(True)
        if any(items.values()):
            print('Equipped Items:')
            to_report = []
            for (slot, item) in items.items():
                if item:
                    if item.eng_name:
                        to_report.append(' - {}: {} ({}): {}'.format(slot, item.eng_name, item.get_level_eng(), item.get_serial_base64()))
                    else:
                        to_report.append(' - {}: unknown item: {}'.format(slot, item.get_serial_base64()))
            for line in sorted(to_report):
                print(line)
        else:
            print('No Equipped Items')

    # SDUs
    sdus = save.get_sdus_with_max(True)
    if len(sdus) == 0:
        print('No SDUs Purchased')
    else:
        print('SDUs:')
        for sdu, (count, max_sdus) in sdus.items():
            print(' - {}: {}/{}'.format(sdu, count, max_sdus))

    # Ammo
    print('Ammo Pools:')
    for ammo, count in save.get_ammo_counts(True).items():
        print(' - {}: {}'.format(ammo, count))

    # Challenges
    print('Challenges we care about:')
    for challenge, status in save.get_interesting_challenges(True).items():
        print(' - {}: {}'.format(challenge, status))

    # "raw" Challenges
    if args.verbose or args.all_challenges:
        print('All Challenges:')
        for challenge in save.get_all_challenges_raw():
            print(' - {} (Completed: {}, Counter: {}, Progress: {})'.format(
                challenge.challenge_class_path,
                challenge.currently_completed,
                challenge.progress_counter,
                challenge.completed_progress_level,
                ))

    # Vehicle unlocks
    print('Unlocked Vehicle Parts:')
    for vehicle, chassis_count in save.get_vehicle_chassis_counts().items():
        eng = bl3save.vehicle_to_eng[vehicle]
        print(' - {} - Chassis (wheels): {}/{}, Parts: {}/{}, Skins: {}/{}'.format(
            eng,
            chassis_count, len(bl3save.vehicle_chassis[vehicle]),
            save.get_vehicle_part_count(vehicle), len(bl3save.vehicle_parts[vehicle]),
            save.get_vehicle_skin_count(vehicle), len(bl3save.vehicle_skins[vehicle]),
            ))

if __name__ == '__main__':
    main()
