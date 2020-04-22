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
from . import datalib
from bl3save.bl3profile import BL3Profile

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

    parser.add_argument('-f', '--force',
            action='store_true',
            help='Force output file to overwrite',
            )

    parser.add_argument('-q', '--quiet',
            action='store_true',
            help='Supress all non-essential output')

    # Now the actual arguments

    itemlevelgroup = parser.add_mutually_exclusive_group()

    itemlevelgroup.add_argument('--item-levels-max',
            dest='item_levels_max',
            action='store_true',
            help='Set all bank items to max level')

    itemlevelgroup.add_argument('--item-levels',
            dest='item_levels',
            type=int,
            help='Set all bank items to the specified level')

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

    unlock_choices = [
            'lostloot', 'bank',
            ]
    parser.add_argument('--unlock',
            action=DictAction,
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

    # Set max item level arg
    if args.item_levels_max:
        args.item_levels = bl3save.max_level

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

    # Now load the profile
    if not args.quiet:
        print('Loading {}'.format(args.input_filename))
    profile = BL3Profile(args.input_filename)
    if not args.quiet:
        print('')

    # Check to see if we have any changes to make
    have_changes = any([
        len(args.unlock) > 0,
        args.import_items,
        args.item_levels,
        ])

    # Make changes
    if have_changes:

        if not args.quiet:
            print('Making requested changes...')
            print('')

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

        # Import Items
        if args.import_items:
            if not args.quiet:
                print(' - Importing items from {}'.format(args.import_items))
            added_count = 0
            with open(args.import_items) as df:
                for line in df:
                    itemline = line.strip()
                    if itemline.lower().startswith('bl3(') and itemline.endswith(')'):
                        new_item = profile.create_new_item_encoded(itemline)
                        if not args.allow_fabricator:
                            # Report these regardless of args.quiet
                            if not new_item.eng_name:
                                print('   - NOTICE: Skipping unknown item import because --allow-fabricator is not set')
                                continue
                            if new_item.balance_short.lower() == 'balance_eridian_fabricator':
                                print('   - NOTICE: Skipping Fabricator import because --allow-fabricator is not set')
                                continue
                        profile.add_bank_item(new_item)
                        if not args.quiet:
                            if new_item.eng_name:
                                print('   + {} (level {})'.format(new_item.eng_name, new_item.level))
                            else:
                                print('   + unknown item')
                        added_count += 1
            if not args.quiet:
                print('   - Added Item Count: {}'.format(added_count))

        # Setting item levels.  Keep in mind that we'll want to do this *after*
        # various of the actions above.  If we've been asked to change the level
        # of items, we'll want to do it after the item import.
        if args.item_levels:
            num_items = len(profile.get_bank_items())
            if not args.quiet:
                if num_items == 1:
                    plural = ''
                else:
                    plural = 's'
                print(' - Updating {} item{} to level {}'.format(
                    num_items,
                    plural,
                    args.item_levels,
                    ))
            actually_updated = 0
            for idx, item in enumerate(profile.get_bank_items()):
                if item.level != args.item_levels:
                    item.level = args.item_levels
                    profile.set_bank_item(idx, item)
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
        with open(args.output_filename, 'w') as df:
            for item in profile.get_bank_items():
                if item.eng_name:
                    print('# {} (level {})'.format(item.eng_name, item.level), file=df)
                else:
                    print('# unknown item', file=df)
                print(item.get_serial_base64(), file=df)
                print('', file=df)
        if not args.quiet:
            print('Wrote {} items (in base64 format) to {}'.format(len(profile.get_bank_items()), args.output_filename))
    else:
        # Not sure how we'd ever get here
        raise Exception('Invalid output format specified: {}'.format(args.output))

if __name__ == '__main__':
    main()
