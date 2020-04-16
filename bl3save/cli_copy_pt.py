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
import argparse
import bl3save
from bl3save.bl3save import BL3Save

def main():

    # Set up args
    parser = argparse.ArgumentParser(
            description='Copy BL3 Playthrough Data v{}'.format(bl3save.__version__),
            )

    parser.add_argument('-V', '--version',
            action='version',
            version='BL3 CLI SaveEdit v{}'.format(bl3save.__version__),
            )

    parser.add_argument('-f', '--from',
            dest='filename_from',
            type=str,
            required=True,
            help='Filename to copy playthrough data from')

    parser.add_argument('-t', '--to',
            dest='filename_to',
            type=str,
            required=True,
            help='Filename to copy playthrough data to')

    parser.add_argument('-p', '--playthrough',
            type=int,
            default=0,
            help='Playthrough to copy (defaults to all found playthroughs)')

    parser.add_argument('-c', '--clobber',
            action='store_true',
            help='Clobber (overwrite) files without asking')

    # Parse args
    args = parser.parse_args()

    # Make sure that files exist
    if not os.path.exists(args.filename_from):
        raise Exception('From filename {} does not exist'.format(args.filename_from))
    if not os.path.exists(args.filename_to):
        raise Exception('From filename {} does not exist'.format(args.filename_to))
    if args.filename_from == args.filename_to:
        raise argparse.ArgumentTypeError('To and From filenames cannot be the same')

    # Load the from file and do a quick sanity check
    save_from = BL3Save(args.filename_from)
    total_from_playthroughs = save_from.get_max_playthrough_with_data() + 1
    if args.playthrough > 0 and total_from_playthroughs < args.playthrough:
        raise Exception('{} does not have Playthrough {} data'.format(args.filename_from, args.playthrough))

    # Get a list of playthroughs that we'll process
    if args.playthrough == 0:
        playthroughs = list(range(total_from_playthroughs))
    else:
        playthroughs = [args.playthrough-1]

    # Make sure that we can load our "to" file as well, and do a quick sanity check.
    # Given that there's only NVHM/TVHM at the moment, this should never actually
    # trigger, but I'd accidentally unlocked a third playthrough on my savegame
    # archives, so I was able to test it out regardless, in the event that BL3 ever
    # gets a third playthrough.
    save_to = BL3Save(args.filename_to)
    if args.playthrough > 0:
        total_to_playthroughs = save_to.get_max_playthrough_with_data() + 1
        if total_to_playthroughs == 1:
            plural = ''
        else:
            plural = 's'
        if total_to_playthroughs < args.playthrough-1:
            raise Exception('Cannot copy playthrough {} data to {}; only has {} playthrough{} currently'.format(
                args.playthrough,
                args.filename_to,
                total_to_playthroughs,
                plural,
                ))

    # If we've been given an info file, check to see if it exists
    if not args.clobber:
        if len(playthroughs) == 1:
            plural = ''
        else:
            plural = 's'

        print('WARNING: Playthrough{} {} from {} will be copied into {}'.format(
            plural,
            '+'.join([str(p+1) for p in playthroughs]),
            args.filename_from,
            args.filename_to,
            ))
        sys.stdout.write('Continue [y/N]? ')
        sys.stdout.flush()
        response = sys.stdin.readline().strip().lower()
        if response == 'y':
            pass
        else:
            print('')
            print('Aborting!')
            print('')
            sys.exit(1)

    # If we get here, we're good to go
    for pt in playthroughs:
        save_to.copy_playthrough_data(from_obj=save_from, from_pt=pt, to_pt=pt)

    # Update our Completed Playthroughs if we need to, so that the copied
    # playthroughs are actually active
    required_completion = max(playthroughs)
    if save_to.get_playthroughs_completed() < required_completion:
        save_to.set_playthroughs_completed(required_completion)

    # Write back out to the file
    save_to.save_to(args.filename_to)

    # Report!
    print('')
    print('Done!')
    print('')

if __name__ == '__main__':
    main()

