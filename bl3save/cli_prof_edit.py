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
from . import cli_common
from bl3save.bl3profile import BL3Profile

def main():

    # Set up args
    parser = argparse.ArgumentParser(
            description='Borderlands 3 CLI Profile Editor v{} (PC Only)'.format(bl3save.__version__),
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            epilog="""
                The default output type of "profile" will output theoretically-valid
                profile which can be loaded into BL3.  The output type "protobuf"
                will save out the extracted, decrypted protobufs.  The output
                type "json" will output a JSON-encoded version of the protobufs
                in question.  The output type "items" will output a text file
                containing base64-encoded representations of items in the user's
                bank.  These can be read back in using the -i/--import-items
                option.  Note that these are NOT the same as the item strings used
                by the BL3 Memory Editor.
            """
            )

    parser.add_argument('-V', '--version',
            action='version',
            version='BL3 CLI SaveEdit v{}'.format(bl3save.__version__),
            )

    parser.add_argument('-o', '--output',
            choices=['profile', 'protobuf', 'json', 'items'],
            default='profile',
            help='Output file format',
            )

    parser.add_argument('--csv',
            action='store_true',
            help='When importing or exporting items, use CSV files',
            )

    parser.add_argument('-f', '--force',
            action='store_true',
            help='Force output file to overwrite',
            )

    parser.add_argument('-q', '--quiet',
            action='store_true',
            help='Supress all non-essential output')

    # Now the actual arguments

    parser.add_argument('--golden-keys',
            dest='golden_keys',
            type=int,
            help='Number of Golden Keys in the profile',
            )

    itemlevelgroup = parser.add_mutually_exclusive_group()

    itemlevelgroup.add_argument('--item-levels-max',
            dest='item_levels_max',
            action='store_true',
            help='Set all bank items to max level')

    itemlevelgroup.add_argument('--item-levels',
            dest='item_levels',
            type=int,
            help='Set all bank items to the specified level')

    itemmayhemgroup = parser.add_mutually_exclusive_group()

    itemmayhemgroup.add_argument('--item-mayhem-max',
            dest='item_mayhem_max',
            action='store_true',
            help='Set all bank items to the maximum Mayhem level ({})'.format(bl3save.mayhem_max))

    itemmayhemgroup.add_argument('--item-mayhem-levels',
            dest='item_mayhem_levels',
            type=int,
            choices=range(bl3save.mayhem_max+1),
            help='Set all bank items to the specified Mayhem level (0 to remove)')

    parser.add_argument('-i', '--import-items',
            dest='import_items',
            type=str,
            help='Import items from file',
            )

    parser.add_argument('--allow-fabricator',
            dest='allow_fabricator',
            action='store_true',
            help='Allow importing Fabricator when importing items from file',
            )

    parser.add_argument('--clear-customizations',
            dest='clear_customizations',
            action='store_true',
            help='Remove all unlocked customizations',
            )

    parser.add_argument('--alpha',
            dest='alpha',
            action='store_true',
            help='Alphabetize unlocked room decorations, trinkets, and weapon skins',
            )

    unlock_choices = [
            'lostloot', 'bank',
            'skins', 'heads',
            'echothemes', 'emotes', 'decos',
            'weaponskins', 'trinkets',
            'customizations',
            ]
    parser.add_argument('--unlock',
            action=cli_common.DictAction,
            choices=unlock_choices + ['all'],
            default={},
            help='Game features to unlock',
            )

    # Positional args
    parser.add_argument('input_filename',
            help='Input filename',
            )

    parser.add_argument('output_filename',
            help='Output filename',
            )

    # Parse args
    args = parser.parse_args()

    # Expand any of our "all" unlock actions
    if 'all' in args.unlock:
        args.unlock = {k: True for k in unlock_choices}
    elif 'customizations' in args.unlock:
        args.unlock['skins'] = True
        args.unlock['heads'] = True
        args.unlock['echothemes'] = True
        args.unlock['emotes'] = True
        args.unlock['decos'] = True
        args.unlock['weaponskins'] = True
        args.unlock['trinkets'] = True

    # Set max item level arg
    if args.item_levels_max:
        args.item_levels = bl3save.max_level

    # Set max mayhem arg
    if args.item_mayhem_max:
        args.item_mayhem_levels = bl3save.mayhem_max

    # Check golden key count; don't let it be below zero
    if args.golden_keys is not None and args.golden_keys < 0:
        raise argparse.ArgumentTypeError('Golden keys cannot be negative')

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
        if args.output_filename == args.input_filename:
            confirm_msg = 'Really overwrite {} with specified changes (no backup will be made)'.format(args.output_filename)
        else:
            confirm_msg = '{} already exists.  Overwrite'.format(args.output_filename)
        sys.stdout.write('WARNING: {} [y/N]? '.format(confirm_msg))
        sys.stdout.flush()
        response = sys.stdin.readline().strip().lower()
        if len(response) == 0 or response[0] != 'y':
            print('Aborting!')
            sys.exit(1)
        print('')

    # Now load the profile
    if not args.quiet:
        print('Loading {}'.format(args.input_filename))
    profile = BL3Profile(args.input_filename)
    if not args.quiet:
        print('')

    # Check to see if we have any changes to make
    have_changes = any([
        args.golden_keys is not None,
        len(args.unlock) > 0,
        args.import_items,
        args.item_levels,
        args.clear_customizations,
        args.alpha,
        args.item_mayhem_levels is not None,
        ])

    # Make changes
    if have_changes:

        if not args.quiet:
            print('Making requested changes...')
            print('')

        # Golden Keys
        if args.golden_keys is not None:
            print(' - Setting Golden Key count to {}'.format(args.golden_keys))
            profile.set_golden_keys(args.golden_keys)

        # Clear Customizations (do this *before* explicit customization unlocks)
        if args.clear_customizations:
            print(' - Clearing all customizations')
            profile.clear_all_customizations()

        # Unlocks
        if len(args.unlock) > 0:
            if not args.quiet:
                print(' - Processing Unlocks:')

            # Lost Loot
            if 'lostloot' in args.unlock:
                if not args.quiet:
                    print('   - Lost Loot SDUs')
                profile.set_max_sdus([bl3save.PSDU_LOSTLOOT])

            # Bank
            if 'bank' in args.unlock:
                if not args.quiet:
                    print('   - Bank SDUs')
                profile.set_max_sdus([bl3save.PSDU_BANK])

            # Skins
            if 'skins' in args.unlock:
                if not args.quiet:
                    print('   - Character Skins')
                profile.unlock_char_skins()

            # Heads
            if 'heads' in args.unlock:
                if not args.quiet:
                    print('   - Character Heads')
                profile.unlock_char_heads()

            # ECHO Themes
            if 'echothemes' in args.unlock:
                if not args.quiet:
                    print('   - ECHO Themes')
                profile.unlock_echo_themes()

            # Emotes
            if 'emotes' in args.unlock:
                if not args.quiet:
                    print('   - Emotes')
                profile.unlock_emotes()

            # Room Decorations
            if 'decos' in args.unlock:
                if not args.quiet:
                    print('   - Room Decorations')
                profile.unlock_room_decos()

            # Weapon Skins
            if 'weaponskins' in args.unlock:
                if not args.quiet:
                    print('   - Weapon Skins')
                profile.unlock_weapon_skins()

            # Weapon Trinkets
            if 'trinkets' in args.unlock:
                if not args.quiet:
                    print('   - Weapon Trinkets')
                profile.unlock_weapon_trinkets()

        # Customization Alphabetization
        if args.alpha:
            if not args.quiet:
                print(' - Alphabetizing Room Decorations, Trinkets, and Weapon Skins')
            profile.alphabetize_cosmetics()

        # Import Items
        if args.import_items:
            cli_common.import_items(args.import_items,
                    profile.create_new_item_encoded,
                    profile.add_bank_item,
                    file_csv=args.csv,
                    allow_fabricator=args.allow_fabricator,
                    quiet=args.quiet,
                    )

        # Setting item levels.  Keep in mind that we'll want to do this *after*
        # various of the actions above.  If we've been asked to change the level
        # of items, we'll want to do it after the item import.
        if args.item_levels:
            cli_common.update_item_levels(profile.get_bank_items(),
                    args.item_levels,
                    quiet=args.quiet,
                    )

        # Item Mayhem level
        if args.item_mayhem_levels is not None:
            cli_common.update_item_mayhem_levels(profile.get_bank_items(),
                    args.item_mayhem_levels,
                    quiet=args.quiet,
                    )

        # Newline at the end of all this.
        if not args.quiet:
            print('')

    # Write out
    if args.output == 'profile':
        profile.save_to(args.output_filename)
        if not args.quiet:
            print('Wrote profile to {}'.format(args.output_filename))
    elif args.output == 'protobuf':
        profile.save_protobuf_to(args.output_filename)
        if not args.quiet:
            print('Wrote protobuf to {}'.format(args.output_filename))
    elif args.output == 'json':
        profile.save_json_to(args.output_filename)
        if not args.quiet:
            print('Wrote JSON to {}'.format(args.output_filename))
    elif args.output == 'items':
        if args.csv:
            cli_common.export_items_csv(
                    profile.get_bank_items(),
                    args.output_filename,
                    quiet=args.quiet,
                    )
        else:
            cli_common.export_items(
                    profile.get_bank_items(),
                    args.output_filename,
                    quiet=args.quiet,
                    )
    else:
        # Not sure how we'd ever get here
        raise Exception('Invalid output format specified: {}'.format(args.output))

if __name__ == '__main__':
    main()
