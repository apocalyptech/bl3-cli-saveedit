#!/usr/bin/env python3
# vim: set expandtab tabstop=4 shiftwidth=4:

import io
import json
import lzma
import struct
import base64
import random
import binascii
import pkg_resources

from . import *

class ArbitraryBits(object):
    """
    Ridiculous little object to deal with variable-bit-length packed data that
    we find inside item serial numbers.  This is super-inefficient on the
    large scale, but given that we're likely to only be dealing with hundreds of
    items at the absolute most (and more likely only dozens), it probably doesn't
    matter.

    Rather than doing clever things with bitwise operations and shifting data
    around, we're convering all the data into a string where each letter is a
    0 or 1, so we can just use regular Python indexing and slicing to do whatever
    we want with them.  A call to `int(data, 2)` on the string (or a bit of the
    string) will convert it back into a number for us.

    Many bits of data will span byte boundaries, and to properly handle the way
    they're packed, we're actually storing the data in backwards chunks of 8
    bits.  So when we mention the "front" of the data, we'll actually end up
    looking at the *end* of our internally-stored data, and vice-versa.  "Front"
    and "back" are used as if you're looking at the actual binary representation,
    not our own janky internal model.
    """

    def __init__(self, data=b''):
        self.data = ''.join([f'{d:08b}' for d in reversed(data)])

    def eat(self, bits):
        """
        Eats the specified number of `bits` off the front of the
        data and returns the value.  This is destructive; the data
        eaten off the front will no longer be in the data.
        """
        if bits > len(self.data):
            raise Exception('Attempted to read {} bits, but only {} remain'.format(bits, len(self.data)))
        val = int(self.data[-bits:], 2)
        self.data = self.data[:-bits]
        return val

    def append_value(self, value, bits):
        """
        Feeds the given `value` to the end of the data, using the given
        number of `bits` to do so.  We're assuming that `value` is
        an unsigned number.
        """
        value_data = struct.pack('>I', value)
        value_txt = ''.join([f'{d:08b}' for d in value_data])
        self.data = value_txt[-bits:] + self.data

    def append_data(self, new_data):
        """
        Appends the given `new_data` (from another ArbitraryBits object)
        to the end of our data.
        """
        self.data = new_data + self.data

    def get_data(self):
        """
        Returns our current data in binary format.  Will bad the end with
        `0` bits if we're not a multiple of 8.
        """
        # Pad with 0s if need be
        need_bits = (8-len(self.data)) % 8
        temp_data = '0'*need_bits + self.data

        # Now convert back to an actual bytearray
        byte_data = []
        for i in range(int(len(temp_data)/8)-1, -1, -1):
            byte_data.append(int(temp_data[i*8:(i*8)+8], 2))
        return bytearray(byte_data)

class BL3Serial(object):
    """
    Class to handle serializing and deserializing BL3 item/weapon serial
    numbers.
    """

    def __init__(self, serial, datawrapper):

        self.datawrapper = datawrapper
        self.serial_db = datawrapper.serial_db
        self.name_db = datawrapper.name_db
        self.invkey_db = datawrapper.invkey_db
        self.set_serial(serial)

    def _update_superclass_serial(self):
        """
        To be implemented by any superclass which wraps this serial number in
        a larger object (such as a savegame item structure or profile array).
        The serial itself will be available in `self.serial`.
        """
        pass

    def set_serial(self, serial):
        """
        Sets our serial number
        """

        self.serial = serial
        (self.decrypted_serial, self.orig_seed) = BL3Serial._decrypt_serial(serial)
        self.parsed = False
        self.parts_parsed = False
        self.can_parse = True
        self.can_parse_parts = True
        self.changed_parts = False

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

        # Additional data that gets filled in if we can parse parts
        self._part_invkey = None
        self._part_bits = None
        self._parts = None
        self._generic_bits = None
        self._generic_parts = None
        self._additional_data = None
        self._num_customs = None

        # Call out to any superclass procedures here
        self._update_superclass_serial()

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
        temp = BL3Serial._xor_data(data, seed)

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
        return bytearray(BL3Serial._xor_data(rotated, seed))

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
        decrypted = BL3Serial._bogodecrypt(serial[5:], orig_seed)

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
        return header + BL3Serial._bogoencrypt(checksum + data, seed)

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

    def _get_inv_db_header_part_repeated(self, category, bits, count_bits):
        """
        Given the category name `category` and the ArbitraryBits object `bits`,
        containing serial number data, and `count_bits`, which specifies the
        number of bits which make up the count of parts to read, returns a
        tuple containing:
            1) The number of bits each part in the category takes up
            2) A list containing tuples with the following:
                1) The part name
                2) The numerical index of the part
        """
        num_bits = self.serial_db.get_num_bits(category, self._version)
        parts = []
        num_parts = bits.eat(count_bits)
        for _ in range(num_parts):
            part_idx = bits.eat(num_bits)
            part_val = self.serial_db.get_part(category, part_idx)
            if not part_val:
                part_val = 'unknown'
            parts.append((part_val, part_idx))
        return (num_bits, parts)

    def _parse_serial(self):
        """
        Parse our serial number, at least up to the level.  We're not going
        to care about actual parts in here.
        """

        if not self.can_parse:
            return

        bits = ArbitraryBits(self.decrypted_serial)

        # First value should always be 128, apparently
        assert(bits.eat(8) == 128)

        # Grab the serial version and check it against the max version we know about
        self._version = bits.eat(7)
        if self._version > self.serial_db.max_version:
            self.can_parse = False
            self.can_parse_parts = False
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

        # Parse out a "short" balance name, for convenience's sake
        self._balance_short = self._balance.split('.')[-1]

        # If we know of an English name for this balance, use it
        self._eng_name = self.name_db.get(self._balance_short)

        # Mark down that we've parsed the basic info (we have enough to level up
        # gear at this point)
        self.parsed = True

        # Make a note of our remaining data - if we re-save without any parts
        # changes, we can just use this rather than reconstructing the whole
        # serial.
        self._remaining_data = bits.data

        # Now let's see if we can parse parts
        self._part_invkey = self.invkey_db.get(self._balance)
        if self._part_invkey is None:
            self.can_parse_parts = False
        else:

            # Let's assume at first that we're going to correctly parse all this
            self.parts_parsed = True

            # Read parts
            (self._part_bits, self._parts) = self._get_inv_db_header_part_repeated(
                    self._part_invkey, bits, 6)

            # Read generics (anointments+mayhem)
            (self._generic_bits, self._generic_parts) = self._get_inv_db_header_part_repeated(
                    'InventoryGenericPartData', bits, 4)

            # Read additional data (no idea for the most part; some item "wear"
            # is in here, we think.  Maybe other stuff, too?)
            additional_count = bits.eat(8)
            self._additional_data = []
            for _ in range(additional_count):
                self._additional_data.append(bits.eat(8))

            # Read in "customization" parts; this presumably used to be
            # trinkets+weaponskins, but was removed at some point.  If we
            # have anything but 0 in here, we're going to force `can_parse_parts`
            # to false, 'cause we don't know how many bits these things
            # might take if they're present.
            self._num_customs = bits.eat(4)
            if self._num_customs != 0:
                self.parts_parsed = False
                self.can_parse_parts = False

            # And read in our remaining data.  If there's more than 7 bits
            # left, we've done something wrong, because it should only be
            # zero-padding after all the "real" data is in place.
            if len(bits.data) > 7:
                self.parts_parsed = False
                self.can_parse_parts = False
            elif '1' in bits.data:
                # This is supposed to only be zero-padding at the moment, if
                # we see something else, abort
                self.parts_parsed = False
                self.can_parse_parts = False
            else:
                # Okay, we're good!  Don't bother saving the remaining 0 bits.
                pass

    def _deparse_serial(self):
        """
        De-parses a serial; used after we make changes to the data that gets
        pulled out during `_parse_serial`.  At the moment, that's both level
        changes and mayhem level changes.  Will end up calling out to the
        superclass's `_update_superclass_serial` to propagate the serial change
        to whatever containing structure needs it, and set the object to trigger a
        re-parse if anything else needs to read more.  That's probably overkill
        and makes this technically quite inefficient, especially when making
        multiple edits to the same item, but given the scale of processing,
        we'll probably be fine.
        """

        if not self.can_parse:
            return

        if self.changed_parts:
            # If we changed any parts, re-save using the latest serial version,
            # which means that we'll have to figure out new bit lengths for
            # everything.  I'm not doing this *all* the time because I like
            # changing as little as possible when doing these edits, and this
            # way we can do stuff like change the level of an item without
            # having to re-encode its parts.
            self._version = self.serial_db.max_version
            self._balance_bits = self.serial_db.get_num_bits('InventoryBalanceData', self._version)
            self._invdata_bits = self.serial_db.get_num_bits('InventoryData', self._version)
            self._manufacturer_bits = self.serial_db.get_num_bits('ManufacturerData', self._version)
            self._part_bits = self.serial_db.get_num_bits(self._part_invkey, self._version)
            self._generic_bits = self.serial_db.get_num_bits('InventoryGenericPartData', self._version)

        # Construct a new header
        bits = ArbitraryBits()
        bits.append_value(128, 8)
        bits.append_value(self._version, 7)
        bits.append_value(self._balance_idx, self._balance_bits)
        bits.append_value(self._invdata_idx, self._invdata_bits)
        bits.append_value(self._manufacturer_idx, self._manufacturer_bits)
        bits.append_value(self._level, 7)

        # Arguably we should *always* re-encode parts, if we're able to, just so this
        # function is less complex.  For now I'm keeping it like this, though.

        if self.changed_parts:
            # If we've changed parts, just write out everything again.  First parts
            bits.append_value(len(self._parts), 6)
            for (part_val, part_idx) in self._parts:
                bits.append_value(part_idx, self._part_bits)

            # Then generics
            bits.append_value(len(self._generic_parts), 4)
            for (part_val, part_idx) in self._generic_parts:
                bits.append_value(part_idx, self._generic_bits)

            # Then additional data
            bits.append_value(len(self._additional_data), 8)
            for value in self._additional_data:
                bits.append_value(value, 8)

            # Then our number of customs (should always be zero)
            bits.append_value(self._num_customs, 4)

        else:
            # Otherwise, we can re-use our original remaining data
            bits.append_data(self._remaining_data)

        # Read the serial back out of our structure
        new_data = bits.get_data()

        # Encode the new serial (using seed 0; unencrypted)
        new_serial = BL3Serial._encrypt_serial(new_data, 0)

        # Load in the new serial (this will set `parsed` to `False`)
        # It bothers me that I've just done an `_encrypt_serial` in the
        # previous statement, when this call to `set_serial` will just
        # turn right around and decrypt it again.  Alas.
        self.set_serial(new_serial)

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
        self._update_superclass_serial()

    def get_serial_number(self, orig_seed=False):
        """
        Returns the binary item serial number.  If `orig_seed` is `True`, the
        serial number will use the same seed that was used in the savegame.
        Otherwise, it will use a seed of `0`, which will then be unencrypted.
        """
        if orig_seed:
            seed = self.orig_seed
        else:
            seed = 0
        return BL3Serial._encrypt_serial(self.decrypted_serial, seed)

    def get_serial_base64(self, orig_seed=False):
        """
        Returns the base64-encoded item serial number.  If `orig_seed` is
        `True`, the serial number will use the same seed that was used in the
        savegame.  Otherwise, it will use a seed of `0`, which will then be
        unencrypted.
        """
        return 'BL3({})'.format(base64.b64encode(self.get_serial_number(orig_seed)).decode('latin1'))

    @staticmethod
    def decode_serial_base64(new_data):
        """
        Decodes a `BL3()`-encoded item serial into a binary serial
        """
        if not new_data.lower().startswith('bl3(') or not new_data.endswith(')'):
            raise Exception('Unknown item format: {}'.format(new_data))
        encoded = new_data[4:-1]
        return base64.b64decode(encoded)

    @property
    def mayhem_level(self):
        """
        Returns the current Mayhem level of the item, with `0` signifying
        that there is no Mayhem level present, and `None` signifying that
        the Mayhem level could not be parsed (due to being unable to parse the
        item parts)
        """
        if not self.parsed or not self.parts_parsed:
            self._parse_serial()
            if not self.can_parse or not self.can_parse_parts:
                return None
        # Given the presence of item editors, there could possibly be more
        # than one Mayhem part present in a serial (though they don't seem
        # to stack at all, so doing so would be pointless).  We'll just
        # abort processing as soon as we find one, which I suspect is likely
        # what the game does, too.
        for part_name, part_idx in self._generic_parts:
            if part_name.lower() in mayhem_part_lower_to_lvl:
                return mayhem_part_lower_to_lvl[part_name.lower()]
        return 0

    def can_have_mayhem(self):
        """
        Returns `True` if this is an item type which can have a mayhem level,
        or `False` otherwise.  Will also return `False` if we're unable to
        parse parts for the item.
        """
        if not self.parsed or not self.parts_parsed:
            self._parse_serial()
            if not self.can_parse or not self.can_parse_parts:
                return False
        return self._invdata.lower() in mayhem_invdata_lower_types

    def can_have_anointment(self):
        """
        Returns `True` if this is an item type which can have an anointment,
        or `False` otherwise.  Will also return `False` if we're unable to
        parse parts for the item.
        """
        if not self.parsed or not self.parts_parsed:
            self._parse_serial()
            if not self.can_parse or not self.can_parse_parts:
                return False
        return self._invdata.lower() in anointable_invdata_lower_types

    @mayhem_level.setter
    def mayhem_level(self, value):
        """
        Sets the given mayhem level on the item.  Returns `True` if we were
        able to do so, or `False` if not.
        """
        # The call to `can_have_mayhem` will parse the serial if possible,
        # so we'll be all set.
        if not self.can_have_mayhem():
            return False

        # Don't forget to set this
        self.changed_parts = True

        # First grab a list of any non-Mayhem parts (should just be anoints)
        new_parts = []
        for idx, (part_name, part_idx) in enumerate(self._generic_parts):
            if part_name.lower() not in mayhem_part_lower_to_lvl:
                new_parts.append((part_name, part_idx))

        # Now add our new one in
        if value > 0:
            new_mayhem_part = self.serial_db.get_part_index(
                    'InventoryGenericPartData',
                    mayhem_lvl_to_part[value],
                    )
            if new_mayhem_part is None:
                return False
            else:
                new_parts.append((mayhem_lvl_to_part[value], new_mayhem_part))

        # Aaaand assign our list of generic parts back
        self._generic_parts = new_parts

        # Re-serialize
        self._deparse_serial()
        self._update_superclass_serial()

        # return!
        return True

    def set_anointment(self, anointment):
        """
        Sets the given anointment on the item, if possible.  Returns `True` if we were
        able to do so, or `False` if not.  This does not do any checking to see if
        the anointment would be ordinarily "valid" for the given item type, but it does
        at least attempt to only apply if it's an item type which can ordinarily have
        anointments.

        This will overwrite any existing anointment part on the item in question.

        TODO: This routine currently assumes that any Generic part that's *not* a
        Mayhem Level part is an anointment, and will wipe those out before setting
        the specified part.  As of November 2020 this should be a safe assumption,
        but might not be in the future.  Should this functionality ever get exported
        though a "proper" CLI arg, we should really import a list of legit
        anointments to check against, just to assist in futureproofing.
        """

        # Check for anointment part validity first thing, before we do anything
        # else.
        new_anointment_part = self.serial_db.get_part_index(
                'InventoryGenericPartData',
                anointment,
                )
        if not new_anointment_part:
            raise Exception('ERROR: {} is not a known anointment'.format(anointment))

        # The call to `can_have_anointment` will parse the serial if possible,
        # so we'll be all set.
        if not self.can_have_anointment():
            return False

        # Don't forget to set this
        self.changed_parts = True

        # Start out with our new anointment part
        new_parts = [(anointment, new_anointment_part)]

        # Now add in any existing Mayhem parts (should just be the one, but
        # whatever)
        for idx, (part_name, part_idx) in enumerate(self._generic_parts):
            if part_name.lower() in mayhem_part_lower_to_lvl:
                new_parts.append((part_name, part_idx))

        # Aaaand assign our list of generic parts back
        self._generic_parts = new_parts

        # Re-serialize
        self._deparse_serial()
        self._update_superclass_serial()

        # return!
        return True

    def get_level_eng(self):
        """
        Returns an English representation of our level, including Mayhem level,
        suitable for reporting to a user.
        """
        # First, regular level
        level = self.level
        if level is None:
            return 'unknown lvl'
        to_ret = 'level {}'.format(level)

        # Then Mayhem
        mayhem_level = self.mayhem_level
        if mayhem_level is None:
            return '{}, mayhem unknown'.format(to_ret)
        elif mayhem_level > 0:
            return '{}, mayhem {}'.format(to_ret, mayhem_level)
        else:
            return to_ret

class InventorySerialDB(object):
    """
    Little wrapper to provide access to our inventory serial number DB
    """

    def __init__(self):
        self.initialized = False
        self.db = None
        self._max_version = -1
        self.part_cache = {}

    def _initialize(self):
        """
        Actually read in our data.  Not doing this automatically because I
        only want to do it if we're doing an operation which requires it.
        """
        if not self.initialized:
            with lzma.open(io.BytesIO(pkg_resources.resource_string(
                    __name__, 'resources/inventoryserialdb.json.xz'
                    ))) as df:
                self.db = json.load(df)
            self.initialized = True

            # I generally shy away from complex one-liners like this, but eh?
            self._max_version = max(
                    [max([v['version'] for v in category['versions']]) for category in self.db.values()]
                    )

    @property
    def max_version(self):
        """
        Return the max version we can handle
        """
        if not self.initialized:
            self._initialize()
        return self._max_version

    def get_num_bits(self, category, version):
        """
        Returns the number of bits used for the specified `category`, using
        a serial with version `version`
        """
        if not self.initialized:
            self._initialize()
        cur_bits = self.db[category]['versions'][0]['bits']
        for cat_version in self.db[category]['versions']:
            if cat_version['version'] > version:
                return cur_bits
            elif version >= cat_version['version']:
                cur_bits = cat_version['bits']
        return cur_bits

    def get_part(self, category, index):
        """
        Given the specified `category`, return the part for `index`
        """
        if not self.initialized:
            self._initialize()
        if index < 1:
            return None
        else:
            if index > len(self.db[category]['assets']):
                return None
            else:
                return self.db[category]['assets'][index-1]

    def get_part_index(self, category, part_name):
        """
        Find the correct index to use for the given `part_name`, inside the given
        `category`.  Will return `None` if the part cannot be found.
        """
        if not self.initialized:
            self._initialize()
        if category not in self.part_cache:
            self.part_cache[category] = {}
        if part_name not in self.part_cache[category]:
            for idx, asset_part_name in enumerate(self.db[category]['assets']):
                if part_name == asset_part_name:
                    self.part_cache[category][part_name] = idx+1
                    return idx+1
        if part_name in self.part_cache[category]:
            return self.part_cache[category][part_name]
        else:
            return None

class BalanceToName(object):
    """
    Little wrapper to provide access to a mapping from Balance names (actually
    just the "short" version of those, without path) to English names that
    we can report on.
    """

    def __init__(self):
        self.initialized = False
        self.mapping = None

    def _initialize(self):
        """
        Actually read in our data.  Not doing this automatically because I
        only want to do it if we're doing an operation which requires it.
        """
        if not self.initialized:
            with lzma.open(io.BytesIO(pkg_resources.resource_string(
                    __name__, 'resources/short_name_balance_mapping.json.xz'
                    ))) as df:
                self.mapping = json.load(df)
            self.initialized = True

    def get(self, balance):
        """
        Returns an english mapping for the given balance, if we can.
        """
        if not self.initialized:
            self._initialize()
        if '/' in balance:
            balance = balance.split('/')[-1]
        if '.' in balance:
            balance = balance.split('.')[-1]
        balance = balance.lower()
        if balance in self.mapping:
            return self.mapping[balance]
        else:
            return None

class BalanceToInvKey(object):
    """
    Little wrapper to provide access to a mapping from Balance names to
    the inventory key that we'd need to use to read its parts out.
    """

    def __init__(self):
        self.initialized = False
        self.mapping = None

    def _initialize(self):
        """
        Actually read in our data.  Not doing this automatically because I
        only want to do it if we're doing an operation which requires it.
        """
        if not self.initialized:
            with lzma.open(io.BytesIO(pkg_resources.resource_string(
                    __name__, 'resources/balance_to_inv_key.json.xz'
                    ))) as df:
                self.mapping = json.load(df)
            self.initialized = True

    def get(self, balance):
        """
        Returns the inventory key for the given balance, if we can.
        """
        if not self.initialized:
            self._initialize()
        if '.' not in balance:
            balance = '{}.{}'.format(balance, balance.split('/')[-1])
        balance = balance.lower()
        if balance in self.mapping:
            return self.mapping[balance]
        else:
            return None

class DataWrapper(object):
    """
    Weird little metaclass which just has an instance of each of our file-backed
    data objects in here.  This way apps using it can just pass around a single
    object instance and take what they want, rather than having to carry around
    multiple.  (For instance, BL3Item needs both InventorySerialDB and
    BalanceToName, and we instantiate a fair number of those.)
    """

    def __init__(self):
        self.serial_db = InventorySerialDB()
        self.name_db = BalanceToName()
        self.invkey_db = BalanceToInvKey()

