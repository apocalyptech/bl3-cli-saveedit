# Borderlands 3 Commandline Profile Editor - Profile Editing Reference

This is the documentation for the profile editing portions of the
BL3 CLI Savegame Editor.  For general app information, installation,
upgrade procedures, and other information, please see the main
[README file](README.md).

These docs will assume that you've installed via `pip3` - if you're using
a Github checkout, substitute the commands as appropriate.  The equivalent
commands will be:

    python -m bl3save.cli_prof_edit -h
    python -m bl3save.cli_prof_info -h
    python -m bl3save.cli_prof_import_protobuf -h
    python -m bl3save.cli_prof_import_json -h

# Table of Contents

- [Basic Operation](#basic-operation)
- [Output Formats](#output-formats)
- [Modifying the Profile](#modifying-the-profile)
  - [Golden Keys](#golden-keys)
  - [Guardian Rank](#guardian-rank)
    - [Zeroing Guardian Rank](#zeroing-guardian-rank)
    - [Minimizing Guardian Rank](#minimizing-guardian-rank)
    - [Guardian Rank Rewards](#guardian-rank-rewards)
    - [Guardian Rank Tokens](#guardian-rank-tokens)
  - [Bank Item Levels](#bank-item-levels)
  - [Bank Item Mayhem Levels](#bank-item-mayhem-levels)
  - [Alphabetize Customizations](#alphabetize-customizations)
  - [Clear Customizations](#clear-customizations)
  - [Unlocks](#unlocks)
    - [Lost Loot and Bank Capacity](#lost-loot-and-bank-capacity)
    - [Customizations](#customizations)
    - [All Unlocks at Once](#all-unlocks-at-once)
  - [Import Bank Items](#import-bank-items)
- [Importing Raw Protobufs](#importing-raw-protobufs)
- [Importing JSON](#importing-json)
- [Profile Info Usage](#profile-info-usage)
  - [Items/Inventory](#itemsinventory)

# Basic Operation

At its most basic, you can run the editor with only an input and output
file, and it will simply load and then re-encode the profile.  For
instance, in this example, `profile.sav` and `newprofile.sav` will be
identical as far as BL3 is concerned:

    bl3-profile-edit profile.sav newprofile.sav

If `newprofile.sav` exists, the utility will prompt you if you want to
overwrite it.  If you want to force the utility to overwrite without asking,
use the `-f`/`--force` option:

    bl3-profile-edit profile.sav newprofile.sav -f

As the app processes files, it will output exactly what it's doing.  If
you prefer to have silent output (unless there's an error), such as if
you're using this to process a group of files in a loop, you can use
the `-q`/`--quiet` option:

    bl3-profile-edit profile.sav newprofile.sav -q

Note that currently, the app will refuse to overwrite the same file that
you're editing.  You'll need to move/rename the `newprofile.sav` over the
original, if you want it to replace your current profile.  Be sure to keep
backups!

# Output Formats

The editor can output files in a few different formats, and you can
specify the format using the `-o`/`--output` option, like so:

    bl3-profile-edit profile.sav newprofile.sav -o profile
    bl3-profile-edit profile.sav newprofile.pbraw -o protobuf
    bl3-profile-edit profile.sav newprofile.json -o json
    bl3-profile-edit profile.sav newprofile.txt -o items

- **profile** - This is the default, if you don't specify an output
  format.  It will save the game like a valid BL3 profile.  This
  will likely be your most commonly-used option.
- **protobuf** - This will write out the raw, unencrypted Protobuf
  entries contained in the profile, which might be useful if you
  want to look at them with a Protobuf viewer of some sort (such
  as [this one](https://protogen.marcgravell.com/decode)), or to
  make hand edits of your own.  Raw protobuf files can be imported
  back into the profile using the separate `bl3-profile-import-protobuf`
  command, whose docs you can find near the bottom of this README.
- **json** - Alternatively, this will write out the raw protobufs
  as encoded into JSON.  Like the protobuf output, you should be
  able to edit this by hand and then re-import using the
  `bl3-profile-import-json` utility.  **NOTE:** JSON import is not
  super well-tested yet, so keep backups!
- **items** - This will output a text file containing item codes
  for all items in your bank, which can be read back in to other
  savegames or profiles.  It uses a format similar to the item codes
  used by Gibbed's BL2/TPS editors.  (It will probably be identical
  to the codes used by Gibbed's BL3 editor, once that is released,
  but time will tell on that front.)
  - You can optionally specify the `--csv` flag to output a CSV file
    instead of "regular" text file.  The first column will be the
    item names, the second will be the item codes.

Keep in mind that when saving in `items` format, basically all of
the other CLI arguments are pointless, since the app will only save
out the items textfile.

# Modifying the Profile

Here's a list of all the edits you can make to the profile.  You
can specify as many of these as you want on the commandline, to
process multiple changes at once.

## Golden Keys

The number of Golden Keys stored in the profile can be set using
the `--golden-keys` argument:

    bl3-profile-edit profile.sav newprofile.sav --golden-keys 150

## Guardian Rank

There are a number of functions available for managing Guardian Rank
in profiles.  Remember in all cases that if Guardian Rank in a profile
is zeroed out, it will "inherit" the Guardian Rank from the first
savegame that's loaded.  Likewise, a zeroed-out GR in a savegame will
inherit the current GR from the profile.  When editing the profile
Guardian Rank, it might be prudent to zero out all your savegames
using the save editor's `--zero-guardian-rank` afterwards, to make
sure that everything stays in sync.

### Zeroing Guardian Rank

Guardian rank can be completely cleared from a profile using the
`--zero-guardian-rank` argument.  This might be useful if your
profile's Guardian Rank got "infected" with Guardian Rank from
someone else's save, from back before Gearbox fixed that particular
bug, and you wanted to clear it out.  Remember that the profile will
probably "inherit" the GR from the first-loaded savegame, so make sure
that the save has what you want first.  The `--min-guardian-rank`
option below might be better, if you're looking to start from scratch.

Anyway, there's probably not much call for it nowadays, but here it is,
just in case.

    bl3-profile-edit profile.sav newprofile.sav --zero-guardian-rank

### Minimizing Guardian Rank

This is a "safer" version of `--zero-guardian-rank` which starts you
off with 18 Guardian Rank, with one point in each of the Guardian Rank
Rewards.  This will prevent the profile from picking up the GR status
from the first savegame that it loads.  So if you're looking to reset your
GR and start over from scratch, this is probably the better of the two
options.  The argument is called `--min-guardian-rank`:

    bl3-profile-edit profile.sav newprofile.sav --min-guardian-rank

### Guardian Rank Rewards

To set the specified investment in Guardian Rank Rewards, across all
eighteen rewards, use the `--guardian-rank-rewards` argument.  The value
you use should be the number of times you want each reward to be
"redeemed."  For example, to put everything at about 14%:

    bl3-profile-edit profile.sav newprofile.sav --guardian-rank-rewards 40

Specifying `1` for the value is nearly identical to using `--min-guardian-rank`,
except that this argument doesn't clear out the Guardian XP reported by
the game, or the available token count.  This argument will also update your
main Guardian Rank number to be an appropriate value, given the number of
rewards and available tokens.

### Guardian Rank Tokens

The number of available Guardian Rank tokens can be set using the
`--guardian-rank-tokens` argument:

    bl3-profile-edit profile.sav newprofile.sav --guardian-rank-tokens 10

This argument will also update your main Guardian Rank number to be an
appropriate value, given the number of rewards and available tokens.

## Bank Item Levels

There are two arguments to set item levels for gear that's stored in
your bank.  The first is to set all items/weapons in the bank to the
max level in the game.  This can be done with `--item-levels-max`

    bl3-profile-edit profile.sav newprofile.sav --item-levels-max

Alternatively, you can set an explicit level using `--item-levels`

    bl3-profile-edit profile.sav newprofile.sav --item-levels 57

## Bank Item Mayhem Levels

There are two arguments to set bank item mayhem levels.  The first is
to set all weapons to the maximum mayhem level, which is currently 10,
using `--item-mayhem-max`.  Note that currently only weapons and
grenades can have Mayhem applied; other items will end up generating
a message like `<num> were unable to be levelled`.

    bl3-profile-edit profile.sav newprofile.sav --item-mayhem-max

Alternatively, you can specify a specific Mayhem level with
`--item-mayhem-levels`:

    bl3-profile-edit profile.sav newprofile.sav --item-mayhem-levels 5

To remove Mayhem levels from weapons/grenades entirely, specify `0` for
`--item-mayhem-levels`.

## Alphabetize Customizations

Room Decorations, Weapon Trinkets, and Weapon Skins show up in the game
in the order in which they were picked up, generally, which makes it
sometimes hard to find the one you're looking for.  The `--alpha` option
will rearrange the data so that they're in alphabetical order, so you'll
have a nice ordered list to choose from:

    bl3-profile-edit profile.sav newprofile.sav --alpha

## Clear Customizations

If for some reason you'd like to clear your profile of all found
customizations, you can do so with `--clear-customizations`.  (This was
honestly mostly just useful to myself when testing the app.)

    bl3-profile-edit profile.sav newprofile.sav --clear-customizations

## Unlocks

There are a number of things you can unlock with the utility, all
specified using the `--unlock` argument.  You can specify this
multiple times on the commandline, to unlock more than one thing
at once, like so:

    bl3-profile-edit profile.sav newprofile.sav --unlock lostloot --unlock bank

### Lost Loot and Bank Capacity

The `lostloot` and `bank` unlocks will give you the maximum number
of SDUs for the Lost Loot machine and Bank, respectively:

    bl3-profile-edit profile.sav newprofile.sav --unlock lostloot
    bl3-profile-edit profile.sav newprofile.sav --unlock bank

### Customizations

You can specify various types of cosmetics to unlock individually,
which will give you all known customizations of that type.  (Note that
as new content is released, this editor will have to be updated to
include the new customizations.)  They can be individually unlocked
with any of the following:

    bl3-profile-edit profile.sav newprofile.sav --unlock skins
    bl3-profile-edit profile.sav newprofile.sav --unlock heads
    bl3-profile-edit profile.sav newprofile.sav --unlock echothemes
    bl3-profile-edit profile.sav newprofile.sav --unlock emotes
    bl3-profile-edit profile.sav newprofile.sav --unlock decos
    bl3-profile-edit profile.sav newprofile.sav --unlock weaponskins
    bl3-profile-edit profile.sav newprofile.sav --unlock trinkets

Alternatively, you can unlock *all* customizations all at once, by
using the `customizations` unlock:

    bl3-profile-edit profile.sav newprofile.sav --unlock customizations

**Note:** DLC-locked customizations, such as the Gold Pack, or any
customization specific to a story DLC, will remain unavailable even
if unlocked via this utility.  If you later purchase the DLC in question,
though, the relevant cosmetics should show up as available immediately.

### All Unlocks at Once

You can also use `all` to unlock all the various `--unlock`
options at once, without having to specify each one individually:

    bl3-profile-edit profile.sav newprofile.sav --unlock all

## Import Bank Items

The `-i`/`--import-items` option will let you import items into
your bank, of the sort you can export using `-o items`.  Simply
specify a text file as the argument to `-i` and it will load in
any line starting with `BL3(` as an item into the savegame:

    bl3-profile-edit profile.sav newprofile.sav -i items.txt

Note that by default, the app will not allow Fabricators to be
imported into the bank, since the player doesn't have a good way to
get rid of them.  You can tell the app to allow importing
Fabricators anyway with the `--allow-fabricator` option (which has
no use when not used along with `-i`/`--import-items`)

    bl3-profile-edit profile.sav newprofile.sav -i items.txt --allow-fabricator

If the utility can't tell what an item is during import (which may
happen if BL3 has been updated but this editor hasn't been updated
yet), it will refuse to import the unknown items, unless
`--allow-fabricator` is specified, since the unknown item could be
a Fabricator.  Other edits and imports can still happen, however.

If you have items saved in a CSV file (such as one exported using
`-o items --csv`), you can add the `--csv` argument to import items
from the CSV:

    bl3-profile-edit profile.sav newprofile.sav -i items.csv --csv

When reading CSV files, any valid BL3 item code found by itself in
a field in the CSV will be imported, so the CSV doesn't have to
be in the exact same format as the ones generated by `-o items --csv`.

# Importing Raw Protobufs

If you've saved a profile in raw protobuf format (using the
`-o protobuf` option, or otherwise), you may want to re-import it
into the profile, perhaps after having edited it by hand.  This can
be done with the separate utility `bl3-profile-import-protobuf`.  This
requires a `-p`/`--protobuf` argument to specify the file where
the raw protobuf is stored, and a `-t`/`--to-filename` argument,
which specifies the filename to import the protobufs into:

    bl3-profile-import-protobuf -p edited.pbraw -t profile.sav

By default this will prompt for confirmation before actually
overwriting the file, but you can use the `-c`/`--clobber` option
to force it to overwrite without asking:

    bl3-profile-import-protobuf -p edited.pbraw -t profile.sav -c

**NOTE:** This (and the JSON import) is the one place where these
utilities *expect* to overwrite the file you're giving it.  In the
above examples, it requires an existing `old.sav` file, and the
savefile contents will be written directly into that file.  This
option does *not* currently create a brand-new valid savegame for
you.

# Importing JSON

If you saved a profile in JSON format (using the `-o json` option),
you may want to re-import it into the profile, perhaps after having
edited it by hand.  This can be done with the separate utility
`bl3-profile-import-json`.  This requires a `-j`/`--json` argument to
specify the file where the JSON is stored, and a `-t`/`--to-filename`
argument, which specifies the filename to import the JSON into:

    bl3-profile-import-json -j edited.json -t profile.sav

By default this will prompt for confirmation before actually
overwriting the file, but you can use the `-c`/`--clobber` option
to force it to overwrite without asking:

    bl3-profile-import-json -j edited.json -t profile.sav -c

**NOTE:** This (and the protobuf import) is the one place where these
utilities *expect* to overwrite the file you're giving it.  In the
above examples, it requires an existing `old.sav` file, and the
savefile contents will be written directly into that file.  This
option does *not* currently create a brand-new valid savegame for
you.

# Profile Info Usage

The `bl3-profile-info` script is extremely simple, and just dumps a bunch
of information about the specified savegame to the console.  If you
specify the `-v`/`--verbose` option, it'll output a bunch more info
than it ordinarily would, such as bank and lost loot contents:

    bl3-save-info -v profile.sav

Instead of doing a global "verbose" option, you can instead choose
to output just some of the extra information, though at the moment there's
only one extra option, so the two are identical:

## Items/Inventory

The `-i`/`--items` argument will output your bank and Lost Loot machine
contents, including item codes which could be put in a text file for
later import:

    bl3-profile-info -i profile.sav

