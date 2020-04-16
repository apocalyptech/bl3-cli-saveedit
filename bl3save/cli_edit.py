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

import os
import sys
import bl3save
import argparse
from bl3save.bl3save import BL3Save

class DictAction(argparse.Action):
    """
    Custom argparse action to put list-like arguments into
    a dict (where the value will be True) rather than a list.
    This is probably implemented fairly shoddily.
    """
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        """
        Constructor, taken right from https://docs.python.org/2.7/library/argparse.html#action
        """
        if nargs is not None:
            raise ValueError('nargs is not allowed')
        super(DictAction, self).__init__(option_strings, dest, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        """
        Actually setting a value.  Forces the attr into a dict if it isn't already.
        """
        arg_value = getattr(namespace, self.dest)
        if not isinstance(arg_value, dict):
            arg_value = {}
        arg_value[values] = True
        setattr(namespace, self.dest, arg_value)

def main():

    # Set up args
    parser = argparse.ArgumentParser(
            description='Borderlands 3 CLI Savegame Editor v{} (PC Only)'.format(bl3save.__version__),
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            epilog="""
                The default output type of "savegame" will output theoretically-valid
                savegames which can be loaded into BL3.  The output type "protobuf"
                will save out the extracted, decrypted protobufs.  These protobufs
                CANNOT be read back into the file using this editor, so that's a
                write-only operation.  The output type "items" will output a text
                file containing base64-encoded representations of the user's
                inventory.  These can be read back in using the -i/--import-items
                option.  Note that these are NOT the same as the item strings used
                by the BL3 Memory Editor.
            """
            )

    parser.add_argument('-V', '--version',
            action='version',
            version='BL3 CLI SaveEdit v{}'.format(bl3save.__version__),
            )

    parser.add_argument('-o', '--output',
            choices=['savegame', 'protobuf', 'json', 'items'],
            default='savegame',
            help='Output file format',
            )

    parser.add_argument('-f', '--force',
            action='store_true',
            help='Force output file to overwrite',
            )

    parser.add_argument('-q', '--quiet',
            action='store_true',
            help='Supress all non-essential output')

    # Actual changes the user can request
    parser.add_argument('--name',
            type=str,
            help='Set the name of the character',
            )

    parser.add_argument('--save-game-id',
            dest='save_game_id',
            type=int,
            help='Set the save game slot ID (possibly not actually ever needed)',
            )

    levelgroup = parser.add_mutually_exclusive_group()

    levelgroup.add_argument('--level',
            type=int,
            help='Set the character to this level (from 1 to {})'.format(bl3save.max_level),
            )

    levelgroup.add_argument('--level-max',
            dest='level_max',
            action='store_true',
            help='Set the character to max level ({})'.format(bl3save.max_level),
            )

    itemlevelgroup = parser.add_mutually_exclusive_group()

    itemlevelgroup.add_argument('--items-to-char',
            dest='items_to_char',
            action='store_true',
            help='Set all inventory items to the level of the character')

    itemlevelgroup.add_argument('--item-levels',
            dest='item_levels',
            type=int,
            help='Set all inventory items to the specified level')

    parser.add_argument('--mayhem',
            type=int,
            choices=range(5),
            help='Set the mayhem mode for all playthroughs (mostly useful for Normal mode)',
            )

    parser.add_argument('--money',
            type=int,
            help='Set money value',
            )

    parser.add_argument('--eridium',
            type=int,
            help='Set Eridium value',
            )

    unlock_choices = [
            'ammo', 'backpack',
            'analyzer', 'resonator',
            'gunslots', 'artifactslot', 'comslot', 'allslots',
            'tvhm',
            'vehicles', 'vehicleskins',
            ]
    parser.add_argument('--unlock',
            action=DictAction,
            choices=unlock_choices + ['all'],
            default={},
            help='Game features to unlock',
            )

    tvhmgroup = parser.add_mutually_exclusive_group()

    tvhmgroup.add_argument('--copy-nvhm',
            dest='copy_nvhm',
            action='store_true',
            help='Copies NVHM/Normal state to TVHM',
            )

    tvhmgroup.add_argument('--unfinish-nvhm',
            dest='unfinish_nvhm',
            action='store_true',
            help='"Un-finishes" the game: remove all TVHM data and set Playthrough 1 to Not Completed',
            )

    parser.add_argument('-i', '--import-items',
            dest='import_items',
            type=str,
            help='Import items from file',
            )

    parser.add_argument('--allow-fabricator',
            dest='allow_fabricator',
            action='store_true',
            help='Allow importing Fabricator when importing items from file')

    # Positional args
    parser.add_argument('input_filename',
            help='Input filename',
            )

    parser.add_argument('output_filename',
            help='Output filename',
            )

    # Parse args
    args = parser.parse_args()
    if args.level is not None and (args.level < 1 or args.level > bl3save.max_level):
        raise argparse.ArgumentTypeError('Valid level range is 1 through {}'.format(bl3save.max_level))

    # Expand any of our "all" unlock actions
    if 'all' in args.unlock:
        args.unlock = {k: True for k in unlock_choices}
    elif 'allslots' in args.unlock:
        args.unlock['gunslots'] = True
        args.unlock['artifactslot'] = True
        args.unlock['comslot'] = True

    # Make sure we're not trying to clear and unlock THVM at the same time
    if 'tvhm' in args.unlock and args.unfinish_nvhm:
        raise argparse.ArgumentTypeError('Cannot both unlock TVHM and un-finish NVHM')

    # Set max level arg
    if args.level_max:
        args.level = bl3save.max_level

    # Check item level.  The max storeable in the serial number is 127, but the
    # effective limit in-game is 100, thanks to MaxGameStage attributes.  We
    # could use `bl3save.max_level` here, too, of course, but in the event that
    # I don't get this updated in a timely fashion, having it higher would let
    # this util potentially continue to be able to level up gear.
    if args.item_levels:
        if args.item_levels < 1 or args.item_levels > 100:
            raise argparse.ArgumentTypeError('Valid item level range is 1 through 100')

    # Check for overwrite warnings
    if os.path.exists(args.output_filename) and not args.force:
        sys.stdout.write('WARNING: {} already exists.  Overwrite [y/N]? '.format(args.output_filename))
        sys.stdout.flush()
        response = sys.stdin.readline().strip().lower()
        if len(response) == 0 or response[0] != 'y':
            print('Aborting!')
            sys.exit(1)
        print('')

    # Now load the savegame
    if not args.quiet:
        print('Loading {}'.format(args.input_filename))
    save = BL3Save(args.input_filename)
    if not args.quiet:
        print('')

    # Some argument interactions we should check on
    if args.copy_nvhm:
        if save.get_playthroughs_completed() < 1:
            if 'tvhm' not in args.unlock:
                args.unlock['tvhm'] = True

    # Check to see if we have any changes to make
    have_changes = any([
        args.name,
        args.save_game_id is not None,
        args.level is not None,
        args.mayhem is not None,
        args.money is not None,
        args.eridium is not None,
        len(args.unlock) > 0,
        args.copy_nvhm,
        args.import_items,
        args.items_to_char,
        args.item_levels,
        args.unfinish_nvhm,
        ])

    # Make changes
    if have_changes:

        if not args.quiet:
            print('Making requested changes...')
            print('')

        # Char Name
        if args.name:
            if not args.quiet:
                print(' - Setting Character Name to: {}'.format(args.name))
            save.set_char_name(args.name)

        # Savegame ID
        if args.save_game_id is not None:
            if not args.quiet:
                print(' - Setting Savegame ID to: {}'.format(args.save_game_id))
            save.set_savegame_id(args.save_game_id)

        if args.mayhem is not None:
            if not args.quiet:
                print(' - Setting Mayhem Level to: {}'.format(args.mayhem))
            save.set_all_mayhem_level(args.mayhem)
            if args.mayhem > 0:
                if not args.quiet:
                    print('   - Also ensuring that Mayhem Mode is unlocked')
                save.unlock_challenge(bl3save.MAYHEM)

        # Level
        if args.level is not None:
            if not args.quiet:
                print(' - Setting Character Level to: {}'.format(args.level))
            save.set_level(args.level)

        # Money
        if args.money is not None:
            if not args.quiet:
                print(' - Setting Money to: {}'.format(args.money))
            save.set_money(args.money)

        # Eridium
        if args.eridium is not None:
            if not args.quiet:
                print(' - Setting Eridium to: {}'.format(args.eridium))
            save.set_eridium(args.eridium)

        # Unlocks
        if len(args.unlock) > 0:
            if not args.quiet:
                print(' - Processing Unlocks:')

            # Ammo
            if 'ammo' in args.unlock:
                if not args.quiet:
                    print('   - Ammo SDUs (and setting ammo to max)')
                save.set_max_sdus(bl3save.ammo_sdus)
                save.set_max_ammo()

            # Backpack
            if 'backpack' in args.unlock:
                if not args.quiet:
                    print('   - Backpack SDUs')
                save.set_max_sdus([bl3save.SDU_BACKPACK])

            # Eridian Analyzer
            if 'analyzer' in args.unlock:
                if not args.quiet:
                    print('   - Eridian Analyzer')
                save.unlock_challenge(bl3save.ERIDIAN_ANALYZER)

            # Eridian Resonator
            if 'resonator' in args.unlock:
                if not args.quiet:
                    print('   - Eridian Resonator')
                save.unlock_challenge(bl3save.ERIDIAN_RESONATOR)

            # Gun Slots
            if 'gunslots' in args.unlock:
                if not args.quiet:
                    print('   - Weapon Slots (3+4)')
                save.unlock_slots([bl3save.WEAPON3, bl3save.WEAPON4])

            # Artifact Slot
            if 'artifactslot' in args.unlock:
                if not args.quiet:
                    print('   - Artifact Inventory Slot')
                save.unlock_slots([bl3save.ARTIFACT])

            # COM Slot
            if 'comslot' in args.unlock:
                if not args.quiet:
                    print('   - COM Inventory Slot')
                save.unlock_slots([bl3save.COM])

            # Vehicles
            if 'vehicles' in args.unlock:
                if not args.quiet:
                    print('   - Vehicles (and parts)')
                save.unlock_vehicle_chassis()
                save.unlock_vehicle_parts()

            # Vehicle Skins
            if 'vehicleskins' in args.unlock:
                if not args.quiet:
                    print('   - Vehicle Skins')
                save.unlock_vehicle_skins()

            # TVHM
            if 'tvhm' in args.unlock:
                if not args.quiet:
                    print('   - TVHM')
                save.set_playthroughs_completed(1)

        # Import Items
        if args.import_items:
            if not args.quiet:
                print(' - Importing items from {}'.format(args.import_items))
            added_count = 0
            with open(args.import_items) as df:
                for line in df:
                    itemline = line.strip()
                    if itemline.lower().startswith('bl3(') and itemline.endswith(')'):
                        new_item = save.create_new_item_encoded(itemline)
                        if not args.allow_fabricator:
                            # Report these regardless of args.quiet
                            if not new_item.eng_name:
                                print('   - NOTICE: Skipping unknown item import because --allow-fabricator is not set')
                                continue
                            if new_item.balance_short.lower() == 'balance_eridian_fabricator':
                                print('   - NOTICE: Skipping Fabricator import because --allow-fabricator is not set')
                                continue
                        save.add_item(new_item)
                        if not args.quiet:
                            if new_item.eng_name:
                                print('   + {} (level {})'.format(new_item.eng_name, new_item.level))
                            else:
                                print('   + unknown item')
                        added_count += 1
            if not args.quiet:
                print('   - Added Item Count: {}'.format(added_count))

        # Setting item levels.  Keep in mind that we'll want to do this *after*
        # various of the actions above.  If we've been asked to up the level of
        # the character, we'll want items to follow suit, and if we've been asked
        # to change the level of items, we'll want to do it after the item import.
        if args.items_to_char or args.item_levels:
            if args.items_to_char:
                to_level = save.get_level()
            else:
                to_level = args.item_levels
            num_items = len(save.get_items())
            if not args.quiet:
                if num_items == 1:
                    plural = ''
                else:
                    plural = 's'
                print(' - Updating {} item{} to level {}'.format(
                    num_items,
                    plural,
                    to_level,
                    ))
            actually_updated = 0
            for item in save.get_items():
                if item.level != to_level:
                    item.level = to_level
                    actually_updated += 1
            if not args.quiet:
                remaining = num_items - actually_updated
                if actually_updated == 1:
                    updated_verb = 'was'
                else:
                    updated_verb = 'were'
                if remaining > 0:
                    if remaining == 1:
                        remaining_verb = 'was'
                    else:
                        remaining_verb = 'were'
                    remaining_txt = ' ({} {} already at that level)'.format(remaining, remaining_verb)
                else:
                    remaining_txt = ''
                print('   - {} {} updated{}'.format(
                    actually_updated,
                    updated_verb,
                    remaining_txt,
                    ))

        # Copying NVHM state
        if args.copy_nvhm:
            if not args.quiet:
                print(' - Copying NVHM state to TVHM')
            save.copy_playthrough_data()
        elif args.unfinish_nvhm:
            if not args.quiet:
                print(' - Un-finishing NVHM state entirely')
            # ... or clearing TVHM state entirely.
            save.set_playthroughs_completed(0)
            save.clear_playthrough_data(1)

        # Newline at the end of all this.
        if not args.quiet:
            print('')

    # Write out
    if args.output == 'savegame':
        save.save_to(args.output_filename)
        if not args.quiet:
            print('Wrote savegame to {}'.format(args.output_filename))
    elif args.output == 'protobuf':
        save.save_protobuf_to(args.output_filename)
        if not args.quiet:
            print('Wrote protobuf to {}'.format(args.output_filename))
    elif args.output == 'json':
        save.save_json_to(args.output_filename)
        if not args.quiet:
            print('Wrote JSON to {}'.format(args.output_filename))
    elif args.output == 'items':
        with open(args.output_filename, 'w') as df:
            for item in save.get_items():
                if item.eng_name:
                    print('# {} (level {})'.format(item.eng_name, item.level), file=df)
                else:
                    print('# unknown item', file=df)
                print(item.get_serial_base64(), file=df)
                print('', file=df)
        if not args.quiet:
            print('Wrote {} items (in base64 format) to {}'.format(len(save.get_items()), args.output_filename))
    else:
        # Not sure how we'd ever get here
        raise Exception('Invalid output format specified: {}'.format(args.output))

if __name__ == '__main__':
    main()
