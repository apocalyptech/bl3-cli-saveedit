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

def import_items(import_file, item_create_func, item_add_func, allow_fabricator=False, quiet=False):
    """
    Imports items from `import_file`.  `item_create_func` should point to
    a function used to create the item appropriately, and `item_add_func`
    should point to a function used to actually add the item into the
    appropriate container.  If `allow_fabricator` is `False` (the default),
    this routine will refuse to import Fabricators, or any item which
    can't be decoded (in case it's a Fabricator).  If `quiet` is `True`,
    only error/warning output will be shown.
    """
    if not quiet:
        print(' - Importing items from {}'.format(import_file))
    added_count = 0
    with open(import_file) as df:
        for line in df:
            itemline = line.strip()
            if itemline.lower().startswith('bl3(') and itemline.endswith(')'):
                new_item = item_create_func(itemline)
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

def update_item_levels(items, to_level, index_update_func=None, quiet=False):
    """
    Given a list of `items`, update their base level to `level`.  Optionally, for
    Profile editing support, pass in `index_update_func` to specify a function
    to call to update an item serial based on its index in a list.  (Save item
    editing doesn't need that.)  If `quiet` is `True`, only errors will be
    printed.
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
    for idx, item in enumerate(items):
        if item.level != to_level:
            item.level = to_level
            if index_update_func:
                index_update_func(idx, item)
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

