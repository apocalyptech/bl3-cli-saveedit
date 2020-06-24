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

# The encryption/decryption stanzas in BL3Profile.__init__
# were helpfully provided by Gibbed (rick 'at' gibbed 'dot' us), so many
# thanks for that!  https://gist.github.com/gibbed/b6a93f74c575ce99b42c3b629ac1856a
#
# The rest of the savegame format was gleaned from 13xforever/Ilya's
# "gvas-converter" project: https://github.com/13xforever/gvas-converter

import base64
import struct
import google.protobuf
import google.protobuf.json_format
from . import *
from . import datalib
from . import OakProfile_pb2, OakShared_pb2

class BL3ProfItem(datalib.BL3Serial):
    """
    Pretty thin wrapper around the serial number for an item.  Mostly
    just so we can keep track of what index it is in the profile.
    """

    def __init__(self, serial_number, container, index, datawrapper):
        self.container = container
        self.index = index
        super().__init__(serial_number, datawrapper)

    @staticmethod
    def create(serial_number, container, datawrapper):
        """
        Creates a new item with the specified serial number, in the specified
        `container`
        """
        return BL3ProfItem(serial_number, container, -1, datawrapper)

    def _update_superclass_serial(self):
        """
        Action to take when our serial number gets updated.  In this case,
        overwriting our position in the containing list.
        """
        if self.index >= 0:
            self.container[self.index] = self.serial

class BL3Profile(object):
    """
    Wrapper around the protobuf object for a BL3 profile file.

    Only tested on PC versions.  Thanks to Gibbed for the encryption method and
    the Protobuf definitions!

    https://gist.github.com/gibbed/b6a93f74c575ce99b42c3b629ac1856a

    All these getters/setters are rather un-Pythonic; should be using
    some decorations for that instead.  Alas!
    """

    _prefix_magic = bytearray([
        0xD8, 0x04, 0xB9, 0x08, 0x5C, 0x4E, 0x2B, 0xC0,
        0x61, 0x9F, 0x7C, 0x8D, 0x5D, 0x34, 0x00, 0x56,
        0xE7, 0x7B, 0x4E, 0xC0, 0xA4, 0xD6, 0xA7, 0x01,
        0x14, 0x15, 0xA9, 0x93, 0x1F, 0x27, 0x2C, 0x8F,
        ])

    _xor_magic = bytearray([
        0xE8, 0xDC, 0x3A, 0x66, 0xF7, 0xEF, 0x85, 0xE0,
        0xBD, 0x4A, 0xA9, 0x73, 0x57, 0x99, 0x30, 0x8C,
        0x94, 0x63, 0x59, 0xA8, 0xC9, 0xAE, 0xD9, 0x58,
        0x7D, 0x51, 0xB0, 0x1E, 0xBE, 0xD0, 0x77, 0x43,
        ])

    def __init__(self, filename, debug=False):
        self.filename = filename
        self.datawrapper = datalib.DataWrapper()
        with open(filename, 'rb') as df:

            header = df.read(4)
            assert(header == b'GVAS')

            self.sg_version = self._read_int(df)
            if debug:
                print('Profile version: {}'.format(self.sg_version))
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
                print('Profile type: {}'.format(sg_type))

            # Read in the actual data
            remaining_data_len = self._read_int(df)
            data = bytearray(df.read(remaining_data_len))

            # Decrypt
            for i in range(len(data)-1, -1, -1):
                if i < 32:
                    b = BL3Profile._prefix_magic[i]
                else:
                    b = data[i - 32]
                b ^= BL3Profile._xor_magic[i % 32]
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
        self.prof = OakProfile_pb2.Profile()
        try:
            self.prof.ParseFromString(data)
        except google.protobuf.message.DecodeError as e:
            raise Exception('Unable to parse profile (did you pass a savegame, instead?): {}'.format(e)) from None

    def import_json(self, json_str):
        """
        Given JSON data, convert to protobuf and load it into ourselves so
        that we can work with it.  This also sets up a few convenience vars
        for our later use
        """
        message = google.protobuf.json_format.Parse(json_str, OakProfile_pb2.Profile())
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
            data = bytearray(self.prof.SerializeToString())

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
            df.write(self.prof.SerializeToString())

    def save_json_to(self, filename):
        """
        Saves a JSON version of our protobuf to the specfied filename
        """
        with open(filename, 'w') as df:
            df.write(google.protobuf.json_format.MessageToJson(self.prof,
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

    def get_sdus(self, eng=False):
        """
        Returns a dict containing the SDU type and the number purchased.  The SDU
        type key will be a constant by default, or an English label if `eng` is `True`
        """
        to_ret = {}
        for psdu in self.prof.profile_sdu_list:
            key = psduobj_to_psdu[psdu.sdu_data_path]
            if eng:
                key = psdu_to_eng[key]
            to_ret[key] = psdu.sdu_level
        return to_ret

    def get_sdus_with_max(self, eng=False):
        """
        Returns a dict whose keys are the SDU type, and the values are tuples with
        two values:
            1. The number of that SDU type purchased
            2. The maximum number of SDUs available for that type
        The SDU type key will be a constant by default, or an English label if
        `eng` is `True`.  This is just a convenience function suitable for
        giving more information to users.
        """
        to_ret = {}
        for psdu in self.prof.profile_sdu_list:
            key = psduobj_to_psdu[psdu.sdu_data_path]
            max_sdus = psdu_to_max[key]
            if eng:
                key = psdu_to_eng[key]
            to_ret[key] = (psdu.sdu_level, max_sdus)
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
            all_sdus = set(psdu_to_eng.keys())
        else:
            all_sdus = set(sdulist)

        # Set all existing SDUs to max
        for psdu in self.prof.profile_sdu_list:
            sdu_key = psduobj_to_psdu[psdu.sdu_data_path]
            if sdu_key in all_sdus:
                all_sdus.remove(sdu_key)
                psdu.sdu_level = psdu_to_max[sdu_key]

        # If we're missing any, add them.
        for psdu in all_sdus:
            self.prof.profile_sdu_list.append(OakShared_pb2.OakSDUSaveGameData(
                sdu_data_path=psdu_to_psduobj[psdu],
                sdu_level=psdu_to_max[psdu],
                ))

    def create_new_item(self, item_serial):
        """
        Creates a new item (as a BL3ProfItem object) from the given binary `item_serial`,
        which can later be added to our item bank list.
        """

        # Create the item and return it
        return BL3ProfItem.create(item_serial, self.prof.bank_inventory_list, self.datawrapper)

    def create_new_item_encoded(self, item_serial_b64):
        """
        Creates a new item (as a BL3ProfItem object) from the base64-encoded (and
        "BL3()"-wrapped) `item_serial_b64`, which can later be added to our item
        list.
        """
        return self.create_new_item(datalib.BL3Serial.decode_serial_base64(item_serial_b64))

    def get_lostloot_items(self):
        """
        Returns a list of this profile's Lost Loot items, as BL3ProfItem objects.
        """
        return [BL3ProfItem(s, self.prof.lost_loot_inventory_list, idx, self.datawrapper) for idx, s in enumerate(self.prof.lost_loot_inventory_list)]

    def get_bank_items(self):
        """
        Returns a list of this profile's bank items, as BL3ProfItem objects.
        """
        return [BL3ProfItem(s, self.prof.bank_inventory_list, idx, self.datawrapper) for idx, s in enumerate(self.prof.bank_inventory_list)]

    def add_bank_item(self, item_serial):
        """
        Adds a new item to our item list using `item_serial`, which should either
        be a `BL3ProfItem` object or a raw-data serial number.
        """
        if type(item_serial) == BL3ProfItem:
            self.prof.bank_inventory_list.append(item_serial.get_serial_number())
        else:
            self.prof.bank_inventory_list.append(item_serial)

    def get_cur_customizations(self, cust_set):
        """
        Returns a set of the currently-unlocked customizations which live in the
        given `cust_set`.  (A variety of customization types all live in the same
        data structure in the savegame, which is why we have this layer.)
        """
        to_ret = set()
        for cust in self.prof.unlocked_customizations:
            if cust.customization_asset_path in cust_set:
                to_ret.add(cust.customization_asset_path)
        return to_ret

    def get_cur_weapon_customizations(self, cust_set):
        """
        Returns a set of the currently-unlocked weapon customizations which
        live in the given `cust_set`, composed of their in-game hashes.  (Both
        trinkets and weapon skins live in the same data structure, which is why
        we have this layer.)
        """
        to_ret = set()
        for cust in self.prof.unlocked_inventory_customization_parts:
            if cust.customization_part_hash in cust_set:
                to_ret.add(cust.customization_part_hash)
        return to_ret

    def unlock_customization_set(self, cust_set):
        """
        Unlocks the given set of customizations in the main customization
        area.
        """
        current_custs = self.get_cur_customizations(cust_set)
        missing = cust_set - current_custs
        for cust in missing:
            self.prof.unlocked_customizations.append(OakProfile_pb2.OakCustomizationSaveGameData(
                is_new=True,
                customization_asset_path=cust,
                ))

    def unlock_weapon_customization_set(self, cust_dict):
        """
        Unlocks the given set of weapon customizations, given a `cust_dict` whose
        keys are the customization hashes.
        """
        current_custs = self.get_cur_weapon_customizations(cust_dict)
        missing = set(cust_dict.keys()) - current_custs
        for cust in missing:
            self.prof.unlocked_inventory_customization_parts.append(OakProfile_pb2.OakInventoryCustomizationPartInfo(
                customization_part_hash=cust,
                is_new=True,
                ))

    def get_char_skins_total(self):
        """
        Returns the total number of skins that are possible to unlock.  Includes the
        skins that are unlocked by default (just one per char).
        """
        return len(profile_skins) + len(profile_skins_defaults)

    def get_char_skins(self):
        """
        Returns a set of the current character skins which are unlocked.  Includes the
        skins that are unlocked by default (just one per char).
        """
        return self.get_cur_customizations(profile_skins) | profile_skins_defaults

    def unlock_char_skins(self):
        """
        Unlocks all character skins
        """
        self.unlock_customization_set(profile_skins)

    def get_char_heads_total(self):
        """
        Returns the total number of heads that are possible to unlock.  Includes the
        heads that are unlocked by default (just one per char).
        """
        return len(profile_heads) + len(profile_heads_defaults)

    def get_char_heads(self):
        """
        Returns a set of the current character heads which are unlocked.  Includes the
        heads that are unlocked by default (just one per char).
        """
        return self.get_cur_customizations(profile_heads) | profile_heads_defaults

    def unlock_char_heads(self):
        """
        Unlocks all character heads
        """
        self.unlock_customization_set(profile_heads)

    def get_echo_themes_total(self):
        """
        Returns the total number of ECHO themes that are possible to unlock.  Includes
        the ECHO theme that is unlocked by default.
        """
        return len(profile_echothemes) + len(profile_echothemes_defaults)

    def get_echo_themes(self):
        """
        Returns a set of the current ECHO themes which are unlocked.  Includes the
        ECHO theme that is unlocked by default.
        """
        return self.get_cur_customizations(profile_echothemes) | profile_echothemes_defaults

    def unlock_echo_themes(self):
        """
        Unlocks all ECHO Themes
        """
        self.unlock_customization_set(profile_echothemes)

    def get_emotes_total(self):
        """
        Returns the total number of emotes that are possible to unlock.  Includes the
        emotes that are unlocked by default (four per char).
        """
        return len(profile_emotes) + len(profile_emotes_defaults)

    def get_emotes(self):
        """
        Returns a set of the current emotes which are unlocked.  Includes the emotes
        that are unlocked by default (four per char).
        """
        return self.get_cur_customizations(profile_emotes) | profile_emotes_defaults

    def unlock_emotes(self):
        """
        Unlocks all emotes
        """
        self.unlock_customization_set(profile_emotes)

    def get_room_decos_total(self):
        """
        Returns the total number of room decorations that are possible to unlock.
        """
        return len(profile_roomdeco_obj_to_eng)

    def get_room_decos(self):
        """
        Returns a set of the current room decorations which are unlocked.
        """
        return set([d.decoration_item_asset_path for d in self.prof.unlocked_crew_quarters_decorations])

    def unlock_room_decos(self):
        """
        Unlocks all room decorations
        """
        current_custs = self.get_room_decos()
        missing = set(profile_roomdeco_obj_to_eng.keys()) - current_custs
        for cust in missing:
            self.prof.unlocked_crew_quarters_decorations.append(OakProfile_pb2.CrewQuartersDecorationItemSaveGameData(
                is_new=True,
                decoration_item_asset_path=cust,
                ))

    def get_weapon_skins_total(self):
        """
        Returns the total number of weapon skins that are possible to unlock
        """
        return len(profile_weaponskins_obj_to_eng)

    def get_weapon_skins(self, eng=False):
        """
        Returns a set of the current weapon skins which are unlocked.  By default
        these will be the hashes used in the save file, but if `eng` is `True`, they
        will be the english names of the skins.
        """
        if eng:
            return set([
                profile_weaponskins_hash_to_eng[h] for h in self.get_weapon_skins()
                ])
        else:
            return self.get_cur_weapon_customizations(profile_weaponskins_hash_to_eng)

    def unlock_weapon_skins(self):
        """
        Unlocks all weapon skins
        """
        self.unlock_weapon_customization_set(profile_weaponskins_hash_to_eng)

    def get_weapon_trinkets_total(self):
        """
        Returns the total number of weapon trinkets that are possible to unlock
        """
        return len(profile_weapontrinkets_obj_to_eng)

    def get_weapon_trinkets(self, eng=False):
        """
        Returns a set of the current weapon trinkets which are unlocked.  By default
        these will be the hashes used in the save file, but if `eng` is `True`, they
        will be the english names of the trinkets, if possible.
        """
        if eng:
            return set([
                profile_weapontrinkets_hash_to_eng[h] for h in self.get_weapon_trinkets()
                ])
        else:
            return self.get_cur_weapon_customizations(profile_weapontrinkets_hash_to_eng)

    def unlock_weapon_trinkets(self):
        """
        Unlocks all weapon trinkets
        """
        self.unlock_weapon_customization_set(profile_weapontrinkets_hash_to_eng)

    def clear_all_customizations(self):
        """
        Removes all unlocked customizations.
        """
        # It didn't seem worth coding these individually, since multiple customization
        # types exist for most of these.  Whatever.
        del self.prof.unlocked_customizations[:]
        del self.prof.unlocked_crew_quarters_decorations[:]
        del self.prof.unlocked_inventory_customization_parts[:]

    def alphabetize_cosmetics(self):
        """
        Room Decorations, Trinkets, and Weapon Skins just show up in the UI in the
        same order that they were unlocked, which can be annoying.  This will make
        all of those alphabetized so that they show up in a nice ordered list.
        """

        # First, decorations
        cur_decos = {}
        for d in self.prof.unlocked_crew_quarters_decorations:
            cur_decos[d.decoration_item_asset_path] = d.is_new
        new_order = []
        for name, obj_path in sorted(profile_roomdeco_eng_to_obj.items(), key=lambda i: i[0].casefold()):
            if obj_path in cur_decos:
                new_order.append((obj_path, cur_decos[obj_path]))
                del cur_decos[obj_path]
        # Don't forget to add any in that we don't actually know about.  At the end is fine.
        for obj_path, is_new in cur_decos.items():
            new_order.append((obj_path, is_new))
        # Now do the rearranging
        del self.prof.unlocked_crew_quarters_decorations[:]
        for obj_path, is_new in new_order:
            self.prof.unlocked_crew_quarters_decorations.append(OakProfile_pb2.CrewQuartersDecorationItemSaveGameData(
                is_new=is_new,
                decoration_item_asset_path=obj_path,
                ))

        # Then, weapon skins and trinkets
        cur_custs = {}
        for c in self.prof.unlocked_inventory_customization_parts:
            cur_custs[c.customization_part_hash] = c.is_new
        new_order = []
        for name, hashval in sorted(profile_weaponskins_eng_to_hash.items(), key=lambda i: i[0].casefold()):
            if hashval in cur_custs:
                new_order.append((hashval, cur_custs[hashval]))
                del cur_custs[hashval]
        for name, hashval in sorted(profile_weapontrinkets_eng_to_hash.items(), key=lambda i: i[0].casefold()):
            if hashval in cur_custs:
                new_order.append((hashval, cur_custs[hashval]))
                del cur_custs[hashval]
        # Don't forget to add any in that we don't actually know about.  At the end is fine.
        for hashval, is_new in cur_custs.items():
            new_order.append((hashval, is_new))
        del self.prof.unlocked_inventory_customization_parts[:]
        for hashval, is_new in new_order:
            self.prof.unlocked_inventory_customization_parts.append(OakProfile_pb2.OakInventoryCustomizationPartInfo(
                customization_part_hash=hashval,
                is_new=is_new,
                ))

    def get_golden_keys(self):
        """
        Returns the number of golden keys stored on this profile
        """
        for cat in self.prof.bank_inventory_category_list:
            if cat.base_category_definition_hash == goldenkey_hash:
                return cat.quantity
        return 0

    def set_golden_keys(self, num_keys):
        """
        Sets the number of golden keys to `num_keys`
        """
        for cat in self.prof.bank_inventory_category_list:
            if cat.base_category_definition_hash == goldenkey_hash:
                cat.quantity = num_keys
                return

        # If we got here, apparently this profile hasn't seen golden keys at all
        self.prof.bank_inventory_category_list.append(OakShared_pb2.InventoryCategorySaveData(
            base_category_definition_hash=goldenkey_hash,
            quantity=num_keys
            ))

    def fixup_guardian_rank(self, force=True):
        """
        Fixes Guardian Rank, based on the redeemed rewards and available tokens.
        When `force` is `True` (the default), it will always set the value it
        thinks is right.  When `force` is `False`, though, it will only *raise*
        the GR if need be, but not lower it.  Returns the new Guardian Rank
        if it was changed, or `None` otherwise.
        """
        min_guardian_rank_level = sum([r.num_tokens for r in self.prof.guardian_rank.rank_rewards])
        min_guardian_rank_level += self.prof.guardian_rank.available_tokens

        # Figure out if we should set the value or not
        set_value = False
        if force and self.prof.guardian_rank.guardian_rank != min_guardian_rank_level:
            set_value = True
        elif not force and self.prof.guardian_rank.guardian_rank < min_guardian_rank_level:
            set_value = True

        # Now do it (or not)
        if set_value:
            self.prof.guardian_rank.guardian_rank = min_guardian_rank_level
            return min_guardian_rank_level
        else:
            return None

    def get_guardian_rank(self):
        """
        Gets our current guardian rank
        """
        return self.prof.guardian_rank.guardian_rank

    def get_guardian_rank_tokens(self):
        """
        Gets our available guardian rank token count
        """
        return self.prof.guardian_rank.available_tokens

    def set_guardian_rank_tokens(self, tokens):
        """
        Sets our available guardian rank token count.  Will increase the profile's
        Guardian Rank to suit, if needed, and will return the new Guardian Rank
        if that was required (or `None` otherwise).
        """
        self.prof.guardian_rank.available_tokens = tokens
        return self.fixup_guardian_rank(force=False)

    def zero_guardian_rank(self):
        """
        Resets this profile's Guardian Rank to zero.
        """
        # Leaving `guardian_reward_random_seed` alone, I guess?
        # `guardian_experience` is an old value that's no longer used; the real new
        # var is `new_guardian_experience`.
        self.prof.guardian_rank.available_tokens = 0
        del self.prof.guardian_rank.rank_rewards[:]
        self.prof.guardian_rank.guardian_rank = 0
        self.prof.guardian_rank.guardian_experience = 0
        self.prof.guardian_rank.new_guardian_experience = 0

    def set_guardian_rank_reward_levels(self, points, force=True):
        """
        Sets the given number of `points` in each of the guardian rank rewards.
        Will also raise our Guardian Rank level upwards if appropriate.  If
        `force` is `True`, we will set the given level regardless of the current
        values.  If it is `False`, we will only *increase* the reward level,
        never decrease.  Returns the new `guardian_rank` level, if it is
        changed (or `None` otherwise).
        """

        # Set any existing records appropriately
        rewards_to_set = set(list(guardian_rank_rewards))
        for reward in self.prof.guardian_rank.rank_rewards:
            if reward.reward_data_path in rewards_to_set:
                rewards_to_set.remove(reward.reward_data_path)
                if force or reward.num_tokens < points:
                    reward.num_tokens = points

        # If we're missing any, add them.
        for reward in rewards_to_set:
            self.prof.guardian_rank.rank_rewards.append(OakProfile_pb2.GuardianRankRewardSaveGameData(
                num_tokens=points,
                reward_data_path=reward,
                ))

        # Now fix up Guardian Rank level, if needed
        return self.fixup_guardian_rank()

    def min_guardian_rank(self):
        """
        Sets our guardian rank to the lowest level possible such that we won't get
        overwritten by savegames that get loaded (as opposed to `zero_guardian_rank()`).
        Namely, 18 Guardian Rank, and a single point in each Reward.  Will return the
        new guardian rank.
        """
        self.prof.guardian_rank.guardian_rank = 0
        self.prof.guardian_rank.available_tokens = 0
        self.prof.guardian_rank.guardian_experience = 0
        self.prof.guardian_rank.new_guardian_experience = 0
        return self.set_guardian_rank_reward_levels(1, force=True)

