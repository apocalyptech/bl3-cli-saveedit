Borderlands 3 Commandline Savefile Editor
=========================================

This project will eventually be a CLI savefile editor for Borderlands 3.

TODO
====

- The actual CLI editor bit
- Proper packaging (would like to get this on PyPI)
- Proper modularization (I think it's probably a bit weird at the moment)
- Something a bit more Enum-like for various things in `__init__.py`; I
  know that's not very Pythonic, but when dealing with extra-Python data
  formats, one must sometimes make exceptions.
- Figure out item serial number parsing (or, almost certainly, wait for
  someone else to figure it out and then take it from there, assuming
  a FOSS'd project. :)
  - This'll let us level up items in addition to characters
- Unit tests?

Credits
=======

The encryption/decryption stanzas in `BL3Save.__init__` and `BL3Save.save_to`
were helpfully provided by Gibbed (rick 'at' gibbed 'dot' us), so many
thanks for that!  The protobuf definitions are also provided by Gibbed, from
his [Borderlands3Protos](https://github.com/gibbed/Borderlands3Protos) repo,
and used with permission.

The rest of the savegame format was gleaned from 13xforever/Ilya's
`gvas-converter` project: https://github.com/13xforever/gvas-converter

License
=======

All code in this project is licensed under the
[zlib/libpng license](https://opensource.org/licenses/Zlib).  A copy is
provided in [COPYING.txt](COPYING.txt).

