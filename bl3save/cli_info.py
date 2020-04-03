#!/usr/bin/env python
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

    parser.add_argument('-v', '--verbose',
            action='store_true',
            help='Show all available information',
            )

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

    # Currencies
    print('Money: {}'.format(save.get_money()))
    print('Eridium: {}'.format(save.get_eridium()))

    # Playthroughs
    print('Playthroughs Completed: {}'.format(save.get_playthroughs_completed()))

    # Playthrough-specific Data
    for pt, (mayhem, mapname, stations, missions, mission_count) in enumerate(itertools.zip_longest(
            save.get_pt_mayhem_levels(),
            save.get_pt_last_maps(True),
            save.get_pt_active_ft_station_lists(),
            save.get_pt_active_mission_lists(True),
            save.get_pt_completed_mission_counts(),
            )):

        print('Playthrough {} Info:'.format(pt+1))

        # Mayhem
        if mayhem is not None:
            print(' - Mayhem Level: {}'.format(mayhem))

        # Map
        if mapname is not None:
            print(' - In Map: {}'.format(mapname))

        # FT Stations
        if args.verbose:
            if stations is not None:
                if len(stations) == 0:
                    print(' - No Active FT Stations')
                else:
                    print(' - Active FT Stations:'.format(pt+1))
                    for station in stations:
                        print('   - {}'.format(station))

        # Missions
        if missions is not None:
            if len(missions) == 0:
                print(' - No Active Missions')
            else:
                print(' - Active Missions:')
                for mission in sorted(missions):
                    print('   - {}'.format(mission))

        # Completed mission count
        if mission_count is not None:
            print(' - Missions completed: {}'.format(mission_count))

    # Inventory Slots that we care about
    print('Unlockable Inventory Slots:')
    for slot in [bl3save.WEAPON3, bl3save.WEAPON4, bl3save.COM, bl3save.ARTIFACT]:
        print(' - {}: {}'.format(
            bl3save.slot_to_eng[slot],
            save.get_equip_slot(slot).enabled(),
            ))

    # Inventory
    if args.verbose:
        items = save.get_items()
        if len(items) == 0:
            print('Nothing in Inventory')
        else:
            print('Inventory:')
            for item in items:
                print(' - {}'.format(item.get_serial_base64()))

    # Equipped Items
    if args.verbose:
        items = save.get_equipped_items(True)
        if any(items.values()):
            print('Equipped Items:')
            for (slot, item) in items.items():
                if item:
                    print(' - {}: {}'.format(slot, item.get_serial_base64()))
        else:
            print('No Equipped Items')

    # SDUs
    sdus = save.get_sdus(True)
    if len(sdus) == 0:
        print('No SDUs Purchased')
    else:
        print('SDUs:')
        for sdu, count in sdus.items():
            print(' - {}: {}'.format(sdu, count))

    # Ammo
    print('Ammo Pools:')
    for ammo, count in save.get_ammo_counts(True).items():
        print(' - {}: {}'.format(ammo, count))

    # Challenges
    print('Challenges we care about:')
    for challenge, status in save.get_interesting_challenges(True).items():
        print(' - {}: {}'.format(challenge, status))

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
