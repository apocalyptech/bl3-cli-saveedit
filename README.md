# Borderlands 3 Commandline Savegame Editor

This project is a commandline Python-based Borderlands 3 Savegame
Editor.  It's a companion to the very similar
[CLI editor for BL2/TPS](https://github.com/apocalyptech/borderlands2),
and provides some very similar functionality.  It can be used
to level up your characters, unlock Mayhem modes early in the
game, unlock TVHM, add SDUs, unlock equipment slots, and more.
One thing it does *not* do yet is levelling up items/weapons.

This editor has only been tested on PC Savegames -- other platforms'
savegames are not supported at the moment.

Please keep the following in mind:

- This app does not have any graphical interface.  You must be
  on a commandline in order to use it.
- It does not provide any mechanisms for creating items/weapons,
  or even editing items/weapons in any useful fashion.
- While I have not experienced any data loss with the app,
  **take backups of your savegames before using this**, and
  keep in mind that it could end up corrupting your saves.  If
  you do encounter any data loss problems, please contact me
  and I'll try to at least fix whatever bug caused it.

# Installation

This editor requires [Python 3](https://www.python.org/), and has been
tested on 3.7 and 3.8.  It also requires the [protobuf package](https://pypi.org/project/protobuf/).

The easiest way to install this app is via `pip`.  Once Python 3 is
installed, you should be able to run this to install the app:

    pip install bl3-cli-saveedit

Once installed, there should be a few new commandline utilities available
to you.  The main editor is `bl3-save-edit`, and you can see its possible
arguments with `-h`/`--help`:

    bl3-save-edit -h

There's also a `bl3-save-info` utility which just shows some information
about a specified savefile.  You can see its possible arguments with
`-h`/`--help` as well:

    bl3-save-info -h

Finally, there's a utility which I'd used to generate my
[BL3 Savegame Archive Page](http://apocalyptech.com/games/bl-saves/bl3.php).
This one won't be useful to anyone but me, but you can view its arguments
as well, if you like:

    bl3-process-archive-saves -h

### Notes for People using Windows

This is a command-line utility, which means there's no graphical interface,
and you'll have to run it from either a Windows `cmd.exe` prompt, or presumably
running through PowerShell should work, too.  The first step is to
[install Python](https://www.python.org/downloads/windows/) -- grab what's
available in the 3.x series (at time of writing, that's either 3.8.2 or
3.7.7).  When you install, make sure to check the checkbox which says something
like "add to PATH", so that you can run Python from the commandline directly.

When it's installed, test that you can run it from the commandline.  Open up
either `cmd.exe` or PowerShell, and make sure that you see something like this
when you run `python -V`:

    C:\> python -V
    Python 3.8.2

If that works, you can then run the `pip install bl3-cli-saveedit` command
as mentioned above, and use the commandline scripts to edit to your heart's
content.

### Running from Github

Alternatively, if you want to download or run the Github version of
the app: clone the repository and then install `protobuf` (you can
use `pip install -r requirements.txt` to do so, though a `pip install protobuf`
will also work just fine).

You can then run the scripts directly from the Github checkout, though
you'll have to use a slightly different syntax.  Here are the equivalents:

    python -m bl3save.cli_edit -h
    python -m bl3save.cli_info -h
    python -m bl3save.cli_archive -h

# Editor Usage

This section will assume that you've installed via `pip` - if you're using
a Github checkout, substitute the commands as appropriate, as per the
Installation section above.

## Basic Operation

At its most basic, you can run the editor with only an input and output
file, and it will simply load and then re-encode the savegame.  For
instance, in this example, `old.sav` and `new.sav` will be identical as
far as BL3 is concerned:

    bl3-save-edit old.sav new.sav

If `new.sav` exists, the utility will prompt you if you want to overwrite
it.  If you want to force the utility to overwrite without asking,
use the `-f`/`--force` option:

    bl3-save-edit old.sav new.sav -f

As the app processes files, it will output exactly what it's doing.  If
you prefer to have silent output (unless there's an error), such as if
you're using this to process a group of files in a loop, you can use
the `-q`/`--quiet` option:

    bl3-save-edit old.sav new.sav -q

Note that even with no edits being performed, the output file will not
be identical to the original file, due to how Google's protobuf library
differs from the library used by BL3 itself.

## Output Formats

The editor can output files in a few different formats, and you can
specify the format using the `-o`/`--output` option, like so:

    bl3-save-edit old.sav new.sav -o savegame
    bl3-save-edit old.sav new.protobuf -o protobuf
    bl3-save-edit old.sav new.txt -o items

- **savegame** - This is the default, if you don't specify an output
  format.  It will save the game like a valid BL3 savegame.  This
  will likely be your most commonly-used option.
- **protobuf** - This will write out the raw, unencrypted Protobuf
  entries contained in the savegame, which might be useful if you
  want to look at them with a Protobuf viewer of some sort (such
  as [this one](https://protogen.marcgravell.com/decode)).  Note
  that the utility does not currently support reading raw protobuf
  data back in, so this is a write-only operation.
- **items** - This will output a text file containing item codes
  which can be read back in to other savegames.  It uses a format
  similar to the item codes used by Gibbed's BL2/TPS editors.
  (It will probably be identical to the codes used by Gibbed's BL3
  editor, once that is released, but time will tell on that front.)

## Modifying the Savegame

Here's a list of all the edits you can make to the savegame.  You
can specify as many of these as you want on the commandline, to
process multiple changes at once.

### Character Name

This can be done with the `--name` option:

    bl3-save-edit old.sav new.sav --name "Gregor Samsa"

### Save Game ID

Like with BL2/TPS, I suspect that this ID isn't at all important, but
the editor can set it anyway with the `--save-game-id` option.  BL3
itself sets the savegame ID to match the filename of the savegame, if
interpreted as a hex value (so `10.sav` would have an ID of `16`).

    bl3-save-edit old.sav new.sav --save-game-id 2

### Character Level

You can set your character to a specific level using `--level <num>`,
or to the max level allowed by the game using `--level-max`

    bl3-save-edit old.sav new.sav --level 20
    bl3-save-edit old.sav new.sav --level-max

### Mayhem Level

This is only really useful before you've got Mayhem Mode unlocked.
You can use the `--mayhem` argument to activate Mayhem mode even from
the very beginning of the game.  Note that you still won't have access
to the Mayhem console on Sanctuary until it's properly unlocked by the
game, so this will be the only way of changing Mayhem mode until that
point in the game.  This will set the Mayhem level for all
playthroughs found in the game.

    bl3-save-edit old.sav new.sav --mayhem 4

### Currency (Money and Eridium)

Money and Eridium can be set with the `--money` and `--eridium`
arguments, respectively:

    bl3-save-edit old.sav new.sav --money 20000000
    bl3-save-edit old.sav new.sav --eridium 10000

### Unlocks

There are a number of things you can unlock with the utility, all
specified using the `--unlock` argument.  You can specify this
multiple times on the commandline, to unlock more than one thing
at once, like so:

    bl3-save-edit old.sav new.sav --unlock ammo --unlock backpack

#### Ammo/Backpack Unlocks

The `ammo` and `backpack` unlocks will give you the maximum number
of SDUs for all ammo types, and your backpack space, respectively.
The `ammo` SDU unlock will also fill your ammo reserves.

    bl3-save-edit old.sav new.sav --unlock ammo
    bl3-save-edit old.sav new.sav --unlock backpack

#### Eridian Resonator

The `resonator` unlock is what allows you to crack open Eridium
deposits throughout the game.  You ordinarily receive this as a
reward for the plot mission "Beneath the Meridian."

    bl3-save-edit old.sav new.sav --unlock resonator

#### Eridian Analyzer

Likewise, the `analyzer` unlock is what allows you to decode
the Eridian writings scattered throughout BL3.  You ordinarily
receive this ability during the plot mission "The Great Vault."

    bl3-save-edit old.sav new.sav --unlock analyzer

#### Inventory Slots

You can use the `gunslots`, `artifactslot`, and `comslot` unlocks
to activate the inventory slots which are ordinarily locked until
certain points in the game.  You can also use the `allslots` to
unlock all of them at once, rather than having to specify three
unlocks.

    bl3-save-edit old.sav new.sav --unlock gunslots
    bl3-save-edit old.sav new.sav --unlock comslot
    bl3-save-edit old.sav new.sav --unlock artifactslot

Or: 

    bl3-save-edit old.sav new.sav --unlock allslots

#### Vehicles

You can use the `vehicles` unlock to unlock all vehicles and
vehicle parts.  Note that this does *not* prematurely unlock the
Catch-A-Ride system.  You will still have to at least complete
the story mission with Ellie which unlocks those, to have access
to the vehicles.

    bl3-save-edit old.sav new.sav --unlock vehicles

#### Vehicle Skins

You can use `vehicleskins` to unlock all vehicle skins, for all
vehicle types.

    bl3-save-edit old.sav new.sav --unlock vehicleskins

#### TVHM

You can use the `tvhm` unlock to unlock TVHM mode early:

    bl3-save-edit old.sav new.sav --unlock tvhm

#### All Unlocks at Once

You can also use `all` to unlock all the various `--unlock`
options at once, without having to specify each one individually:

    bl3-save-edit old.sav new.sav --unlock all

### Copy NVHM State to THVM

The `--copy-nvhm` argument can be used to copy mission status,
unlocked Fast Travels, Mayhem Mode, and Last Map Visited from Normal
mode (NVHM) to TVHM, so your character in TVHM will be at basically
the exact same game state as in Normal.

    bl3-save-edit old.sav new.sav --copy-nvhm

### Import Items

The `-i`/`--import-items` option will let you import items into
a savegame, of the sort you can export using `-o items`.  Simply
specify a text file as the argument to `-i` and it will load in
any line starting with `BL3(` as an item into the savegame:

    bl3-save-edit old.sav new.sav -i items.txt

# Savegame Info Usage

The `bl3-save-info` script is extremely simple, and just dumps a bunch
of information about the specified savegame to the console.  If you
specify the `-v`/`--verbose` option, it'll output a little more info
than it ordinarily would, such as inventory contents and discovered
Fast Travel stations:

    bl3-save-info -v old.sav

# TODO

- Something a bit more Enum-like for various things in `__init__.py`; I
  know that's not very Pythonic, but when dealing with extra-Python data
  formats, one must sometimes make exceptions.
- Figure out item serial number parsing (or, almost certainly, wait for
  someone else to figure it out and then take it from there, assuming
  a FOSS'd project. :)
  - This'll let us level up items in addition to characters
- Unit tests?

# Credits

The encryption/decryption stanzas in `BL3Save.__init__` and `BL3Save.save_to`
were [helpfully provided by Gibbed](https://twitter.com/gibbed/status/1246863435868049410?s=19)
(rick 'at' gibbed 'dot' us), so many thanks for that!  The protobuf definitions
are also provided by Gibbed, from his
[Borderlands3Protos](https://github.com/gibbed/Borderlands3Protos) repo,
and used with permission.

The rest of the savegame format was gleaned from 13xforever/Ilya's
`gvas-converter` project: https://github.com/13xforever/gvas-converter

# License

All code in this project is licensed under the
[zlib/libpng license](https://opensource.org/licenses/Zlib).  A copy is
provided in [COPYING.txt](COPYING.txt).

# Changelog

**v1.0.0** - April 5, 2020
 - Initial version

