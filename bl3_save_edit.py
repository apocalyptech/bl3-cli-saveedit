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

import os
import sys
import base64
import argparse
import bl3save
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

# Set up args
parser = argparse.ArgumentParser(
        description='Edit Borderlands 3 Save Files (PC Only)',
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

parser.add_argument('-o', '--output',
        choices=['savegame', 'protobuf', 'items'],
        default='savegame',
        help='Output file format',
        )

parser.add_argument('-f', '--force',
        action='store_true',
        help='Force output file to overwrite',
        )

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

parser.add_argument('--level',
        type=int,
        help='Set the character to this level (from 1 to {})'.format(bl3save.max_level),
        )

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

unlock_choices = ['ammo', 'backpack', 'analyzer', 'resonator', 'artifactslot', 'comslot', 'tvhm']
parser.add_argument('--unlock',
        action=DictAction,
        choices=unlock_choices + ['all'],
        default={},
        help='Game features to unlock',
        )

parser.add_argument('--copy-nvhm',
        dest='copy_nvhm',
        action='store_true',
        help='Copies NVHM/Normal state to TVHM',
        )

parser.add_argument('-i', '--import-items',
        dest='import_items',
        type=str,
        help='Import items from file',
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
if args.level is not None and (args.level < 1 or args.level > bl3save.max_level):
    raise argparse.ArgumentTypeError('Valid level range is 1 through {}'.format(bl3save.max_level))
if 'all' in args.unlock:
    args.unlock = {k: True for k in unlock_choices}

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
print('Loading {}'.format(args.input_filename))
save = BL3Save(args.input_filename)
print('')

# Some argument interactions we should check on
if args.copy_nvhm:
    if save.get_playthroughs_completed() < 1:
        if 'tvhm' not in args.unlock:
            args.unlock['tvhm'] = True

# Make changes
print('Making requested changes...')
print('')

# Char Name
if args.name:
    print(' - Setting Character Name to: {}'.format(args.name))
    save.set_char_name(args.name)

# Savegame ID
if args.save_game_id is not None:
    print(' - Setting Savegame ID to: {}'.format(args.save_game_id))
    save.set_savegame_id(args.save_game_id)

if args.mayhem is not None:
    print(' - Setting Mayhem Level to: {}'.format(args.mayhem))
    save.set_all_mayhem_level(args.mayhem)
    if args.mayhem > 0:
        print('   - Also ensuring that Mayhem Mode is unlocked')
        save.unlock_challenge(bl3save.MAYHEM)

# Level
if args.level is not None:
    print(' - Setting Character Level to: {}'.format(args.level))
    save.set_level(args.level)

# Money
if args.money is not None:
    print(' - Setting Money to: {}'.format(args.money))
    save.set_money(args.money)

# Eridium
if args.eridium is not None:
    print(' - Setting Eridium to: {}'.format(args.eridium))
    save.set_eridium(args.eridium)

# Unlocks
if len(args.unlock) > 0:
    print(' - Processing Unlocks:')

    # Ammo
    if 'ammo' in args.unlock:
        print('   - Ammo SDUs (and setting ammo to max)')
        save.set_max_sdus(bl3save.ammo_sdus)
        save.set_max_ammo()

    # Backpack
    if 'backpack' in args.unlock:
        print('   - Backpack SDUs')
        save.set_max_sdus([bl3save.SDU_BACKPACK])

    # Eridian Analyzer
    if 'analyzer' in args.unlock:
        print('   - Eridian Analyzer')
        save.unlock_challenge(bl3save.ERIDIAN_ANALYZER)

    # Eridian Resonator
    if 'resonator' in args.unlock:
        print('   - Eridian Resonator')
        save.unlock_challenge(bl3save.ERIDIAN_RESONATOR)

    # Artifact Slot
    if 'artifactslot' in args.unlock:
        print('   - Artifact Inventory Slot')
        save.unlock_challenge(bl3save.CHAL_ARTIFACT)

    # COM Slot
    if 'comslot' in args.unlock:
        print('   - COM Inventory Slot')
        save.unlock_char_com_slot()

    # TVHM
    if 'tvhm' in args.unlock:
        print('   - TVHM')
        save.set_playthroughs_completed(1)

# Import Items
if args.import_items:
    print(' - Importing items from {}'.format(args.import_items))
    added_count = 0
    with open(args.import_items) as df:
        for line in df:
            itemline = line.strip()
            if itemline != '' and itemline[0] != '#' and itemline[0] != ';':
                itemdata = base64.b64decode(itemline)
                save.add_new_item(itemdata)
                added_count += 1
    print('   - Added Item Count: {}'.format(added_count))

# Copying NVHM state
if args.copy_nvhm:
    print(' - Copying NVHM state to TVHM')
    save.copy_playthrough_data()

# Write out
print('')
if args.output == 'savegame':
    save.save_to(args.output_filename)
    print('Wrote savegame to {}'.format(args.output_filename))
elif args.output == 'protobuf':
    save.save_protobuf_to(args.output_filename)
    print('Wrote protobuf to {}'.format(args.output_filename))
elif args.output == 'items':
    with open(args.output_filename, 'w') as df:
        for item in save.get_items():
            print(item.get_serial_base64(), file=df)
    print('Wrote {} items (in base64 format) to {}'.format(len(save.get_items()), args.output_filename))
else:
    # Not sure how we'd ever get here
    raise Exception('Invalid output format specified: {}'.format(args.output))

