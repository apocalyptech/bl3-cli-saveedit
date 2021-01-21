# Borderlands 3 Commandline Savegame/Profile Editor

This project is a commandline Python-based Borderlands 3 Savegame
and Profile Editor.  It's a companion to the very similar
[CLI editor for BL2/TPS](https://github.com/apocalyptech/borderlands2),
and provides some very similar functionality.  It can be used
to level up your characters, unlock Mayhem modes early in the
game, unlock TVHM, add SDUs, unlock equipment slots, and more.

This editor has only been tested on PC Savegames -- other platforms'
savegames are not supported at the moment.

Please keep the following in mind:

- This app does not have any graphical interface.  You must be
  on a commandline in order to use it.
- The app has only very limited item-editing capability at the
  moment, which is restricted to:
  - Item Levels can be changed
  - Mayhem Level can be set on items
- It does not offer any direct ability to alter Guardian Rank status.
- While I have not experienced any data loss with the app,
  **take backups of your savegames before using this**, and
  keep in mind that it could end up corrupting your saves.  If
  you do encounter any data loss problems, please contact me
  and I'll try to at least fix whatever bug caused it.

# Table of Contents

- [Installation](#installation)
  - [Upgrading](#upgrading)
  - [Notes for People Using Windows](#notes-for-people-using-windows)
  - [Running from Github](#running-from-github)
  - [Finding Savegames](#finding-savegames)
- [Editor Usage](#editor-usage)
- [TODO](#todo)
- [Credits](#credits)
- [License](#license)
- [Other Utilities](#other-utilities)
- [Changelog](#changelog)

# Installation

This editor requires [Python 3](https://www.python.org/), and has been
tested on 3.7 and 3.8.  It also requires the [protobuf package](https://pypi.org/project/protobuf/).

The easiest way to install this app is via `pip`/`pip3`.  Once Python 3 is
installed, you should be able to run this to install the app:

    pip3 install bl3-cli-saveedit

Once installed, there should be a few new commandline utilities available
to you.  The main editor is `bl3-save-edit`, and you can see its possible
arguments with `-h`/`--help`:

    bl3-save-edit -h

There's also a `bl3-save-info` utility which just shows some information
about a specified savefile.  You can see its possible arguments with
`-h`/`--help` as well:

    bl3-save-info -h

If you've got a raw savegame protobuf file that you've hand-edited (or
otherwise processed) that you'd like to import into an existing savegame,
you can do that with `bl3-save-import-protobuf`:

    bl3-save-import-protobuf -h

Alternatively, if you've got a savegame exported as JSON that you'd like
to import into an existing savegame, you can do that with
`bl3-save-import-json`:

    bl3-save-import-json -h

Finally, there's a utility which I'd used to generate my
[BL3 Savegame Archive Page](http://apocalyptech.com/games/bl-saves/bl3.php).
This one won't be useful to anyone but me, but you can view its arguments
as well, if you like:

    bl3-process-archive-saves -h

There are also profile-specific versions of most of those commands, which
can be used to edit the main BL3 `profile.sav`:

    bl3-profile-edit -h
    bl3-profile-info -h
    bl3-profile-import-protobuf -h
    bl3-profile-import-json -h

### Upgrading

When a new version is available, you can update using `pip3` like so:

    pip3 install --upgrade bl3-cli-saveedit

You can check your current version by running any of the apps with the
`-V`/`--version` argument:

    bl3-save-info --version

### Notes for People Using Windows

This is a command-line utility, which means there's no graphical interface,
and you'll have to run it from either a Windows `cmd.exe` prompt, or presumably
running through PowerShell should work, too.  The first step is to
install Python:

- The recommended way is to [install Python from python.org](https://www.python.org/downloads/windows/).
  Grab what's available in the 3.x series (at time of writing, that's either
  3.8.2 or 3.7.7), and when it's installing, make sure to check the checkbox
  which says something like "add to PATH", so that you can run Python from the
  commandline directly.
- If you're on Windows 10, you can apparently just type `python3` into a command
  prompt to be taken to the Windows store, where you can install Python with
  just one click.  I've heard reports that this method does *not* provide the
  ability to add Python to your system PATH, though, so it's possible that
  running it would be more complicated.

When it's installed, test that you can run it from the commandline.  Open up
either `cmd.exe` or PowerShell, and make sure that you see something like this
when you run `python -V`:

    C:\> python -V
    Python 3.8.2

If that works, you can then run the `pip3 install bl3-cli-saveedit` command
as mentioned above, and use the commandline scripts to edit to your heart's
content.

### Running from Github

Alternatively, if you want to download or run the Github version of
the app: clone the repository and then install `protobuf` (you can
use `pip3 install -r requirements.txt` to do so, though a `pip3 install protobuf`
will also work just fine).

You can then run the scripts directly from the Github checkout, though
you'll have to use a slightly different syntax.  For instance, rather than
running `bl3-save-edit -h` to get help for the main savegame editor, you
would run:

    python -m bl3save.cli_edit -h

The equivalents for each of the commands are listed in their individual
README files, linked below.

### Finding Savegames

This app doesn't actually know *where* your savegames or profiles are located.
When you give it a filename, it'll expect that the file lives in your "current"
directory, unless the filename includes all its path information.  When launching
a `cmd.exe` on Windows, for instance, you'll probably start out in your home
directory (`C:\Users\username`), but your savegames will actually live in a
directory more like `C:\Users\username\My Documents\My Games\Borderlands 3\Saved\SaveGames\<numbers>\`.
The easiest way to run the utilities is to just use `cd` to go into the dir
where your saves are (or otherwise launch your commandline in the directory you
want).  Otherwise, you could copy the save into your main user dir (and then
copy back after editing), or even specify the full paths with the filenames.

# Editor Usage

For instructions on using the Savegame portions of the editor, see
[README-saves.md](https://github.com/apocalyptech/bl3-cli-saveedit/blob/master/README-saves.md).

FOr instructions on using the Profile portions of the editor, see
[README-profile.md](https://github.com/apocalyptech/bl3-cli-saveedit/blob/master/README-profile.md).

# TODO

- Would anyone appreciate an option to *delete* Fabricators?  Hm.
- Would be nice to have some anointment-setting functions in here.
- If we fail to read a savefile or profile, might be nice to *actually* check
  if it's the other of profile-or-savefile, and give a more helpful message in
  those cases.
- Something a bit more Enum-like for various things in `__init__.py`; I
  know that's not very Pythonic, but when dealing with extra-Python data
  formats, one must sometimes make exceptions.
- Unit tests?

# Credits

The encryption/decryption stanzas in `BL3Save.__init__` and `BL3Save.save_to`
were [helpfully provided by Gibbed](https://twitter.com/gibbed/status/1246863435868049410?s=19)
(rick 'at' gibbed 'dot' us), so many thanks for that!  The protobuf definitions
are also provided by Gibbed, from his
[Borderlands3Protos](https://github.com/gibbed/Borderlands3Protos) repo,
and used with permission.  Gibbed also kindly provided the exact hashing
mechanism used to work with weapon skins and trinkets.

The rest of the savegame format was gleaned from 13xforever/Ilya's
`gvas-converter` project: https://github.com/13xforever/gvas-converter

Many thanks also to Baysix, who endured an awful lot of basic questions about
pulling apart item serial numbers.  Without their help, we wouldn't have
item level editing (or nice item names in the output)!

Basically what I'm saying is that anything remotely "hard" in here is all thanks
to lots of other folks.  I'm just pasting together all their stuff.  Thanks, all!

# License

All code in this project is licensed under the
[zlib/libpng license](https://opensource.org/licenses/Zlib).  A copy is
provided in [COPYING.txt](COPYING.txt).

# Other Utilities

Various BL3 Savegame/Profile editors have been popping up, ever since Gibbed
released the encryption details.  Here's a few which could be more to your
liking, if you didn't want to use this one for whatever reason:

- [Baysix's Web-Based Editor](http://www.bl3editor.com) - Just web-based for
  now; sourcecode release is still forthcoming.
- [Raptor's CLI Tools](https://github.com/cfi2017/bl3-save) - These are written
  in [Go](https://golang.org/), and the project has easy downloads for Windows,
  Mac, and Linux (in addition to the sourcecode).
- [FromDarkHell's Profile Editor](https://github.com/FromDarkHell/BL3ProfileEditor) -
  Written in C#, has EXE downloads for ease of use on Windows.
- [sandsmark's borderlands3-save-editor](https://github.com/sandsmark/borderlands3-save-editor) -
  Written in C++ with Qt for GUI.  Is still in development.  Native downloads
  for Windows, but should compile fine on other platforms.
- [HackerSmaker's CSave Editor](https://github.com/HackerSmacker/CSave) - Cross-platform
  commandline editor written in C.  Has a terminal (ncurses) UI on UNIX-like OSes.

# Changelog

**v1.10.3** - January 21, 2021
 - Updated internal inventory DB with data from today's patch.  (No real functionality
   changes with this.)

**v1.10.2** - November 10, 2020
 - Updated internal inventory DB with a minor change which was in the previous GBX
   patch.  (Probably no actual functionality changes with this.)

**v1.10.1** - November 10, 2020
 - A second patch was released, about 12 hours after the Designer's Cut release, which
   updated the protobufs and was causing us to not read saves properly.  This has been
   fixed up now.
 - Also require at least protobuf v3.12, which appears to be required as of my
   latest protobuf generation.

**v1.10.0** - November 9, 2020
 - Updated with DLC5 (Designer's Cut) support

**v1.9.2** - October 8, 2020
 - Added in the missed weapon skin "Porphyrophobia," from Bloody Harvest 2020.

**v1.9.1** - September 30, 2020
 - Fixed unlocking FL4K's "Antisoci4l" head (though you should still get
   that one [all legit-like](https://gearboxloot.com/products/borderlands-3-mask-skins-head-pack))

**v1.9.0** - September 10, 2020
 - Updated with DLC4 (Psycho Krieg and the Fantastic Fustercluck) support

**v1.8.2** - July 27, 2020
 - Updated to allow unlocking the Battle Driver and Devil Tooth weapon trinkets, since
   the July 23 patch fixed those so that they properly stay in your profile.

**v1.8.1** - July 14, 2020
 - `--item-mayhem-max` and `--item-mayhem-levels` will now apply Mayhem parts to
   grenades as well as weapons.

**v1.8.0** - July 11, 2020
 - Added `--mayhem-seed` option to `bl3-save-edit`, to set the random seed used to
   determine active Mayhem modifiers.  The seed is now shown in the `bl3-save-info`
   output, as well.

**v1.7.2** - July 6, 2020
 - Allow characters to use skill trees properly if levelled higher directly from level 1.

**v1.7.1** - June 29, 2020
 - Added three more DLC3 room decorations that I'd missed orginally, for the profile
   editor's cosmetic-unlock ability
 - Added Jetbeast unlocks (both parts and skins)

**v1.7.0** - June 26, 2020
 - Updated for DLC3 (Bounty of Blood) content
   - Jetbeast vehicle unlocks are forthcoming, until I can actually test them out.
 - Added various Guardian Rank processing
   - For savegames and profiles, added `--zero-guardian-rank`
   - For only profiles, added `--min-guardian-rank`, `--guardian-rank-rewards`, and
     `--guardian-rank-tokens`
 - Added `--unlock cubepuzzle` to reset the Eridian Cube puzzle in Desolation's Edge
 - Added `--clear-takedowns` to get rid of the Takedown mission-pickup notifications
   for chars you never intend to do Takedowns with.
 - Item name processing will now recognize the specific legendary artifact balances
   added by the Maliwan Takedown update (they're functionally identical to the world-
   drop versions)
 - Updated `bl3-process-archive-saves` to wipe out Guardian Rank entirely

**v1.6.2** - June 18, 2020
 - Allow setting character/item levels higher than the currently-known max, in case
   users want to pre-level their saves ahead of level cap increases (and in case
   they don't want to wait for an official update of this app)

**v1.6.1** - June 13, 2020
 - Updated room decoration/trinket/weaponskin alphabetization to ignore case (so
   "Casino Banner" sorts before "COV Bat," for instance).
 - Counts of unlocked cosmetic items in `bl3-profile-info` will now include the
   "default" cosmetics which are always unlocked, so those counts match the numbers
   in-game.

**v1.6.0** - June 11, 2020
 - Updated for extra content introduced by Takedown at the Guardian Breach
 - Added `--golden-keys` option to `bl3-profile-edit`, to set available Golden Keys
 - Added `--randomize-guid` option to `bl3-save-edit`

**v1.5.2** - May 23, 2020
 - Updated item name mapping to include the COM Balances used by Trials bosses, for
   their dedicated COM drops.
 - Add in the `--csv` option to allow importing/exporting items into CSV files,
   instead of just text files (which is the default without `--csv`).  Has no effect
   except on item imports/exports.

**v1.5.1** - May 5, 2020
 - Fixed alphabetization of COV Buzzaxe room decoration.  In the game data it looks
   like it's called "Psycho Buzzaxe," but the actual in-game label is COV Buzzaxe.
 - Fixed name displays for "regular" (non-E-Tech, non-Legendary) Maliwan snipers and
   Tediore pistols.
 - Updated item name mapping to distinguish between the blue-rarity mission reward
   version of Redistributor from the legendary version from Maliwan Takedown.
 - Updated `bl3-process-archive-saves` to clear out some 3rd-playthrough data
   which earlier versions had accidentally introduced *(only really of interest
   to myself)*

**v1.5.0** - April 28, 2020
 - Added ability to alter Mayhem level for items, both in savegames and profile.
   `--item-mayhem-max` will set items to the max Mayhem level (`10`), or
   `--item-mayhem-levels <num>` will set a specific level (`0` to remove Mayhem
   from items entirely).
 - Item level reports when viewing contents or exporting items will include
   the Mayhem levels
 - Info views will show the total number of available SDUs along with the
   purchased count
 - Various internal code reorganization

**v1.4.0** - April 23, 2020
 - Updated for the Cartels + Mayhem 2.0 patch:
   - Update item/weapon handling to understand new serial number versions
   - Added in new cosmetic unlocks
   - Mayhem level can now be set as high as 10
   - Extra SDU levels added
   - Fixed a bug related to viewing vehicle unlocks, thanks to new game data
 - Introduction of profile editing utilities, via `bl3-profile-edit`,
   `bl3-profile-info`, `bl3-profile-import-json`, and `bl3-profile-import-protobuf`.
   The following functionality is supported:
   - Importing/Exporting to both JSON and Protobuf
   - Importing/Exporting items to/from the bank
   - Altering the level of gear stored in the bank
   - Unlocking all global customizations/cosmetics
   - Alphabetizing the list of room decorations, trinkets, and weapon skins
 - Display changes for `bl3-save-info` - introduced individual arguments to
   show more detailed information as-requested, instead of only having a
   global `-v`/`--verbose` option:
   - Added `-i`/`--items` argument, to show inventory information
   - Added `--fast-travel` argument, to show unlocked fast travel stations
   - Added `--all-challenges` argument, to list all challenges in the save file
     and their statuses (note: this will be over 1.5k items!)
   - Added `--all-missions` argument, to list all completed missions in addition
     to active ones
   - `-v`/`--verbose` now implies the four options above.
 - `bl3-save-info` will now also report on whether the savegame has finished the
   main game or any of the DLCs.
 - Added `--unfinish-nvhm` option to `bl3-save-edit`, to completely clear out
 any TVHM data and pretend that NVHM was never finished.

**v1.3.1** - April 14, 2020
 - Bah, forgot a few more README tweaks about the JSON export/import

**v1.3.0** - April 14, 2020
 - Added `json` output type, to export the protobuf as encoded into JSON
 - Added `bl3-save-import-json` utility, to load JSON into a savegame

**v1.2.2** - April 12, 2020
 - Updated README with some more specific Windows 10 installation advice.

**v1.2.1** - April 12, 2020
 - Updated Credits section of the README with one more credit that I'd
   wanted to put in but forgot. :)

**v1.2.0** - April 12, 2020
 - Added ability to change item/weapon levels, using `--items-to-char`
   or `--item-levels`
 - Item Imports will now *not* import Fabricators unless explicitly
   told to with the `--allow-fabricator` option.
 - Item names and levels are now shown where appropriate:
   - In verbose `bl3-save-info` output
   - In item export files
   - While importing items
 - Updated to Protobuf v3, which is what BL3 itself uses.  Now when we
   re-save without any edits, the save should be identical to the
   original savegame.
 - Item export will now be done without any encryption, so an item will
   have the exact same item code regardless of where it came from
   (previously, item codes would change every time the game was saved,
   so the same item could have very different-looking codes)
 - Added `-V`/`--version` flag to show version number

**v1.1.1** - April 7, 2020
 - Added in Citizen Science mission name.

**v1.1.0** - April 7, 2020
 - Added `bl3-save-import-protobuf` command, to load a raw protobuf file
   into an existing savegame.

**v1.0.1** - April 5, 2020
 - Some saves include Eridium as an ammo type, presumably related to the
   Fabricator.  Fixed a crash in `bl3-save-info` related to that.

**v1.0.0** - April 5, 2020
 - Initial version

