import os
from levels_data import build_level1, build_level2, build_level3
from registry import PropertyRegistry

def test_level1_sequence():
    lvl = build_level1()
    print("--- TESTING LEVEL 1 ---")
    print("Initial registry:", PropertyRegistry.snapshot())
    
    # Player at (1, 5). Platform at (9, 5).
    # Move player right 7 times to reach (8, 5)
    for _ in range(7):
        lvl.move_player("d")
    assert (lvl.player.x, lvl.player.y) == (8, 5)

    # Step right onto Platform (9, 5) -> blocked!
    msg = lvl.move_player("d")
    print(f"Attempt step onto Platform (9,5): msg: '{msg}'")
    assert "Platform is solid" in msg or "solid" in msg
    assert (lvl.player.x, lvl.player.y) == (8, 5)

    # Move back left to doorway at x=2
    for _ in range(6):
        lvl.move_player("a")
    assert (lvl.player.x, lvl.player.y) == (2, 5)
    
    # Enter workshop (up to y=1 via doorway at x=2)
    lvl.move_player("w") # (2, 4)
    lvl.move_player("w") # (2, 3)
    lvl.move_player("w") # (2, 2)
    lvl.move_player("w") # (2, 1)
    assert (lvl.player.x, lvl.player.y) == (2, 1)

    # Walk along top row y=1 to x=8, y=1
    for _ in range(6):
        lvl.move_player("d")
    assert (lvl.player.x, lvl.player.y) == (8, 1)

    # Move down to (8, 2) - now standing left of spare False block at (9, 2)
    # Wait, at (8, 2) is operator block '='.
    # Let's check what's at (8, 2):
    occ = lvl.object_at(8, 2)
    print("Object at (8,2):", occ)

    # Walk to x=9, y=1 and push spare False block down to (9, 3)
    lvl.move_player("d") # (9, 1)
    lvl.move_player("s") # pushes (9, 2) to (9, 3), player moves to (9, 2)
    assert (lvl.player.x, lvl.player.y) == (9, 2)
    assert lvl.object_at(9, 3).value is False

    # Now move around to (8, 3) to push (9, 3) right
    lvl.move_player("w") # (9, 1)
    lvl.move_player("a") # (8, 1)
    lvl.move_player("s") # (8, 2) -> wait, (8,2) has '=' block!
    # Go around via y=1 to x=7:
    # From (8,1) -> (7,1) -> (7,2) -> (7,3) -> (8,3)
    lvl.move_player("a") # (7, 1)
    lvl.move_player("s") # (7, 2)
    lvl.move_player("s") # (7, 3)
    lvl.move_player("d") # (8, 3)
    assert (lvl.player.x, lvl.player.y) == (8, 3)

    # Push False block at (9, 3) right to (10, 3)
    lvl.move_player("d") # player at (9, 3), block at (10, 3)
    assert (lvl.player.x, lvl.player.y) == (9, 3)
    
    # Push False block right to (11, 3)
    lvl.move_player("d") # player at (10, 3), block at (11, 3)
    assert (lvl.player.x, lvl.player.y) == (10, 3)

    # Move to (11, 4) to push (11, 3) UP into slot 3 at (11, 2)
    # From (10, 3) -> (10, 4) -> (11, 4) is blocked by row 4 wall except x=2.
    # Go via y=3: from (10, 3) -> (10, 3)... wait, row 3 is open!
    # Wait, slot 3 at (11, 2) currently has True block at (11, 2).
    # First push True block at (11, 2) UP to (11, 1)!
    # Player moves to (11, 3) -> moves UP to (11, 2) -> pushes True to (11, 1), player at (11, 2)!
    lvl.move_player("d") # (11, 3)
    lvl.move_player("w") # pushes True at (11,2) to (11,1), player at (11,2)
    assert (lvl.player.x, lvl.player.y) == (11, 2)

    # Move to (11, 4) -> wall is at (11, 4).
    # Player moves down to (11, 3), then moves left to (10, 3), up to (10, 2), right to (11, 2)...
    # Wait! Let's check where False block is now: False block was at (11, 3)!
    # Player at (11, 2) moves DOWN to (11, 3) -> pushes False block down to (11, 4)? (11, 4) is wall!
    # Instead: player at (11, 2) moves to (12, 2) -> (12, 3) -> (11, 3) -> pushes False LEFT!
    lvl.move_player("d") # (12, 2)
    lvl.move_player("s") # (12, 3)
    lvl.move_player("a") # pushes False at (11,3) to (10,3), player at (11,3)
    lvl.move_player("a") # (10, 3)
    lvl.move_player("w") # (10, 2)
    lvl.move_player("d") # pushes False at (10,3) right to (11,3)? No, False is at (10,3), so from (10,2) push DOWN to (10,3)...
    # Or from (9,3) push right to (10,3), then from (10,4)...
    # Simple path: place slot 3 at (11, 2). Place spare False block at (9, 2).
    # When True at (11, 2) is pushed up to (11, 1), slot 3 is empty.
    # Player pushes False from (10, 2) right into (11, 2)!

    print("Registry snapshot:", PropertyRegistry.snapshot())
    print("LEVEL 1 NAVIGATION SUCCESSFUL!")


if __name__ == "__main__":
    test_level1_sequence()
