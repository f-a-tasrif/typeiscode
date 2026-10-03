# Type Is Code

A terminal puzzle game where you solve environmental puzzles by
**rewriting the source code of the world**

## How to run

Requires Python 3.10+ (uses `X | None` type hints), no third-party
dependencies.

```bash
python3 main.py                 # start at level 1
python3 main.py --level 8       # start directly at level 8
python3 main.py -l 5            # short form
python3 main.py --list          # list available levels
python3 main.py --renderer panda  # Phase-1 3D graybox (needs: pip install panda3d)
```

## Controls

| Key | Action |
|-----|--------|
| `w` / `a` / `s` / `d` | Move up / left / down / right (walking into a pushable code block pushes it) |
| `r` | Restart the current level |
| `h` | Show help |
| `q` | Quit |

## The core mechanic

Each level has one or more **circuit lines**: four grid cells that act
as a tiny compiler. They read, left to right:

```
[CLASS] [PROPERTY] [OPERATOR] [VALUE]
Path   .   solid     =          false
```

Pushable **code blocks** (`Path.`/class tokens, `solid`/property tokens,
` = `/operators, `True`/`False` value tokens) sit on the grid. Push the
wrong block out of a slot and push the correct one in, and the moment
all four slots hold a valid statement, the engine "compiles" it and
writes it into a **live property registry**. Every object of that
class in the level re-evaluates its behavior on the very next tick —
seal a void with `Path.solid`, open `Door.isOpen`, or disarm
`Trap.isLethal` to clear the way to the goal (`GOAL`).

**The void trap:** every `Path` cell in the corridor is a bottomless
void while the logic says `Path.solid = False`. Stepping into it drops
the character into the void — it vanishes (invisible) and the run ends.
Compile `Path.solid = True` and the void trap is removed: the cell
becomes plain walkable ground. Change the logic back and the trap
reappears.

## OOP architecture

```
game_object.py    GameObject (abstract base)
                    +-- Wall, Floor, Goal, Player
                    +-- Platform   (the Path cell: Path.solid = False is a void)
                    +-- Door       (is_blocking() reads Door.isOpen)
                    +-- Trap       (is_lethal()   reads Trap.isLethal)
blocks.py         CodeBlock(GameObject)  -- pushable syntax tokens
                                             (incl. the NOT token)
                   CircuitLine            -- the 4-slot "compiler"
                                             (circuit levels only)
registry.py       PropertyRegistry       -- the master, mutable,
                                            class -> {property: value}
                                            dictionary every instance
                                            reads from every tick
level.py          Level                  -- grid, movement/push rules,
                                            win/lose conditions;
                                            rule_mode "circuit" (1-4)
                                            vs "global" (5-8)
levels_data.py    build_level1..8        -- concrete puzzle layouts;
                   _build_from_map       -- data-driven global levels
                                            from maps_data.py
maps_data.py      MAPS                   -- level 5-8 maps ported from
                                            type-is-code-maps.html
engine.py         GameEngine             -- terminal UI / main loop
main.py           entry point
```

This directly demonstrates the concepts described in the design
brief:

* **Inheritance** — `Platform`, `Door`, `Trap`, `Player`, `Wall` all
  derive from `GameObject`.
* **Polymorphism** — every object's `is_blocking()` / `is_lethal()`
  is overridden differently, and the engine calls these same two
  methods on *any* object without caring which subclass it is.
* **Dynamic property dictionaries** — `PropertyRegistry` is the
  single source of truth; nothing is hard-coded or cached, so a
  circuit compiling `Path.solid = true` retroactively changes
  every `Platform` instance's behavior on the next tick.

## Levels

1. **First Compile** — tutorial: seal the void in the path.
2. **Spacious Statements** — two tall workshops, a corridor whose GOAL is
   sealed behind a booby-trapped wall, and the token-fusion trick
   described below.
3. **Serpentine Vault** — both rules use `NOT` (`NOT True` opens
   the table gap, `NOT False` opens the door).
4. **Swap the Values** — rules revert to defaults when a value
   leaves; arm the trap rule, then open the door.
5. **Four Chambers, Three Gates** — the longest chain: `True`
   opens the door and seals the table, `NOT True` disarms the
   trap.

## rule_mode: "circuit" vs "global"

Levels 1-4 run in `circuit` mode: each `CircuitLine` owns one
`(CLASS, PROP)` target learned from its 4 slots, and a statement can
also be assembled anywhere (rows read left-to-right, columns
top-to-bottom).

Levels 5-8 run in `global` mode (`Level.rule_mode = "global"`,
fusion disabled):

* Rules are read **horizontally only**, left to right, in one row:
  `CLASS PROP = VALUE`, where the value may be `NOT <bool>`, which
  inverts it (`NOT True` is False).
* Rules are found **anywhere** on the board by scanning blocks in
  row-major order; later rules override earlier ones. A stray token
  after the value is ignored.
* Only `(class, prop)` pairs present in the level's initial registry
  take effect; anything else is ignored.
* When a value leaves a rule, the registry **reverts to its default**
  on the very next recompile.
* Defaults for these levels (`RULES_REGISTRY`): `Wall.solid = True`,
  `Platform.isSolid = False` (the path starts as an open void, like
  level 1), `Door.isOpen = False`, `Trap.isLethal = True`.

## New tokens and obstacles (levels 5-8)

* **`NOT` token** (`blocks.NOT`): placed directly after `=`, with the
  boolean value directly after it. Rendered as its own pink chip in
  the GUI.
* **Path traps in levels 5-8** are level 1's own `Platform`:
  plain floor while `Path.solid = True`, lethal void pit while
  `False` (stepping in drops the character, invisible, run over).
  Levels 5 and 8 feed their Path rule with `True` instead of the
  HTML's `False`, and level 6's first-room `True` is a `False`, so
  every Path rule seals into safe floor (see `_flip_value_block`
  in `levels_data.py`). All four replays pass.

## Fusing tokens into a new GOAL (Level 4)

Push the `Path.` class token (first workshop) next to the `open`
property token (second workshop) — horizontally or vertically, in
either order. The moment the two blocks touch they **fuse**: both
tokens are consumed and a brand-new `GOAL` tile blooms on the cell the
pushed token occupied, right in front of you — no pressing rounds. The
new flag replaces the old one: level 4's original corridor `GOAL`
vanishes the moment the fusion completes, so only one flag exists at a
time.

## Extending the game

Add a new obstacle class in `game_object.py` (override
`is_blocking`/`is_lethal`/`is_win`), add matching glyphs to
`blocks.py`'s `_GLYPHS`, and build a new level function in
`levels_data.py` following the "workshop + corridor" pattern used by
the existing levels (see the module docstring there for the layout
rules that keep puzzles from being bypassable).
