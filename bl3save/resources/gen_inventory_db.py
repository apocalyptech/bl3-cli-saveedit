#!/usr/bin/env python3
# vim: set expandtab tabstop=4 shiftwidth=4:

# Copyright (c) 2020-2021 CJ Kucera (cj@apocalyptech.com)
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

import io
import lzma
import json
import codecs
import argparse
from Crypto.Cipher import AES

# Takes InventorySerialNumberDatabase.dat from inside the BL3 paks and turns
# it into a compressed JSON file suitable for use in our savegame apps.
# At user request, will also write out a version suitable for sending PRs
# to https://github.com/gibbed/Borderlands3Dumps

# Input/Output parameters
input_file = 'InventorySerialNumberDatabase.dat'
output_file = 'inventoryserialdb.json.xz'
gibbed_file = 'Inventory Serial Number Database.json'

###
### Decryption bit.  Thanks to Baysix for this!
###

def decrypt(key, data):
    cipher = AES.new(key, AES.MODE_ECB)
    return cipher.decrypt(data)

def decrypt_db_file(file_path):
    with open(file_path, 'rb') as df:
        data = df.read()
        key = decrypt(data[:32], data[-32:])
        return decrypt(key, data[:-32]).rstrip(b'\x00')

###
### Arguments
###

parser = argparse.ArgumentParser(description='Convert InventorySerialNumberDatabase.dat into JSON')

parser.add_argument('-g', '--gibbed',
        action='store_true',
        help='Also generate JSON suitable for sending PRs to Gibbed at https://github.com/gibbed/Borderlands3Dumps')

args = parser.parse_args()

###
### Do the work
###

# Decrypt
df = io.StringIO(decrypt_db_file(input_file).decode('latin1'))

# Make sure the file header makes sense
header = df.readline().strip()
if header != 'InvSnDb':
    raise Exception('Could not find file header')
version_line = df.readline().strip()
if version_line.startswith('FileVersion='):
    version = int(version_line.split('=', 1)[1])
    if version != 1:
        raise Exception('Unknown serial number: {}'.format(version))
else:
    raise Exception("Didn't find version string")

# Loop through the file and turn it into JSON
top = {}
cur_class = None
for line in df:
    line = line.strip()
    (key, value) = line.split('=', 1)
    if key == 'Class':
        if value in top:
            raise Exception('Already found in db: {}'.format(value))
        cur_class = value
        print('Processing class: {}'.format(cur_class))
        top[cur_class] = {'versions': [], 'assets': []}
    elif key == 'Version':
        if not cur_class:
            raise Exception('Found version without cur_class')
        (vers, bits) = [int(v) for v in value.split(',', 1)]
        top[cur_class]['versions'].append({'version': vers, 'bits': bits})
    elif key == 'Asset':
        if not cur_class:
            raise Exception('Found asset without cur_class')
        (uuid, obj_name) = value.split(',', 1)
        top[cur_class]['assets'].append(obj_name)

# Output to compressed JSON
with lzma.open(output_file, 'wt') as odf:
    json.dump(top, odf, separators=(',', ':'))
print('')
print('Wrote JSON to {}'.format(output_file))

# If we've been asked to, also generate a Gibbed-compatible JSON file, so that
# diffs in that repo are nice and clean.  This is pretty stupidly done, but
# whatever -- the format's simple enough.
if args.gibbed:
    df = io.StringIO(json.dumps(top, indent='  '))
    with open(gibbed_file, 'wt', encoding='utf-8') as real_df:
        real_df.write(codecs.BOM_UTF8.decode('utf-8'))
        doing_versions = False
        started_version = False
        for line in df:
            if doing_versions:
                if started_version:
                    if '}' in line:
                        version_lines.append(line.lstrip())
                        real_df.write(''.join(version_lines))
                        started_version = False
                    else:
                        version_lines.append(line.strip().replace(' ', ''))
                elif '{' in line:
                    version_lines = [line.rstrip()]
                    started_version = True
                else:
                    doing_versions = False
                    real_df.write(line)
            elif '"versions":' in line:
                doing_versions = True
                real_df.write(line)
            else:
                if line == "}\n":
                    real_df.write('}')
                else:
                    real_df.write(line)
    print('')
    print('Wrote Gibbed-compatible JSON to {}'.format(gibbed_file))

