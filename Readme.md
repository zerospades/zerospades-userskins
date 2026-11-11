# ZeroSpades user skins

Player skins for [ZeroSpades](https://github.com/zerospades/zerospades). Work in progress.

A skin is picked by **the player's in-game name**. There is no protocol extension and
nothing to configure: the client looks the name up here and draws what it finds. Since the
server is the only thing that sets names, the server decides who wears what.

## The two folders

| | `reserved-skins/` | `user-skins/` |
|---|---|---|
| What | the official catalogue: defaults and gameplay roles | personal skins |
| Who may change one | maintainers | the GitHub user who created it |
| Shipped | with the client | optional download |
| May it affect gameplay | yes, that is the point | no, cosmetic only |

`reserved-skins/` is an interface. Once servers rely on a name there, it cannot be renamed
or removed, and its silhouette cannot change much. `user-skins/` is yours to change or
delete whenever you like, because nothing depends on it.

Reserved names resolve **first**, so a name in `reserved-skins/` can never be taken by a
user skin. A server that wants to protect a reserved name from players simply gives a
player asking for it a different name — that is server policy, not something this repo or
the client enforces.

## Making a skin

1. Copy `reserved-skins/Deuce/` — the default, with every part in all four variants.
2. Rename the copy to your **in-game name** under `user-skins/`.
3. Delete the parts you did not change. Anything you leave out comes from `Deuce`, so a
   skin that changes only the head is one `Head.kv6`.

One skin per GitHub user: the one you created. Nothing records that — the owner of a skin
is whoever authored the earliest commit touching its folder, which git already knows. CI
warns when a pull request edits someone else's skin or adds a second one for the same
author; a maintainer can still merge it.

Don't rename or delete a skin folder: the folder name is the lookup key, so renaming it
silently takes the skin away from the player wearing it.

### Layout

```
user-skins/<in-game name>/
	meta.json                  # optional, credits only
	Arm.kv6  ArmRight.kv6  Arms.kv6  Dead.kv6  Head.kv6
	Leg.kv6  LegCrouch.kv6  LegRight.kv6  LegRightCrouch.kv6
	Torso.kv6  TorsoCrouch.kv6  UpperArm.kv6  UpperArmRight.kv6
	Rifle/  SMG/  Shotgun/     # optional, same 13 names, used for that weapon
```

The 13 parts at the top are used whatever the player holds. A `Rifle/`, `SMG/` or
`Shotgun/` folder overrides them for that weapon, exactly as the base game's own sets do —
so a skin *can* depend on the weapon, but it does not have to.

A skin may ship one `Player.2kv6` scene in place of loose `.kv6` parts.

A skin must **not** ship `Headlamp.kv6` or `XmasHat.kv6`. Those are worn over whatever head
a skin provides and stay shared by every skin.

### meta.json

Optional, and for credit only — it is never consulted to decide who owns a skin:

```json
{
	"title": "YourInGameName",
	"description": "One line.",
	"authors": ["whoever modelled it"]
}
```

## Rules a skin has to follow

- **Colorable.** Team colour goes where the default uniform is coloured. A player must be
  able to tell your team at a glance.
- **Readable silhouette.** Stay within the standard player bounds and keep the shape
  recognisable as a player at distance. Nobody should be harder to see because they wear a
  skin, and nobody should get an advantage from wearing one.
- **Every part present or inherited.** A missing part falls back to `Deuce`, so a
  half-finished skin still draws.

## How a name becomes a skin

The client folds the name — trims it and lowercases it — then takes the first match:

1. `reserved-skins/<name>`
2. `user-skins/<name>`
3. the name with trailing digits removed, tried against 1 and 2 again
4. the base game's own set for the weapon the player holds

Step 3 is there because a server appends a number when a name is already in game: with
three `Deuce`s in the server they are named `Deuce`, `Deuce1` and `Deuce2`, and all three
should look like Deuce. It also lets a server deploy several of the same role — `Zombie`,
`Zombie1`, `Zombie2`. An exact match is always tried before any digits are stripped, so a
skin for a player whose name genuinely ends in a digit still works.

Two folders whose folded names collide are rejected by CI.
