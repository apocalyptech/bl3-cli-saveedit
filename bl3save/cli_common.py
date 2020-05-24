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

import csv
import argparse

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

def export_items(items, export_file, quiet=False):
    """
    Exports the given `items` to the given text `export_file`.  If `quiet` is
    `False`, only errors will be printed.
    """
    with open(export_file, 'w') as df:
        for item in items:
            if item.eng_name:
                print('# {} ({})'.format(item.eng_name, item.get_level_eng()), file=df)
            else:
                print('# unknown item', file=df)
            print(item.get_serial_base64(), file=df)
            print('', file=df)
    if not quiet:
        print('Wrote {} items (in base64 format) to {}'.format(len(items), export_file))

def export_items_csv(items, export_file, quiet=False):
    """
    Exports the given `items` to the given CSV `export_file`.  The first column
    will be the English item name, and the second will be the code.  If `quiet` is
    `False`, only errors will be printed.
    """
    with open(export_file, 'w') as df:
        writer = csv.writer(df)
        for item in items:
            if item.eng_name:
                name_label = '{} ({})'.format(item.eng_name, item.get_level_eng())
            else:
                name_label = 'unknown item'
            writer.writerow([
                name_label,
                item.get_serial_base64(),
                ])
    if not quiet:
        print('Wrote {} items (in base64 format) to CSV file {}'.format(len(items), export_file))

def import_items(import_file, item_create_func, item_add_func, file_csv=False, allow_fabricator=False, quiet=False):
    """
    Imports items from `import_file`.  `item_create_func` should point to
    a function used to create the item appropriately, and `item_add_func`
    should point to a function used to actually add the item into the
    appropriate container.  If `file_csv` is `True`, we will process the file
    as if it's a CSV, otherwise we'll process as if it's a "regular"
    text file.  If `allow_fabricator` is `False` (the default),
    this routine will refuse to import Fabricators, or any item which
    can't be decoded (in case it's a Fabricator).  If `quiet` is `True`,
    only error/warning output will be shown.
    """
    if not quiet:
        print(' - Importing items from {}'.format(import_file))
    added_count = 0

    # Process the file to find serials
    looks_like_csv = False
    serial_list = []
    if file_csv:
        # For CSV files, we'll look for serial numbers in literally any cell
        # of the CSV
        with open(import_file) as df:
            reader = csv.reader(df)
            for row in reader:
                for cell in row:
                    cell = cell.strip()
                    if cell.lower().startswith('bl3(') and cell.endswith(')'):
                        serial_list.append(cell)
    else:
        # For text files, we need the entire line to *just* be a valid serial.
        with open(import_file) as df:
            for line in df:
                itemline = line.strip()
                if itemline.lower().startswith('bl3(') and itemline.endswith(')'):
                    serial_list.append(itemline)
                # Also, check to see if we might be a CSV after all, for reporting
                # purposes.
                if len(serial_list) == 0 and not looks_like_csv:
                    if ',bl3(' in itemline.lower():
                        looks_like_csv = True

    # If we didn't add any items, and the file looked like it might've been a CSV
    # (while being processed as a text file), report that to the user, just in case.
    if not file_csv and looks_like_csv:
        print('   - NOTICE: File looked like a CSV file, try adding --csv to the arguments')

    # Now loop through the serials and see if we should add them
    for serial in serial_list:
        new_item = item_create_func(serial)
        if not allow_fabricator:
            # Report these regardless of `quiet`
            if not new_item.eng_name:
                print('   - NOTICE: Skipping unknown item import because --allow-fabricator is not set')
                continue
            if new_item.balance_short.lower() == 'balance_eridian_fabricator':
                print('   - NOTICE: Skipping Fabricator import because --allow-fabricator is not set')
                continue
        item_add_func(new_item)
        if not quiet:
            if new_item.eng_name:
                print('   + {} ({})'.format(new_item.eng_name, new_item.get_level_eng()))
            else:
                print('   + unknown item')
        added_count += 1
    if not quiet:
        print('   - Added Item Count: {}'.format(added_count))

def update_item_levels(items, to_level, quiet=False):
    """
    Given a list of `items`, update their base level to `level`.  If `quiet`
    is `True`, only errors will be printed.
    """
    num_items = len(items)
    if not quiet:
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
    for item in items:
        if item.level != to_level:
            item.level = to_level
            actually_updated += 1
    if not quiet:
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

def update_item_mayhem_levels(items, to_level, quiet=False):
    """
    Given a list of `items`, update their mayhem level to `level`.  If
    `quiet` is `True`, only errors will be printed.
    """
    num_items = len(items)
    if not quiet:
        if num_items == 1:
            plural = ''
        else:
            plural = 's'
        print(' - Updating {} item{} to mayhem level {}'.format(
            num_items,
            plural,
            to_level,
            ))
    actually_updated = 0
    not_possible = 0
    for item in items:
        if item.mayhem_level is None or not item.can_have_mayhem():
            not_possible += 1
        elif item.mayhem_level != to_level:
            item.mayhem_level = to_level
            actually_updated += 1
    if not quiet:
        remaining = num_items - actually_updated - not_possible
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
        if not_possible > 0:
            if not_possible == 1:
                not_possible_verb = 'was'
            else:
                not_possible_verb = 'were'
            not_possible_txt = ' ({} {} unable to be levelled)'.format(not_possible, not_possible_verb)
        else:
            not_possible_txt = ''
        print('   - {} {} updated{}{}'.format(
            actually_updated,
            updated_verb,
            remaining_txt,
            not_possible_txt
            ))

