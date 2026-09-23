# Type Is Code

A terminal puzzle game where you solve environmental puzzles by
**rewriting the source code of the world**

## How to run

Requires Python 3.10+ (uses `X | None` type hints), no third-party
dependencies.

```bash
python3 main.py                 # start at level 1
python3 main.py --level 4       # start directly at level 4
python3 main.py -l 2            # short form
python3 main.py --list          # list available levels
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
                   CircuitLine            -- the 4-slot "compiler"
registry.py       PropertyRegistry       -- the master, mutable,
                                            class -> {property: value}
                                            dictionary every instance
                                            reads from every tick
level.py          Level                  -- grid, movement/push rules,
                                            win/lose conditions
levels_data.py    build_level1/2/3()     -- concrete puzzle layouts
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
2. **Open Sesame** — introduces Door; open it to pass.
3. **Two Statements** — disarm a Trap, then seal a void, to
   reach the goal.
4. **Spacious Statements** — two tall workshops, a corridor whose GOAL is
   sealed behind a booby-trapped wall, and the token-fusion trick
   described below.

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
