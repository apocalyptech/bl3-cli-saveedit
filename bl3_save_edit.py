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
import argparse
import bl3save
from bl3save.bl3save import BL3Save

# Set up args
parser = argparse.ArgumentParser(
        description='Edit Borderlands 3 Save Files (PC Only)',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
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

# Positional args
parser.add_argument('input_filename',
        help='Input filename',
        )

parser.add_argument('output_filename',
        help='Output filename',
        )

# Parse args
args = parser.parse_args()
if args.level and (args.level < 1 or args.level > bl3save.max_level):
    raise argparse.ArgumentTypeError('Valid level range is 1 through {}'.format(bl3save.max_level))

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

# Make changes
print('Making requested changes...')
print('')

# Char Name
if args.name:
    print(' - Setting Character Name to: {}'.format(args.name))
    save.set_char_name(args.name)

# Savegame ID
if args.save_game_id:
    print(' - Setting Savegame ID to: {}'.format(args.save_game_id))
    save.set_savegame_id(args.save_game_id)

# Level
if args.level:
    print(' - Setting Character Level to: {}'.format(args.level))
    save.set_level(args.level)

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

