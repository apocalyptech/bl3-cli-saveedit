#!/usr/bin/env python3
# vim: set expandtab tabstop=4 shiftwidth=4:

import io
import json
import lzma
import struct
import pkg_resources

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

class InventorySerialDB(object):
    """
    Little wrapper to provide access to our inventory serial number DB
    """

    def __init__(self):
        self.initialized = False
        self.db = None

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
            return self.db[category]['assets'][index-1]

