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

# The encryption/decryption stanzas in BL3Save.__init__ and BL3Save.save_to
# were helpfully provided by Gibbed (rick 'at' gibbed 'dot' us), so many
# thanks for that!  https://twitter.com/gibbed/status/1246863435868049410?s=19
#
# The rest of the savegame format was gleaned from 13xforever/Ilya's
# "gvas-converter" project: https://github.com/13xforever/gvas-converter

import base64
import struct
import random
import binascii
import google.protobuf
import google.protobuf.json_format
from . import *
from . import datalib
from . import OakSave_pb2, OakShared_pb2

MissionState = OakSave_pb2.MissionStatusPlayerSaveGameData.MissionState

class BL3Item(object):
    """
    Pretty thin wrapper around the protobuf object for an item.  We're
    ignoring `development_save_data` entirely since it doesn't seem to
    be present in actual savegames.

    No idea what `pickup_order_index` is, though it might just have
    something to do with the ordering when you're picking up multiple
    things at once (in which case it's probably only really useful for
    things like money and ammo).

    All these getters/setters are rather un-Pythonic; should be using
    some decorations for that instead.  Alas!
    """

    def __init__(self, protobuf, datawrapper):
        self.protobuf = protobuf
        self.datawrapper = datawrapper
        self.serial_db = datawrapper.serial_db
        self.name_db = datawrapper.name_db
        self.parsed = False
        self.can_parse = True
        (self.decrypted_serial, self.orig_seed) = BL3Item._decrypt_serial(self.protobuf.item_serial_number)

        # Attributes which get filled in when we parse
        self._version = None
        self._balance_bits = None
        self._balance_idx = None
        self._balance = None
        self._balance_short = None
        self._eng_name = None
        self._invdata_bits = None
        self._invdata_idx = None
        self._invdata = None
        self._manufacturer_bits = None
        self._manufacturer_idx = None
        self._manufacturer = None
        self._level = None
        self._remaining_data = None

    @staticmethod
    def create(datawrapper, serial_number, pickup_order_idx, skin_path='', is_seen=True, is_favorite=False, is_trash=False):
        """
        Creates a new item with the specified serial number, pickup_order_idx, and skin_path.
        """

        # Start constructing flags
        flags = 0
        if is_seen:
            flags |= 0x1

        # Favorite and Trash are mutually-exclusive
        if is_favorite:
            flags |= 0x2
        elif is_trash:
            flags |= 0x4

        # Now do the creation
        return BL3Item(OakSave_pb2.OakInventoryItemSaveGameData(
                item_serial_number=serial_number,
                pickup_order_index=pickup_order_idx,
                flags=flags,
                weapon_skin_path=skin_path,
                ), datawrapper)

    @staticmethod
    def _xor_data(data, seed):
        """
        Run some `data` through some XOR-based obfuscation, using the
        specified `seed`
        """

        # If the seed is 0, we basically don't do anything (though
        # make sure we return the same datatype as below)
        if seed == 0:
            return [d for d in data]

        # Because our seed can be negative, we do have to do the
        # & here, even though it might not seem to make sense to
        # do so.
        xor = (seed >> 5) & 0xFFFFFFFF
        temp = []
        for i, d in enumerate(data):
            xor = (xor * 0x10A860C1) % 0xFFFFFFFB
            temp.append((d ^ xor) & 0xFF)
        return temp

    @staticmethod
    def _bogodecrypt(data, seed):
        """
        "Decrypts" the given item `data`, using the given `seed`.
        """

        # First run it through the xor wringer.
        temp = BL3Item._xor_data(data, seed)

        # Now rotate the data
        steps = (seed & 0x1F) % len(data)
        return bytearray(temp[-steps:] + temp[:-steps])

    @staticmethod
    def _bogoencrypt(data, seed):
        """
        "Encrypts" the given `data`, using the given `seed`
        """

        # Rotate first
        steps = (seed & 0x1F) % len(data)
        rotated = bytearray(data[steps:] + data[:steps])

        # Then run through the xor stuff
        return bytearray(BL3Item._xor_data(rotated, seed))

    @staticmethod
    def _decrypt_serial(serial):
        """
        Decrypts (really just de-obfuscates) the serial number.
        """

        # Initial byte should always be 3
        assert(serial[0] == 3)

        # Seed does need to be an unsigned int
        orig_seed = struct.unpack('>i', serial[1:5])[0]

        # Do the actual "decryption"
        decrypted = BL3Item._bogodecrypt(serial[5:], orig_seed)

        # Grab the CRC stored in the serial itself
        orig_checksum = bytearray(decrypted[:2])

        # Compute the checksum ourselves to make sure we've done
        # everything properly
        data_to_checksum = serial[:5] + b"\xFF\xFF" + decrypted[2:]
        computed_crc = binascii.crc32(data_to_checksum)
        computed_checksum = struct.pack('>H',
                ((computed_crc >> 16) ^ computed_crc) & 0xFFFF)
        if orig_checksum != computed_checksum:
            raise Exception('Checksum in serial ({}) does not match computed checksum ({})'.format(
                '0x{}'.format(''.join(f'{d:02X}' for d in orig_checksum)),
                '0x{}'.format(''.join(f'{d:02X}' for d in computed_checksum)),
                ))

        # Return what we decrypted
        return (decrypted[2:], orig_seed)

    @staticmethod
    def _encrypt_serial(data, seed=None):
        """
        Given an unencrypted `data`, return the binary serial number for
        the item, optionally with the given `seed`.  If `seed` is not passed in,
        a random one will be passed in.  Use a `seed` of `0` to not apply any
        encryption/obfuscation to the data
        """

        # Pick a random seed if one wasn't given.  Taken from the BL2 CLI editor
        if seed is None:
            seed = random.randrange(0x100000000) - 0x80000000

        # Construct our header and find the checksum
        header = struct.pack('>Bi', 3, seed)
        crc32 = binascii.crc32(header + b"\xFF\xFF" + data)
        checksum = struct.pack('>H', ((crc32 >> 16) ^ crc32) & 0xFFFF)

        # Return the freshly-encrypted item
        return header + BL3Item._bogoencrypt(checksum + data, seed)

    def _get_inv_db_header_part(self, category, bits):
        """
        Given the category name `category`, and the ArbitraryBits object `bits`,
        containing serial number data, return a tuple containing:
            1) The category value
            2) The number of bits the category takes up
            3) The numerical index of the value
        This relies on being run during `_parse_serial`, so that `_version` is
        populated in our object.
        """
        num_bits = self.serial_db.get_num_bits(category, self._version)
        part_idx = bits.eat(num_bits)
        part_val = self.serial_db.get_part(category, part_idx)
        if not part_val:
            part_val = 'unknown'
        return (part_val, num_bits, part_idx)

    def _parse_serial(self):
        """
        Parse our serial number, at least up to the level.  We're not going
        to care about actual parts in here.
        """

        if not self.can_parse:
            return

        bits = datalib.ArbitraryBits(self.decrypted_serial)

        # First value should always be 128, apparently
        assert(bits.eat(8) == 128)

        # Grab the serial version and check it against the max version we know about
        self._version = bits.eat(7)
        if self._version > self.serial_db.max_version:
            self.can_parse = False
            return

        # Now the rest of the data we care about.
        (self._balance,
                self._balance_bits,
                self._balance_idx) = self._get_inv_db_header_part('InventoryBalanceData', bits)
        (self._invdata,
                self._invdata_bits,
                self._invdata_idx) = self._get_inv_db_header_part('InventoryData', bits)
        (self._manufacturer,
                self._manufacturer_bits,
                self._manufacturer_idx) = self._get_inv_db_header_part('ManufacturerData', bits)
        self._level = bits.eat(7)
        self._remaining_data = bits.data

        # At this point, if we were planning on reading parts, we'd read eat six
        # more bits to find the number of parts, then read in that many, using a
        # mapping to get to the correct category.  Then another four bits tells
        # us how many anointments there are, reading from InventoryGenericPartData
        # after that.  After anointments, I'm not totally sure what's out there.

        # Parse out a "short" balance name, for convenience's sake
        self._balance_short = self._balance.split('.')[-1]

        # If we know of an English name for this balance, use it
        self._eng_name = self.name_db.get(self._balance_short)

        # Mark down that we're parsed, now.
        self.parsed = True

    def _deparse_serial(self):
        """
        De-parses a serial; used after we make changes to the data that gets
        pulled out during `_parse_serial`.  At the moment, that's only going
        to be item level changes.  Will update the serial in the protobuf as
        well, and set the object to trigger a re-parse if anything else needs
        to read more.

        This is all pretty inefficient -- really we should just write over the
        bits values with the new values, in-place.  But whatever, this'll do
        for now.
        """

        if not self.can_parse:
            return

        # Construct the new item data
        bits = datalib.ArbitraryBits()
        bits.append_value(128, 8)
        bits.append_value(self._version, 7)
        bits.append_value(self._balance_idx, self._balance_bits)
        bits.append_value(self._invdata_idx, self._invdata_bits)
        bits.append_value(self._manufacturer_idx, self._manufacturer_bits)
        bits.append_value(self._level, 7)
        bits.append_data(self._remaining_data)
        new_data = bits.get_data()

        # Encode the new serial (using seed 0; unencrypted)
        new_serial = BL3Item._encrypt_serial(new_data, 0)

        # Load in the new serial (this will set `parsed` to `False`)
        self.set_serial_number_data(new_serial)

    @property
    def balance(self):
        """
        Returns the balance for this item
        """
        if not self.parsed:
            self._parse_serial()
            if not self.can_parse:
                return None
        return self._balance

    @property
    def balance_short(self):
        """
        Returns the "short" balance for this item
        """
        if not self.parsed:
            self._parse_serial()
            if not self.can_parse:
                return None
        return self._balance_short

    @property
    def eng_name(self):
        """
        Returns an English name for the balance, if possible.  Will default
        to the "short" balance for this item if not.
        """
        if not self.parsed:
            self._parse_serial()
            if not self.can_parse:
                return None
        if self._eng_name:
            return self._eng_name
        else:
            return self._balance_short

    @property
    def level(self):
        """
        Returns the level of this item
        """
        if not self.parsed:
            self._parse_serial()
            if not self.can_parse:
                return None
        return self._level

    @level.setter
    def level(self, value):
        """
        Sets a new level for the item.  This would be a super inefficient way of
        doing it if we supported doing anything other than changing level -- we're
        rebuilding the whole serial right now and triggering a re-parse if anything
        decides to re-read it.  That should be sufficient for our purposes here,
        though.
        """
        if not self.parsed:
            self._parse_serial()
            if not self.can_parse:
                return None

        # Set the level and trigger a re-encode of the serial
        self._level = value
        self._deparse_serial()

    def get_serial_number(self, orig_seed=False):
        """
        Returns the binary item serial number.  If `orig_seed` is `True`, the
        serial number will use the same seed that was used in the savegame.
        Otherwise, it will use a seed of `0`, which will then be unencrypted.
        """
        return BL3Item._encrypt_serial(self.decrypted_serial, 0)

    def get_serial_base64(self, orig_seed=False):
        """
        Returns the base64-encoded item serial number.  If `orig_seed` is
        `True`, the serial number will use the same seed that was used in the
        savegame.  Otherwise, it will use a seed of `0`, which will then be
        unencrypted.
        """
        return 'BL3({})'.format(base64.b64encode(self.get_serial_number(orig_seed)).decode('latin1'))

    def get_pickup_order_idx(self):
        return self.protobuf.pickup_order_index

    def set_serial_number_data(self, new_data):
        """
        Overwrites this item with a new one
        """
        self.protobuf.item_serial_number = new_data
        (self.decrypted_serial, self.orig_seed) = BL3Item._decrypt_serial(self.protobuf.item_serial_number)
        self.parsed = False
        self.can_parse = True

    @staticmethod
    def decode_serial_base64(new_data):
        """
        Overwrites this item with a new one, from a base64 encoding
        """
        if not new_data.lower().startswith('bl3(') or not new_data.endswith(')'):
            raise Exception('Unknown item format: {}'.format(new_data))
        encoded = new_data[4:-1]
        return base64.b64decode(encoded)

class BL3EquipSlot(object):
    """
    Real simple wrapper for a BL3 equipment slot.

    We touch this in a couple of different ways, so it felt like maybe we should
    wrap it up a bit.  We don't touch trinkets at all so I haven't wrapped any
    of that stuff.

    All these getters/setters are rather un-Pythonic; should be using
    some decorations for that instead.  Alas!
    """

    def __init__(self, protobuf):
        self.protobuf = protobuf

    @staticmethod
    def create(index, obj_name, enabled=True, trinket_name=''):
        return BL3EquipSlot(OakSave_pb2.EquippedInventorySaveGameData(
            inventory_list_index=index,
            enabled=enabled,
            slot_data_path=obj_name,
            trinket_data_path=trinket_name,
            ))

    def get_inventory_idx(self):
        """
        Gets the inventory index that we're pointing to
        """
        return self.protobuf.inventory_list_index

    def set_inventory_idx(self, new_idx):
        """
        Sets the inventory index that we're pointing to
        """
        self.protobuf.inventory_list_index = new_idx

    def enabled(self):
        """
        Returns whether we're enabled or not
        """
        return self.protobuf.enabled

    def set_enabled(self, enabled=True):
        """
        Sets our enabled state
        """
        self.protobuf.enabled = enabled

    def get_obj_name(self):
        """
        Returns our path object name
        """
        return self.protobuf.slot_data_path

class BL3Save(object):
    """
    Real simple wrapper for a BL3 savegame file.
    
    Only tested on PC versions.  Thanks to Gibbed for the encryption method and
    the Protobuf definitions!

    https://twitter.com/gibbed/status/1246863435868049410?s=19

    All these getters/setters are rather un-Pythonic; should be using
    some decorations for that instead.  Alas!
    """

    _prefix_magic = bytearray([
        0x71, 0x34, 0x36, 0xB3, 0x56, 0x63, 0x25, 0x5F,
        0xEA, 0xE2, 0x83, 0x73, 0xF4, 0x98, 0xB8, 0x18,
        0x2E, 0xE5, 0x42, 0x2E, 0x50, 0xA2, 0x0F, 0x49,
        0x87, 0x24, 0xE6, 0x65, 0x9A, 0xF0, 0x7C, 0xD7,
        ])

    _xor_magic = bytearray([
        0x7C, 0x07, 0x69, 0x83, 0x31, 0x7E, 0x0C, 0x82,
        0x5F, 0x2E, 0x36, 0x7F, 0x76, 0xB4, 0xA2, 0x71,
        0x38, 0x2B, 0x6E, 0x87, 0x39, 0x05, 0x02, 0xC6,
        0xCD, 0xD8, 0xB1, 0xCC, 0xA1, 0x33, 0xF9, 0xB6,
        ])

    def __init__(self, filename, debug=False):
        self.filename = filename
        self.datawrapper = datalib.DataWrapper()
        with open(filename, 'rb') as df:

            header = df.read(4)
            assert(header == b'GVAS')

            self.sg_version = self._read_int(df)
            if debug:
                print('Savegame version: {}'.format(self.sg_version))
            self.pkg_version = self._read_int(df)
            if debug:
                print('Package version: {}'.format(self.pkg_version))
            self.engine_major = self._read_short(df)
            self.engine_minor = self._read_short(df)
            self.engine_patch = self._read_short(df)
            self.engine_build = self._read_int(df)
            if debug:
                print('Engine version: {}.{}.{}.{}'.format(
                    self.engine_major,
                    self.engine_minor,
                    self.engine_patch,
                    self.engine_build,
                    ))
            self.build_id = self._read_str(df)
            if debug:
                print('Build ID: {}'.format(self.build_id))
            self.fmt_version = self._read_int(df)
            if debug:
                print('Custom Format Version: {}'.format(self.fmt_version))
            fmt_count = self._read_int(df)
            if debug:
                print('Custom Format Data Count: {}'.format(fmt_count))
            self.custom_format_data = []
            for _ in range(fmt_count):
                guid = self._read_guid(df)
                entry = self._read_int(df)
                if debug:
                    print(' - GUID {}: {}'.format(guid, entry))
                self.custom_format_data.append((guid, entry))
            self.sg_type = self._read_str(df)
            if debug:
                print('Savegame type: {}'.format(self.sg_type))

            # Read in the actual data
            remaining_data_len = self._read_int(df)
            data = bytearray(df.read(remaining_data_len))

            # Decrypt
            for i in range(len(data)-1, -1, -1):
                if i < 32:
                    b = BL3Save._prefix_magic[i]
                else:
                    b = data[i - 32]
                b ^= BL3Save._xor_magic[i % 32]
                data[i] ^= b

            # Make sure that was all there was
            last = df.read()
            assert(len(last) == 0)

            # Parse protobufs
            self.import_protobuf(data)

    def import_protobuf(self, data):
        """
        Given raw protobuf data, load it into ourselves so
        that we can work with it.  This also sets up a few
        convenience vars for our later use
        """

        # Now parse the protobufs
        self.save = OakSave_pb2.Character()
        self.save.ParseFromString(data)

        # Some sanity checks, since this is a potentially problematic
        # operation.
        assert(self.save.IsInitialized())
        assert(len(self.save.UnknownFields()) == 0)

        # Not checking on byte size, in case anyone had v2 protobufs
        # exported and were trying to import them now that we've
        # otherwise switched to v3.
        #assert(len(data) == self.save.ByteSize())

        # Do some data processing so that we can wrap things APIwise
        # First: Items
        self.items = [BL3Item(i, self.datawrapper) for i in self.save.inventory_items]

        # Next: Equip slots
        self.equipslots = {}
        for e in self.save.equipped_inventory_list:
            equip = BL3EquipSlot(e)
            slot = slotobj_to_slot[equip.get_obj_name()]
            self.equipslots[slot] = equip

    def import_json(self, json_str):
        """
        Given JSON data, convert to protobuf and load it into ourselves so
        that we can work with it.  This also sets up a few convenience vars
        for our later use
        """
        message = google.protobuf.json_format.Parse(json_str, OakSave_pb2.Character())
        self.import_protobuf(message.SerializeToString())

    def save_to(self, filename):
        """
        Saves ourselves to a new filename
        """
        with open(filename, 'wb') as df:

            # Header info
            df.write(b'GVAS')
            self._write_int(df, self.sg_version)
            self._write_int(df, self.pkg_version)
            self._write_short(df, self.engine_major)
            self._write_short(df, self.engine_minor)
            self._write_short(df, self.engine_patch)
            self._write_int(df, self.engine_build)
            self._write_str(df, self.build_id)
            self._write_int(df, self.fmt_version)
            self._write_int(df, len(self.custom_format_data))
            for guid, entry in self.custom_format_data:
                self._write_guid(df, guid)
                self._write_int(df, entry)
            self._write_str(df, self.sg_type)

            # Turn our parsed protobuf back into data
            data = bytearray(self.save.SerializeToString())

            # Encrypt
            for i in range(len(data)):
                if i < 32:
                    b = self._prefix_magic[i]
                else:
                    b = data[i - 32]
                b ^= self._xor_magic[i % 32]
                data[i] ^= b

            # Write out to the file
            self._write_int(df, len(data))
            df.write(data)

    def save_protobuf_to(self, filename):
        """
        Saves the raw protobufs to the specified filename
        """
        with open(filename, 'wb') as df:
            df.write(self.save.SerializeToString())

    def save_json_to(self, filename):
        """
        Saves a JSON version of our protobuf to the specfied filename
        """
        with open(filename, 'w') as df:
            df.write(google.protobuf.json_format.MessageToJson(self.save,
                including_default_value_fields=True,
                preserving_proto_field_name=True,
                ))

    def _read_int(self, df):
        return struct.unpack('<I', df.read(4))[0]

    def _write_int(self, df, value):
        df.write(struct.pack('<I', value))

    def _read_short(self, df):
        return struct.unpack('<H', df.read(2))[0]

    def _write_short(self, df, value):
        df.write(struct.pack('<H', value))

    def _read_str(self, df):
        datalen = self._read_int(df)
        if datalen == 0:
            return None
        elif datalen == 1:
            return ''
        else:
            value = df.read(datalen)
            return value[:-1].decode('utf-8')

    def _write_str(self, df, value):
        if value is None:
            self._write_int(df, 0)
        elif value == '':
            self._write_int(df, 1)
        else:
            data = value.encode('utf-8') + b'\0'
            self._write_int(df, len(data))
            df.write(data)

    def _read_guid(self, df):
        data = df.read(16)
        return data
        # A bit silly to bother formatting it, since we don't care.
        #arr = ''.join(['{:02x}'.format(d) for d in data])
        #return '{}-{}-{}-{}-{}'.format(
        #        arr[0:8],
        #        arr[8:12],
        #        arr[12:16],
        #        arr[16:20],
        #        arr[20:32],
        #        )

    def _write_guid(self, df, value):
        df.write(value)

    def get_char_name(self):
        """
        Returns the character name
        """
        return self.save.preferred_character_name

    def set_char_name(self, new_name):
        """
        Sets the character name
        """
        self.save.preferred_character_name = new_name

    def get_savegame_id(self):
        """
        Returns the savegame ID (not sure if this is important at all)
        """
        return self.save.save_game_id

    def set_savegame_id(self, new_id):
        """
        Sets the savegame ID (not sure if this is important at all)
        """
        self.save.save_game_id = new_id

    def get_pet_names(self, eng=False):
        """
        Returns a dict mapping pet types to pet names, if any are defined.  The pet type
        key is a constant by default, or an English label if `eng` is `True`
        """
        ret = {}
        for name in self.save.nickname_mappings:
            key = petkey_to_pet[name.key.lower()]
            if eng:
                key = pet_to_eng[key]
            ret[key] = name.value
        return ret

    def get_pet_name(self, pet_type):
        """
        Returns the pet name matching the given type constant
        """
        pet_names = self.get_pet_names()
        if pet_type in pet_names:
            return pet_names[pet_type]
        return None

    def get_class(self, eng=False):
        """
        Returns the class of this character.  By default it will be a constant,
        but if `eng` is `True` it will be an English label instead.
        """
        classval = classobj_to_class[self.save.player_class_data.player_class_path]
        if eng:
            return class_to_eng[classval]
        return classval

    def get_xp(self):
        """
        Returns the character's XP
        """
        return self.save.experience_points

    def get_level(self):
        """
        Returns the character's level
        """
        xp = self.get_xp()
        cur_lvl = 0
        for req_xp_lvl in required_xp_list:
            if xp >= req_xp_lvl:
                cur_lvl += 1
            else:
                return cur_lvl
        return cur_lvl

    def set_level(self, level, top_val=False):
        """
        Sets the character's level to the given `level`.  By default will
        assign the least amount of XP possible to gain the specified level,
        but if `top_val` is `True`, will assign the maximum possible XP in
        that level, instead (so 1XP more will cause the character to level
        up).
        """
        if level > len(required_xp_list):
            raise Exception('Unknown level {}'.format(level))
        if level > max_level:
            raise Exception('Maximum level is {}'.format(max_level))
        if level < 1:
            raise Exception('Level must be at least 1')
        
        # If we've been told to assign the max level, we can't do top_val
        if level == max_level:
            top_val = False

        # Now assign
        if top_val:
            self.save.experience_points = required_xp_list[level]-1
        else:
            self.save.experience_points = required_xp_list[level-1]

    def get_playthroughs_completed(self):
        """
        Returns the number of playthroughs completed
        """
        return self.save.playthroughs_completed

    def set_playthroughs_completed(self, playthrough_count):
        """
        Sets the number of playthroughs completed
        """
        self.save.playthroughs_completed = playthrough_count

    def get_max_playthrough_with_data(self):
        """
        Returns the maximum playthrough for which we have actual data in
        the savegame.  Even if TVHM is unlocked, for instance, we may
        only have NVHM data in the savefile.
        """
        # Really I don't think that any of these numbers will ever be
        # different, but what the hell, we'll check 'em all anyway.
        return min(
                len(self.save.mission_playthroughs_data),
                len(self.save.active_travel_stations_for_playthrough),
                len(self.save.last_active_travel_station_for_playthrough),
                len(self.save.game_state_save_data_for_playthrough),
                )

    def get_pt_mayhem_levels(self):
        """
        Returns a list of Mayhem levels active for each Playthrough
        """
        return [d.mayhem_level for d in self.save.game_state_save_data_for_playthrough]

    def get_pt_mayhem_level(self, pt):
        """
        Returns the Mayhem level for the given Playthrough (zero-indexed)
        """
        if len(self.save.game_state_save_data_for_playthrough) > pt:
            return self.save.game_state_save_data_for_playthrough[pt].mayhem_level
        return None

    def set_mayhem_level_pt(self, pt, mayhem):
        """
        Sets the mayhem level for the given Playthrough (zero-indexed)
        """
        self.save.game_state_save_data_for_playthrough[pt].mayhem_level = mayhem

    def set_all_mayhem_level(self, mayhem):
        """
        Sets the mayhem level for all Playthroughs.
        """
        for data in self.save.game_state_save_data_for_playthrough:
            data.mayhem_level = mayhem

    def copy_game_state_pt(self, from_obj=None, from_pt=0, to_pt=1):
        """
        Copies game state (mostly mayhem level, but also possibly current-map info?
        Though I'd thought that was taken care of with the last active station) from
        one Playthrough to another (zero-indexed playthroughs).  Will refuse to create
        "gaps"; `to_pt` is only allowed to be one higher than the current number of
        Playthroughs.  Defaults to copying NVHM data to TVHM.  This can also be used to
        copy data from another BL3Save object; pass in `from_obj` to do that.
        """
        if not from_obj:
            from_obj = self
        if from_pt > len(from_obj.save.game_state_save_data_for_playthrough)-1:
            raise Exception('PT {} is not found in mission data'.format(from_pt))
        if to_pt > len(self.save.game_state_save_data_for_playthrough):
            raise Exception('to_pt can be at most {} for this save'.format(len(self.save.game_state_save_data_for_playthrough)))
        if from_obj == self and from_pt == to_pt:
            raise Exception('from_pt and to_pt cannot be the same')
        if from_pt < 0 or to_pt < 0:
            raise Exception('from_pt and to_pt cannot be negative')

        if to_pt == len(self.save.game_state_save_data_for_playthrough):
            self.save.game_state_save_data_for_playthrough.append(from_obj.save.game_state_save_data_for_playthrough[from_pt])
        else:
            del self.save.game_state_save_data_for_playthrough[to_pt]
            self.save.game_state_save_data_for_playthrough.insert(to_pt, from_obj.save.game_state_save_data_for_playthrough[from_pt])

    def get_pt_last_stations(self):
        """
        Returns a list of the object names of the last station (fast travel,
        resurrection, level) the player has been near, for each Playthrough
        """
        return self.save.last_active_travel_station_for_playthrough

    def get_pt_last_station(self, pt):
        """
        Returns the last station (fast travel, resurrection, level) the player
        has been near, for the given Playthrough (zero-indexed)
        """
        if len(self.save.last_active_travel_station_for_playthrough) > pt:
            return self.save.last_active_travel_station_for_playthrough[pt]
        return None

    def copy_last_station_pt(self, from_obj=None, from_pt=0, to_pt=1):
        """
        Copies last-station state (ie: current map) from one Playthrough to another
        (zero-indexed playthroughs).  Will refuse to create "gaps"; `to_pt`
        is only allowed to be one higher than the current number of Playthroughs.
        Defaults to copying NVHM data to TVHM.  This can also be used to copy
        data from another BL3Save object; pass in `from_obj` to do that.
        """
        if not from_obj:
            from_obj = self
        if from_pt > len(from_obj.save.last_active_travel_station_for_playthrough)-1:
            raise Exception('PT {} is not found in mission data'.format(from_pt))
        if to_pt > len(self.save.last_active_travel_station_for_playthrough):
            raise Exception('to_pt can be at most {} for this save'.format(len(self.save.last_active_travel_station_for_playthrough)))
        if from_obj == self and from_pt == to_pt:
            raise Exception('from_pt and to_pt cannot be the same')
        if from_pt < 0 or to_pt < 0:
            raise Exception('from_pt and to_pt cannot be negative')

        if to_pt == len(self.save.last_active_travel_station_for_playthrough):
            self.save.last_active_travel_station_for_playthrough.append(from_obj.save.last_active_travel_station_for_playthrough[from_pt])
        else:
            self.save.last_active_travel_station_for_playthrough[to_pt] = from_obj.save.last_active_travel_station_for_playthrough[from_pt]

    def get_pt_last_maps(self, eng=False):
        """
        Returns a list maps which the player has been in, for each Playthrough.
        Maps will be their in-game IDs by default, or English names if `eng`
        is `True`
        """
        # TODO: should maybe handle these edge cases better?
        maps = []
        for station in self.get_pt_last_stations():
            if station is None:
                maps.append('(NO MAP)')
            elif station == '':
                maps.append('(BLANK MAP)')
            else:
                lower = station.lower()
                if lower in fts_to_map:
                    mapname = fts_to_map[lower]
                    if eng:
                        if mapname in map_to_eng:
                            mapname = map_to_eng[mapname]
                        else:
                            mapname = '(Unknown map: {})'.format(mapname)
                    maps.append(mapname)
                else:
                    maps.append('(Unknown station: {})'.format(station))
        return maps

    def get_pt_last_map(self, pt, eng=False):
        """
        Returns the last map the player has been in, for the specified
        Playthrough (zero-indexed).  The map will be its in-game ID by
        default, or the English name if `eng` is `True`
        """
        map_ids = self.get_pt_last_maps(eng=eng)
        if len(map_ids) > pt:
            return map_ids[pt]
        return None

    # Part of attempting to unlock Sanctuary early would probably be unlocking its FT station,
    # in addition to the related Challenge, though my attempts to do so didn't work.  I don't
    # actually care enough to properly wrap this up, but here's some code I'd originally used
    # for the FT unlock:
	#sanc_ft = '/Game/GameData/FastTravel/FTS_Sanctuary.FTS_Sanctuary'
	#have_sanc = False
	#for ft in self.save.active_travel_stations_for_playthrough[0].active_travel_stations:
	#    if ft.active_travel_station_name == sanc_ft:
	#        have_sanc = True
	#        break
	#if not have_sanc:
	#    self.save.active_travel_stations_for_playthrough[0].active_travel_stations.append(OakSave_pb2.ActiveFastTravelSaveData(
	#        active_travel_station_name=sanc_ft,
	#        blacklisted = False,
	#        ))

    def get_pt_active_ft_station_lists(self):
        """
        Returns a list of Fast travel station names active for each playthrough
        """
        to_ret = []
        for data in self.save.active_travel_stations_for_playthrough:
            to_ret.append([d.active_travel_station_name for d in data.active_travel_stations])
        return to_ret

    def get_pt_active_ft_station_list(self, pt):
        """
        Returns a list of Fast Travel station names active for the given
        Playthrough (zero-indexed)
        """
        ptlist = self.get_pt_active_ft_station_lists()
        if len(ptlist) > pt:
            return ptlist[pt]
        return None

    def copy_active_ft_stations_pt(self, from_obj=None, from_pt=0, to_pt=1):
        """
        Copies Fast Travel activation state from one Playthrough to another
        (zero-indexed playthroughs).  Will refuse to create "gaps"; `to_pt`
        is only allowed to be one higher than the current number of Playthroughs.
        Defaults to copying NVHM data to TVHM.  This can also be used to copy
        data from another BL3Save object; pass in `from_obj` to do that.
        """
        if not from_obj:
            from_obj = self
        if from_pt > len(from_obj.save.active_travel_stations_for_playthrough)-1:
            raise Exception('PT {} is not found in mission data'.format(from_pt))
        if to_pt > len(self.save.active_travel_stations_for_playthrough):
            raise Exception('to_pt can be at most {} for this save'.format(len(self.save.active_travel_stations_for_playthrough)))
        if from_obj == self and from_pt == to_pt:
            raise Exception('from_pt and to_pt cannot be the same')
        if from_pt < 0 or to_pt < 0:
            raise Exception('from_pt and to_pt cannot be negative')

        if to_pt == len(self.save.active_travel_stations_for_playthrough):
            self.save.active_travel_stations_for_playthrough.append(from_obj.save.active_travel_stations_for_playthrough[from_pt])
        else:
            del self.save.active_travel_stations_for_playthrough[to_pt]
            self.save.active_travel_stations_for_playthrough.insert(to_pt, from_obj.save.active_travel_stations_for_playthrough[from_pt])

    def get_pt_active_mission_lists(self, eng=False):
        """
        Returns a list of active missions for each Playthrough.  Missions will
        be in their object name by default, or their English names if `eng` is
        `True`.
        """
        to_ret = []
        for pt in self.save.mission_playthroughs_data:
            active_missions = []
            for mission in pt.mission_list:
                if mission.status == MissionState.MS_Active:
                    mission_name = mission.mission_class_path
                    if eng:
                        if mission_name.lower() in mission_to_name:
                            mission_name = mission_to_name[mission_name.lower()]
                        else:
                            mission_name = '(Unknown mission: {})'.format(mission_name)
                    active_missions.append(mission_name)
            to_ret.append(active_missions)
        return to_ret

    def get_pt_active_mission_list(self, pt, eng=False):
        """
        Returns a list of active mission object names for the given
        Playthrough (zero-indexed).  Missions will be in their object name
        by default, or their English names if `eng` is `True`
        """
        missions = self.get_pt_active_mission_lists(eng=eng)
        if len(missions) > pt:
            return missions[pt]
        return None

    def get_pt_completed_mission_counts(self):
        """
        Returns a count of completed missions for each Playthrough.
        """
        to_ret = []
        for pt in self.save.mission_playthroughs_data:
            mission_count = 0
            for mission in pt.mission_list:
                if mission.status == MissionState.MS_Complete:
                    mission_count += 1
            to_ret.append(mission_count)
        return to_ret

    def get_pt_completed_mission_count(self, pt):
        """
        Returns a count of completed mission object names for the given
        Playthrough (zero-indexed).
        """
        counts = self.get_pt_completed_mission_counts()
        if len(counts) > pt:
            return counts[pt]
        return None

    def copy_mission_pt(self, from_obj=None, from_pt=0, to_pt=1):
        """
        Copies mission state from one Playthrough to another (zero-indexed
        playthroughs).  Will refuse to create "gaps"; `to_pt` is only
        allowed to be one higher than the current number of Playthroughs.
        Defaults to copying NVHM data to TVHM.  This can also be used to copy
        data from another BL3Save object; pass in `from_obj` to do that.
        """
        if not from_obj:
            from_obj = self
        if from_pt > len(from_obj.save.mission_playthroughs_data)-1:
            raise Exception('PT {} is not found in mission data'.format(from_pt))
        if to_pt > len(self.save.mission_playthroughs_data):
            raise Exception('to_pt can be at most {} for this save'.format(len(self.save.mission_playthroughs_data)))
        if from_obj == self and from_pt == to_pt:
            raise Exception('from_pt and to_pt cannot be the same')
        if from_pt < 0 or to_pt < 0:
            raise Exception('from_pt and to_pt cannot be negative')

        if to_pt == len(self.save.mission_playthroughs_data):
            self.save.mission_playthroughs_data.append(from_obj.save.mission_playthroughs_data[from_pt])
        else:
            del self.save.mission_playthroughs_data[to_pt]
            self.save.mission_playthroughs_data.insert(to_pt, from_obj.save.mission_playthroughs_data[from_pt])

    def copy_playthrough_data(self, from_obj=None, from_pt=0, to_pt=1):
        """
        Copies playthrough-specific data from one playthrough to another (zero-indexed).  Currently
        handles: mission state, active Fast Travels, last station visited, and "game state," which
        includes mayhem mode.  Will refuse to crate "gaps"; `to_pt` is only allowed to be one
        higher than the current number of Playthroughs.  Defaults to copying NVHM to TVHM.
        This can also be used to copy playthrough data from another BL3Save object; pass in `from_obj`
        to do that.
        """
        if not from_obj:
            from_obj = self
        self.copy_mission_pt(from_obj=from_obj, from_pt=from_pt, to_pt=to_pt)
        self.copy_active_ft_stations_pt(from_obj=from_obj, from_pt=from_pt, to_pt=to_pt)
        self.copy_last_station_pt(from_obj=from_obj, from_pt=from_pt, to_pt=to_pt)
        self.copy_game_state_pt(from_obj=from_obj, from_pt=from_pt, to_pt=to_pt)

    def get_items(self):
        """
        Returns a list of the character's inventory items, as BL3Item objects.
        """
        return self.items

    def get_equipped_items(self, eng=False):
        """
        Returns a dict containing the slot and the equipped item.  The slot will
        be a constant by default, or an English label if `eng` is `True`
        """
        to_ret = {}
        for (key, equipslot) in self.equipslots.items():
            if eng:
                key = slot_to_eng[key]
            if equipslot.get_inventory_idx() >= 0:
                to_ret[key] = self.items[equipslot.get_inventory_idx()]
            else:
                to_ret[key] = None
        return to_ret

    def get_equipped_item_slot(self, slot):
        """
        Given a slot, return the item equipped in that slot
        """
        if slot in self.equipslots:
            inv_idx = self.equipslots[slot].get_inventory_idx()
            if inv_idx >= 0 and len(self.items) > inv_idx:
                return self.items[inv_idx]
        return None

    def get_equip_slots(self, eng=False):
        """
        Returns a dict of slot ID and BL3EquipSlot objects, for all inventory
        slots.  The slot will be a constant by default, or an English label if
        `eng` is `True`
        """
        return self.equipslots

    def get_equip_slot(self, slot):
        """
        Returns the BL3EquipSlot object in the specified `slot`.
        """
        if slot in self.equipslots:
            return self.equipslots[slot]
        return None

    def unlock_slots(self, slots=None):
        """
        Unlocks the specified inventory `slots`, which should be a list of slot
        IDs.  If `slots` is not passed in, will unlock all inventory slots.  This
        will take the initiative to unlock some associated challenges, if
        necessary -- Artifacts and COMs in particular have an associated challenge
        with their slot unlocking, which we'll go ahead and process.
        """
        if not slots:
            slots = slot_to_eng.keys()
        for slot in slots:
            self.equipslots[slot].set_enabled()
            if slot == ARTIFACT:
                self.unlock_challenge(CHAL_ARTIFACT)
            elif slot == COM:
                self.unlock_char_com_challenge()

    def add_item(self, new_item):
        """
        Adds a new `new_item` (BL3Item object) to our item list.  Returns the item's
        new index in our item list.
        """

        # Add the item to the protobuf
        self.save.inventory_items.append(new_item.protobuf)

        # The protobuf reference that we append to the protobuf list
        # ends up *not* being the one that's actually used when we
        # save, so if we want to be able to alter it later (say, below
        # when levelling up items), we have to grab a fresh reference
        # to it.
        new_item.protobuf = self.save.inventory_items[-1]

        # Now update our internal items list and return
        self.items.append(new_item)
        return len(self.items)-1

    def create_new_item(self, item_serial):
        """
        Creates a new item from the given binary `item_serial`, which can later
        be added to our item list.
        """

        # Okay, I have no idea what this pickup_order_index attribute is about, but let's
        # make sure it's unique anyway.  It might be related to ordering when picking
        # up multiple items at once, which would probably make it more useful for auto-pick-up
        # items like money and ammo...
        max_pickup_order = 0
        for item in self.items:
            if item.get_pickup_order_idx() > max_pickup_order:
                max_pickup_order = item.get_pickup_order_idx()

        # Create the item and return it
        new_item = BL3Item.create(self.datawrapper,
                serial_number=item_serial,
                pickup_order_idx=max_pickup_order+1,
                is_favorite=True,
                )
        return new_item

    def create_new_item_encoded(self, item_serial_b64):
        """
        Creates a new item from the base64-encoded (and "BL3()"-wrapped)
        `item_serial_b64`, which can later be added to our item list.
        """
        return self.create_new_item(BL3Item.decode_serial_base64(item_serial_b64))

    def add_new_item(self, item_serial):
        """
        Adds a new item to our item list using the binary `item_serial`.
        Returns a tuple containing the new BL3Item object itself, and its
        new index in our item list.
        """
        new_item = self.create_new_item(item_serial)
        return (new_item, self.add_item(new_item))

    def add_new_item_encoded(self, item_serial_b64):
        """
        Adds a new item to our item list using the base64-encoded (and
        "BL3()"-wrapped) `item_serial_b64`.  Returns a tuple containing the
        new BL3Item object itself, and its new index in our item list.
        """
        return self.add_new_item(BL3Item.decode_serial_base64(item_serial_b64))

    def overwrite_item_in_slot(self, slot, itemdata):
        """
        Given a binary `itemdata`, overwrite whatever item is in the given `slot`.  Will create
        a new item object if the slot is empty.
        """
        item = self.get_equipped_item_slot(slot)
        if item:
            item.set_serial_number_data(itemdata)
        else:
            # Now create a new item
            (new_item, new_index) = self.add_new_item(itemdata)

            # Now assign it to the slot
            found_slot = False
            if slot in self.equipslots:
                found_slot = True
                self.equipslots[slot].set_inventory_idx(new_index)

            # If we didn't find a slot, create it (I don't *think* this should ever happen?)
            if not found_slot:
                equipslot = BL3EquipSlot.create(new_index, slot_obj)
                self.save.equipped_inventory_list.append(equipslot.protobuf)
                self.equipslots[slot] = equipslot

    def get_currency(self, currency_type):
        """
        Returns the amount of currency of the given type
        """
        for cat_save_data in self.save.inventory_category_list:
            if cat_save_data.base_category_definition_hash in curhash_to_currency:
                if currency_type == curhash_to_currency[cat_save_data.base_category_definition_hash]:
                    return cat_save_data.quantity
        return 0

    def set_currency(self, currency_type, new_value):
        """
        Sets a new currency value
        """

        # Update an existing value, if we have it
        for cat_save_data in self.save.inventory_category_list:
            if cat_save_data.base_category_definition_hash in curhash_to_currency:
                if currency_type == curhash_to_currency[cat_save_data.base_category_definition_hash]:
                    cat_save_data.quantity = new_value
                    return

        # Add a new one, if we don't
        self.save.inventory_category_list.append(OakShared_pb2.InventoryCategorySaveData(
            base_category_definition_hash=currency_to_curhash[currency_type],
            quantity=new_value,
            ))

    def get_money(self):
        """
        Returns the amount of money we have
        """
        return self.get_currency(MONEY)

    def set_money(self, new_value):
        """
        Sets the amount of money we have
        """
        return self.set_currency(MONEY, new_value)

    def get_eridium(self):
        """
        Returns the amount of eridium we have
        """
        return self.get_currency(ERIDIUM)

    def set_eridium(self, new_value):
        """
        Sets the amount of eridium we have
        """
        return self.set_currency(ERIDIUM, new_value)

    def get_sdus(self, eng=False):
        """
        Returns a dict containing the SDU type and the number purchased.  The SDU
        type key will be a constant by default, or an English label if `eng` is `True`
        """
        to_ret = {}
        for sdu in self.save.sdu_list:
            key = sduobj_to_sdu[sdu.sdu_data_path]
            if eng:
                key = sdu_to_eng[key]
            to_ret[key] = sdu.sdu_level
        return to_ret

    def get_sdu(self, sdu):
        """
        Returns the number of SDUs purchased for the specified type
        """
        sdus = self.get_sdus()
        if sdu in sdus:
            return sdus[sdu]
        return 0

    def set_max_sdus(self, sdulist=None):
        """
        Sets the specified SDUs (or all SDUs that we know about) to be at the max level
        """
        if sdulist is None:
            all_sdus = set(sdu_to_eng.keys())
        else:
            all_sdus = set(sdulist)

        # Set all existing SDUs to max
        for sdu in self.save.sdu_list:
            sdu_key = sduobj_to_sdu[sdu.sdu_data_path]
            if sdu_key in all_sdus:
                all_sdus.remove(sdu_key)
                sdu.sdu_level = sdu_to_max[sdu_key]

        # If we're missing any, add them.
        for sdu in all_sdus:
            self.save.sdu_list.append(OakShared_pb2.OakSDUSaveGameData(
                sdu_data_path=sdu_to_sduobj[sdu],
                sdu_level=sdu_to_max[sdu],
                ))

    def get_ammo_counts(self, eng=False):
        """
        Returns a dict containing the Ammo type and count.  The ammo type key will
        be a constant by default, or an English label if `eng` is `True`.
        """
        to_ret = {}
        for pool in self.save.resource_pools:
            # In some cases, Eridium can show up as an ammo type.  Related to the
            # Fabricator, presumably.  Anyway, just ignore it.
            if 'Eridium' in pool.resource_path:
                continue
            key = ammoobj_to_ammo[pool.resource_path]
            if eng:
                key = ammo_to_eng[key]
            to_ret[key] = int(pool.amount)
        return to_ret

    def get_ammo_count(self, ammo):
        """
        Returns the ammo count for the specified ammo type
        """
        ammo_vals = self.get_ammo_counts()
        if ammo in ammo_vals:
            return ammo_vals[ammo]
        return 0

    def set_max_ammo(self):
        """
        Sets our ammo counts to be at the max level
        """

        # Set all existing ammo pools to max (shouldn't have to worry about
        # pools not being in here)
        for pool in self.save.resource_pools:
            if pool.resource_path in ammoobj_to_ammo:
                ammo_key = ammoobj_to_ammo[pool.resource_path]
                pool.amount = ammo_to_max[ammo_key]

    def get_interesting_challenges(self, eng=False):
        """
        Returns a dict containing the challenge type and completed status.  The challenge
        type key will be a constant by default, or an English label if `eng` is `True`
        """
        to_ret = {}
        for chal in self.save.challenge_data:
            if chal.challenge_class_path in challengeobj_to_challenge:
                chal_type = challengeobj_to_challenge[chal.challenge_class_path]
                if chal_type not in challenge_char_lock or challenge_char_lock[chal_type] == self.get_class():
                    if eng:
                        chal_type = challenge_to_eng[chal_type]
                    to_ret[chal_type] = chal.currently_completed
        return to_ret

    def get_interesting_challenge(self, chal_type):
        """
        Returns the status of the given challenge type
        """
        challenges = self.get_interesting_challenges()
        if chal_type in challenges:
            return challenges[chal_type]
        return None

    def unlock_challenge_obj(self, challenge_obj, completed_count=1, progress_level=0):
        """
        Unlock the given challenge object.  Not sure what `progress_level`
        does, honestly.  Presumably `completed_count` would be useful for the
        more user-visible challenges on the map menu.  The ones that we're
        primarily concerned with here will just have 1 for it, though.
        """
        # First look for existing objects (should always be here, I think)
        for chal in self.save.challenge_data:
            if chal.challenge_class_path == challenge_obj:
                chal.currently_completed = True
                chal.is_active = False
                chal.completed_count = completed_count
                chal.progress_counter = 0
                chal.completed_progress_level = progress_level
                return

        # AFAIK we should never get here; rather than create a new one,
        # I'm just going to raise an Exception for now.
        raise Exception('Challenge not found: {}'.format(challenge_obj))

    def unlock_challenge(self, chal_type):
        """
        Unlocks the given challenge type
        """
        self.unlock_challenge_obj(challenge_to_challengeobj[chal_type])

    def unlock_char_com_challenge(self):
        """
        Special-case routine to unlock the appropriate challenge for COM slot, which
        will depend on what character we are.
        """
        char_class = self.get_class()
        if char_class == BEASTMASTER:
            self.unlock_challenge(COM_BEASTMASTER)
        elif char_class == GUNNER:
            self.unlock_challenge(COM_GUNNER)
        elif char_class == OPERATIVE:
            self.unlock_challenge(COM_OPERATIVE)
        elif char_class == SIREN:
            self.unlock_challenge(COM_SIREN)
        else:
            # How in the world would we get here?
            raise Exception('Unknown character class: {}'.format(char_class))

    def get_vehicle_chassis_counts(self, eng=False):
        """
        Returns a dict containing the vehicle type and a count of unlocked chassis for
        the vehicle.  The vehicle type key will be a constant by default, or an English
        label if `eng` is `True`
        """
        to_ret = {}
        for v in self.save.vehicles_unlocked_data:
            key = chassis_to_vehicle[v.asset_path]
            if eng:
                key = vehicle_to_eng[key]
            if key in to_ret:
                to_ret[key] += 1
            else:
                to_ret[key] = 1
        return to_ret

    def get_vehicle_chassis_count(self, vehicle_type):
        """
        Given a vehicle type, return the number of chassis types that are unlocked
        """
        counts = self.get_vehicle_chassis_counts()
        if vehicle_type in counts:
            return counts[vehicle_type]
        return 0

    def unlock_vehicle_chassis(self, vehicle_type=None):
        """
        Unlocks vehicle chassis types for the specified `vehicle_type`, or for all
        vehicle types if a type is not specified
        """
        # Construct a list of types
        if vehicle_type:
            types = [vehicle_type]
        else:
            types = [OUTRUNNER, TECHNICAL, CYCLONE]

        # Construct a set of all currently-unlocked chassis types
        cur_unlocks = set([v.asset_path for v in self.save.vehicles_unlocked_data])

        # Now add in any parts which aren't already part of that
        for vehicle_type in types:
            for part in vehicle_chassis[vehicle_type]:
                if part not in cur_unlocks:
                    self.save.vehicles_unlocked_data.append(OakSave_pb2.VehicleUnlockedSaveGameData(
                        asset_path=part,
                        just_unlocked=True,
                        ))

    def _get_vehicle_part_counts(self, p2v_map, eng=False):
        """
        Returns a dict containing the vehicle type and a count of unlocked
        parts (minus wheels, which are part of the chassis definition) for the
        vehicle, using the specified `p2v_map` for the part mapping.  This is
        generalized because we are separating out "functional" parts from
        skins.  The only reasonable values for `p2v_map` are `part_to_vehicle`
        and `skin_to_vehicle`, both found in `__init__.py`.  The vehicle type
        key will be a constant by default, or an English label if `eng` is
        `True`
        """
        to_ret = {}
        for part in self.save.vehicle_parts_unlocked:
            if part in p2v_map:
                key = p2v_map[part]
                if eng:
                    key = vehicle_to_eng[key]
                if key in to_ret:
                    to_ret[key] += 1
                else:
                    to_ret[key] = 1
        return to_ret

    def get_vehicle_part_counts(self, eng=False):
        """
        Returns a dict containing the vehicle type and a count of unlocked parts (minus
        wheels, which are part of the chassis definition) for the vehicle.  The vehicle
        type key will be a constant by default, or an English label if `eng` is `True`
        """
        return self._get_vehicle_part_counts(part_to_vehicle, eng=eng)

    def get_vehicle_skin_counts(self, eng=False):
        """
        Returns a dict containing the vehicle type and a count of unlocked
        skins for the vehicle.  The vehicle type key will be a constant by
        default, or an English label if `eng` is `True`
        """
        return self._get_vehicle_part_counts(skin_to_vehicle, eng=eng)

    def _get_vehicle_part_count(self, vehicle_type, generic_count_func):
        """
        Given a vehicle type, return the number of parts (minus wheels, which
        are part of the chassis definition) that are unlocked, using the
        specified `generic_count_func` to get the counts for all vehicle types.
        This is generalized because we are separating out "functional" parts
        from skins.  The only reasonable values for `generic_count_func` are
        `self.get_vehicle_part_counts` and `self.get_vehicle_skin_counts`.
        """
        counts = generic_count_func()
        if vehicle_type in counts:
            return counts[vehicle_type]
        return 0

    def get_vehicle_part_count(self, vehicle_type):
        """
        Given a vehicle type, return the number of parts (minus wheels, which are part
        of the chassis definition) that are unlocked.
        """
        return self._get_vehicle_part_count(vehicle_type, self.get_vehicle_part_counts)

    def get_vehicle_skin_count(self, vehicle_type):
        """
        Given a vehicle type, return the number of skins that are unlocked.
        """
        return self._get_vehicle_part_count(vehicle_type, self.get_vehicle_skin_counts)

    def _unlock_vehicle_parts(self, part_struct, vehicle_type=None):
        """
        Unlocks vehicle parts for the specified `vehicle_type`, or for all
        vehicle types if a type is not specified, using the specified
        `part_struct` to know which parts to unlock.  This is generalized
        because we are separating out "functional" parts from skins.  The only
        reasonable values for `part_struct` are `vehicle_parts` and
        `vehicle_skins`.
        """
        # Construct a list of types
        if vehicle_type:
            types = [vehicle_type]
        else:
            types = [OUTRUNNER, TECHNICAL, CYCLONE]

        # Construct a set of all currently-unlocked chassis types
        cur_parts = set(self.save.vehicle_parts_unlocked)

        # Now add in any parts which aren't already part of that
        for vehicle_type in types:
            for part in part_struct[vehicle_type]:
                if part not in cur_parts:
                    self.save.vehicle_parts_unlocked.append(part)

    def unlock_vehicle_parts(self, vehicle_type=None):
        """
        Unlocks vehicle parts for the specified `vehicle_type`, or for all
        vehicle types if a type is not specified
        """
        return self._unlock_vehicle_parts(vehicle_parts)

    def unlock_vehicle_skins(self, vehicle_type=None):
        """
        Unlocks vehicle skins for the specified `vehicle_type`, or for all
        vehicle types if a type is not specified
        """
        return self._unlock_vehicle_parts(vehicle_skins)

