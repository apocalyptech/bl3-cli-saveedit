# Borderlands 3 Commandline Savegame Editor - Savegame Editing Reference

This is the documentation for the save editing portions of the
BL3 CLI Savegame Editor.  For general app information, installation,
upgrade procedures, and other information, please see the main
[README file](README.md).

These docs will assume that you've installed via `pip3` - if you're using
a Github checkout, substitute the commands as appropriate.  The equivalent
commands will be:

    python -m bl3save.cli_edit -h
    python -m bl3save.cli_info -h
    python -m bl3save.cli_import_protobuf -h
    python -m bl3save.cli_import_json -h
    python -m bl3save.cli_archive -h

# Table of Contents

- [Basic Operation](#basic-operation)
- [Output Formats](#output-formats)
- [Modifying the Savegame](#modifying-the-savegame)
  - [Character Name](#character-name)
  - [Save Game ID](#save-game-id)
  - [Save Game GUID](#save-game-guid)
  - [Guardian Rank](#guardian-rank)
  - [Character Level](#character-level)
  - [Mayhem Level](#mayhem-level)
  - [Mayhem Random Seed](#mayhem-random-seed)
  - [Currency (Money and Eridium)](#currency-money-and-eridium)
  - [Takedown Discovery Missions](#takedown-discovery-missions)
  - [Item Levels](#item-levels)
  - [Item Mayhem Levels](#item-mayhem-levels)
  - [Unlocks](#unlocks)
    - [Ammo/Backpack Unlocks](#ammobackpack-unlocks)
    - [Eridian Resonator](#eridian-resonator)
    - [Eridian Analyzer](#eridian-analyzer)
    - [Inventory Slots](#inventory-slots)
    - [Vehicles](#vehicles)
    - [Vehicle Skins](#vehicle-skins)
    - [TVHM](#tvhm)
    - [Eridian Cube Puzzle](#eridian-cube-puzzle)
    - [All Unlocks at Once](#all-unlocks-at-once)
  - [Copy NVHM State to TVHM](#copy-nvhm-state-to-tvhm)
  - ["Un-Finish" NVHM](#un-finish-nvhm)
  - [Import Items](#import-items)
- [Importing Raw Protobufs](#importing-raw-protobufs)
- [Importing JSON](#importing-json)
- [Savegame Info Usage](#savegame-info-usage)
  - [Items/Inventory](#itemsinventory)
  - [Fast Travel Stations](#fast-travel-stations)
  - [Challenges](#challenges)
  - [Missions](#missions)

# Basic Operation

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

Note that currently, the app will refuse to overwrite the same file that
you're editing.  You'll need to move/rename the `new.sav` over the
original, if you want it to replace your current save.  Be sure to keep
backups!

# Output Formats

The editor can output files in a few different formats, and you can
specify the format using the `-o`/`--output` option, like so:

    bl3-save-edit old.sav new.sav -o savegame
    bl3-save-edit old.sav new.pbraw -o protobuf
    bl3-save-edit old.sav new.json -o json
    bl3-save-edit old.sav new.txt -o items

- **savegame** - This is the default, if you don't specify an output
  format.  It will save the game like a valid BL3 savegame.  This
  will likely be your most commonly-used option.
- **protobuf** - This will write out the raw, unencrypted Protobuf
  entries contained in the savegame, which might be useful if you
  want to look at them with a Protobuf viewer of some sort (such
  as [this one](https://protogen.marcgravell.com/decode)), or to
  make hand edits of your own.  Raw protobuf files can be imported
  back into savegames using the separate `bl3-save-import-protobuf`
  command, whose docs you can find near the bottom of this README.
- **json** - Alternatively, this will write out the raw protobufs
  as encoded into JSON.  Like the protobuf output, you should be
  able to edit this by hand and then re-import using the
  `bl3-save-import-json` utility.  **NOTE:** JSON import is not
  super well-tested yet, so keep backups!
- **items** - This will output a text file containing item codes
  which can be read back in to other savegames.  It uses a format
  similar to the item codes used by Gibbed's BL2/TPS editors.
  (It will probably be identical to the codes used by Gibbed's BL3
  editor, once that is released, but time will tell on that front.)
  - You can optionally specify the `--csv` flag to output a CSV file
    instead of "regular" text file.  The first column will be the
    item names, the second will be the item codes.

Keep in mind that when saving in `items` format, basically all of
the other CLI arguments are pointless, since the app will only save
out the items textfile.

# Modifying the Savegame

Here's a list of all the edits you can make to the savegame.  You
can specify as many of these as you want on the commandline, to
process multiple changes at once.

## Character Name

This can be done with the `--name` option:

    bl3-save-edit old.sav new.sav --name "Gregor Samsa"

## Save Game ID

Like with BL2/TPS, I suspect that this ID isn't at all important, but
the editor can set it anyway with the `--save-game-id` option.  BL3
itself sets the savegame ID to match the filename of the savegame, if
interpreted as a hex value (so `10.sav` would have an ID of `16`).

    bl3-save-edit old.sav new.sav --save-game-id 2

## Save Game GUID

This is another identifier I suspect isn't actually important at all,
but there's an internal GUID which can be used to identify savegames
uniquely.  The `--randomize-guid` option will randomize this value,
so if you're copying a character or something you can ensure that the
value is different between them.  As I say, I have no idea if that's
ever actually important (I've copied characters many times without
randomizing this value, and they've worked fine) but here's the
option anyway:

    bl3-save-edit old.sav new.sav --randomize-guid

## Guardian Rank

Guardian Rank can be zeroed out using the `--zero-guardian-rank`
argument.  This is useful when a savegame gets out of sync from your
profile, such as if you download a savegame from the internet, or if
you're making changes to values in your profile.  After zeroing out
the Guardian Rank in a savegame, the next time the character is loaded
into the game, it will inherit the main profile's Guardian Rank.

    bl3-save-edit old.sav new.sav --zero-guardian-rank

## Character Level

You can set your character to a specific level using `--level <num>`,
or to the max level allowed by the game using `--level-max`

    bl3-save-edit old.sav new.sav --level 20
    bl3-save-edit old.sav new.sav --level-max

## Mayhem Level

This is only really useful before you've got Mayhem Mode unlocked.
You can use the `--mayhem` argument to activate Mayhem mode even from
the very beginning of the game.  Note that you still won't have access
to the Mayhem console on Sanctuary until it's properly unlocked by the
game, so this will be the only way of changing Mayhem mode until that
point in the game.  This will set the Mayhem level for all
playthroughs found in the game.

    bl3-save-edit old.sav new.sav --mayhem 10

Note that in order to have Anointments drop while playing in Normal
mode, your savegame does need to have THVM unlocked, so see the `--unlock`
docs below for how to do that.

## Mayhem Random Seed

The active modifiers in Mayhem Mode are all generated using a single
[random seed](https://en.wikipedia.org/wiki/Pseudorandom_number_generator)
which is specified on a per-playthrough basis.  If you have a set of
Mayhem modifiers you like, you can take that seed (shown in the `bl3-save-info`
output) and set it onto another save using the `--mayhem-seed` argument:

    bl3-save-edit old.sav new.save --mayhem-seed -3938591

The seeds may be positive or negative, and can range up to 2 billion or
so, both negative and positive.  Note that if Gearbox changes the pool of
available Mayhem modifiers, such as by disabling some, or adding new ones,
the random seeds you're used to will start to give a different result, so
you may have to reroll a bunch to find your favorite set, again.

## Currency (Money and Eridium)

Money and Eridium can be set with the `--money` and `--eridium`
arguments, respectively:

    bl3-save-edit old.sav new.sav --money 20000000
    bl3-save-edit old.sav new.sav --eridium 10000

## Takedown Discovery Missions

You can clear out the two Takedown Discovery missions using the
`--clear-takedowns` argument, if you have a character who you don't
ever plan to do Takedowns with, but want those mission-pickup notifications
gone, without going through the hassle of travelling to the Takedown
maps yourself:

    bl3-save-edit old.sav new.sav --clear-takedowns

Note that if you decide to do the Takedowns later, you'll have to pilot
Sanctuary over to their pickup points before they'll appear in your
Fast Travel menu; this argument doesn't unlock the Fast Travel locations
itself.

Obviously it doesn't take long to just do the Discovery missions yourself;
you can always just fail out of the Takedown itself by fast-travelling out
of the map, but this option would save you a minute or two, anyway.

## Item Levels

There are two arguments to set item levels.  The first is to set
all items/weapons in your inventory to match your character's level.
If you're also changing your character's level at the same time,
items/weapons will get that new level.  This can be done with
`--items-to-char`

    bl3-save-edit old.sav new.sav --items-to-char

Alternatively, you can set an explicit level using `--item-levels`

    bl3-save-edit old.sav new.sav --item-levels 57

## Item Mayhem Levels

There are two arguments to set item mayhem levels.  The first is
to set all weapons to the maximum mayhem level, which is currently 10,
using `--item-mayhem-max`.  Note that currently only weapons and
grenades can have Mayhem applied; other items will end up generating
a message like `<num> were unable to be levelled`.

    bl3-save-edit old.sav new.sav --item-mayhem-max

Alternatively, you can specify a specific Mayhem level with
`--item-mayhem-levels`:

    bl3-save-edit old.sav new.sav --item-mayhem-levels 5

To remove Mayhem levels from weapons/greandes entirely, specify `0` for
`--item-mayhem-levels`.

## Unlocks

There are a number of things you can unlock with the utility, all
specified using the `--unlock` argument.  You can specify this
multiple times on the commandline, to unlock more than one thing
at once, like so:

    bl3-save-edit old.sav new.sav --unlock ammo --unlock backpack

### Ammo/Backpack Unlocks

The `ammo` and `backpack` unlocks will give you the maximum number
of SDUs for all ammo types, and your backpack space, respectively.
The `ammo` SDU unlock will also fill your ammo reserves.

    bl3-save-edit old.sav new.sav --unlock ammo
    bl3-save-edit old.sav new.sav --unlock backpack

### Eridian Resonator

The `resonator` unlock is what allows you to crack open Eridium
deposits throughout the game.  You ordinarily receive this as a
reward for the plot mission "Beneath the Meridian."

    bl3-save-edit old.sav new.sav --unlock resonator

### Eridian Analyzer

Likewise, the `analyzer` unlock is what allows you to decode
the Eridian writings scattered throughout BL3.  You ordinarily
receive this ability during the plot mission "The Great Vault."

    bl3-save-edit old.sav new.sav --unlock analyzer

### Inventory Slots

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

### Vehicles

You can use the `vehicles` unlock to unlock all vehicles and
vehicle parts.  Note that this does *not* prematurely unlock the
Catch-A-Ride system.  You will still have to at least complete
the story mission with Ellie which unlocks those, to have access
to the vehicles.

    bl3-save-edit old.sav new.sav --unlock vehicles

### Vehicle Skins

You can use `vehicleskins` to unlock all vehicle skins, for all
vehicle types.

    bl3-save-edit old.sav new.sav --unlock vehicleskins

### TVHM

You can use the `tvhm` unlock to unlock TVHM mode early:

    bl3-save-edit old.sav new.sav --unlock tvhm

### Eridian Cube Puzzle

The Eridian Cube puzzle in Desolation's Edge (on Nekrotafeyo) is
ordinarily only doable once per savegame.  The `cubepuzzle`
unlock will let you complete it more than once:

    bl3-save-edit old.sav new.sav --unlock cubepuzzle

### All Unlocks at Once

You can also use `all` to unlock all the various `--unlock`
options at once, without having to specify each one individually:

    bl3-save-edit old.sav new.sav --unlock all

## Copy NVHM State to TVHM

The `--copy-nvhm` argument can be used to copy mission status,
unlocked Fast Travels, Mayhem Mode, and Last Map Visited from Normal
mode (NVHM) to TVHM, so your character in TVHM will be at basically
the exact same game state as in Normal.

    bl3-save-edit old.sav new.sav --copy-nvhm

## "Un-Finish" NVHM

Alternatively, you can use the `--unfinish-nvhm` argument to
completely discard all TVHM data, and set the game state so that
NVHM was never finished.  Note that this does *not* reset any
mission status, so if you've already legitimately finished NVHM
in the savegame, you won't be able to re-unlock it in-game (though
`--unlock tvhm` or `--copy-nvhm` could still be used to unlock).
This is primarily useful just if you wanted to undo a `--copy-nvhm`
run, or for myself when testing things out using saves from my
[BL3 Savegame Archive](http://apocalyptech.com/games/bl-saves/bl3.php).

    bl3-save-edit old.sav new.sav --unfinish-nvhm

## Import Items

The `-i`/`--import-items` option will let you import items into
a savegame, of the sort you can export using `-o items`.  Simply
specify a text file as the argument to `-i` and it will load in
any line starting with `BL3(` as an item into the savegame:

    bl3-save-edit old.sav new.sav -i items.txt

Note that by default, the app will not allow Fabricators to be
imported into a save, since the player doesn't have a good way to
get rid of them.  You can tell the app to allow importing
Fabricators anyway with the `--allow-fabricator` option (which has
no use when not used along with `-i`/`--import-items`)

    bl3-save-edit old.sav new.sav -i items.txt --allow-fabricator

If the utility can't tell what an item is during import (which may
happen if BL3 has been updated but this editor hasn't been updated
yet), it will refuse to import the unknown items, unless
`--allow-fabricator` is specified, since the unknown item could be
a Fabricator.  Other edits and imports can still happen, however.

If you have items saved in a CSV file (such as one exported using
`-o items --csv`), you can add the `--csv` argument to import items
from the CSV:

    bl3-save-edit old.sav new.sav -i items.csv --csv

When reading CSV files, any valid BL3 item code found by itself in
a field in the CSV will be imported, so the CSV doesn't have to
be in the exact same format as the ones generated by `-o items --csv`.

# Importing Raw Protobufs

If you've saved a savegame in raw protobuf format (using the
`-o protobuf` option, or otherwise), you may want to re-import it
into a savegame, perhaps after having edited it by hand.  This can
be done with the separate utility `bl3-save-import-protobuf`.  This
requires a `-p`/`--protobuf` argument to specify the file where
the raw protobuf is stored, and a `-t`/`--to-filename` argument,
which specifies the filename to import the protobufs into:

    bl3-save-import-protobuf -p edited.pbraw -t old.sav

By default this will prompt for confirmation before actually
overwriting the file, but you can use the `-c`/`--clobber` option
to force it to overwrite without asking:

    bl3-save-import-protobuf -p edited.pbraw -t old.sav -c

**NOTE:** This (and the JSON import) is the one place where these
utilities *expect* to overwrite the file you're giving it.  In the
above examples, it requires an existing `old.sav` file, and the
savefile contents will be written directly into that file.  This
option does *not* currently create a brand-new valid savegame for
you.

# Importing JSON

If you saved a savegame in JSON format (using the `-o json` option),
you may want to re-import it into a savegame, perhaps after having
edited it by hand.  This can be done with the separate utility
`bl3-save-import-json`.  This requires a `-j`/`--json` argument to
specify the file where the JSON is stored, and a `-t`/`--to-filename`
argument, which specifies the filename to import the JSON into:

    bl3-save-import-json -j edited.json -t old.sav

By default this will prompt for confirmation before actually
overwriting the file, but you can use the `-c`/`--clobber` option
to force it to overwrite without asking:

    bl3-save-import-json -j edited.json -t old.sav -c

**NOTE:** This (and the protobuf import) is the one place where these
utilities *expect* to overwrite the file you're giving it.  In the
above examples, it requires an existing `old.sav` file, and the
savefile contents will be written directly into that file.  This
option does *not* currently create a brand-new valid savegame for
you.

# Savegame Info Usage

The `bl3-save-info` script is extremely simple, and just dumps a bunch
of information about the specified savegame to the console.  If you
specify the `-v`/`--verbose` option, it'll output a bunch more info
than it ordinarily would, such as inventory contents and discovered
Fast Travel stations:

    bl3-save-info -v old.sav

Instead of doing a global "verbose" option, you can instead choose
to output just some of the extra information:

## Items/Inventory

The `-i`/`--items` argument will output your inventory, including item
codes which could be put in a text file for later import:

    bl3-save-info -i old.sav

## Fast Travel Stations

The `--fast-travel` argument will output a list of all unlocked
Fast Travel stations, per playthrough.  These are reported as the raw
object name in the game, so you may have to use a
[level name reference](https://github.com/BLCM/BLCMods/wiki/Level-Name-Reference#borderlands-3)
to get a feel for what is what.

    bl3-save-info --fast-travel old.sav

## Challenges

The `--all-challenges` argument will output the state of all challenges
in your savegame.  Note that BL3 uses challenges to keep track of a
lot of info in the savegames, and this list will be over 1.5k items
long!  As with the fast travel stations, these will be reported as the
raw object names.

    bl3-save-info --all-challenges old.sav

## Missions

The `--all-missions` argument will output all of the missions that the
character has completed, in addition to the active missions which are
always shown.

    bl3-save-info --all-missions old.sav

