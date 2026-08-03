from level import Level
from game_object import Platform
from blocks import CodeBlock, CircuitLine, CLASS, PROP, OP, VALUE
from registry import PropertyRegistry

def test_screenshot_layout():
    DEFAULT_REGISTRY = {
        "Platform": {"isSolid": True},
        "Door": {"isOpen": False},
        "Trap": {"isLethal": True},
    }
    lvl = Level("Screenshot Test", 16, 7, DEFAULT_REGISTRY)
    lvl.add_wall_border()
    lvl.set_player(1, 5)
    lvl.set_goal(14, 5)
    platform = Platform(9, 5)
    lvl.add_object(platform)

    # Circuit line defined with default slots at (4,2), (6,2), (8,2), (11,2)
    slots = [(4, 2), (6, 2), (8, 2), (11, 2)]
    circuit = CircuitLine("Bridge Statement", slots)
    lvl.add_circuit(circuit)

    # Place blocks AT ADJACENT POSITIONS (7,2), (8,2), (9,2), (10,2) exactly as in User's Screenshot 2!
    lvl.add_object(CodeBlock(7, 2, CLASS, "Platform"))
    lvl.add_object(CodeBlock(8, 2, PROP, "isSolid"))
    lvl.add_object(CodeBlock(9, 2, OP, "="))
    lvl.add_object(CodeBlock(10, 2, VALUE, False))

    # Recompile circuits
    lvl.recompile_circuits()

    print("Circuit result text:", circuit.render_text())
    print("Live registry:", PropertyRegistry.snapshot())
    print("Platform is_blocking():", platform.is_blocking())

    assert circuit.last_result == "Platform.isSolid = False", f"Expected statement to compile! Got: {circuit.last_result}"
    assert PropertyRegistry.get("Platform", "isSolid") is False, "Expected Platform.isSolid to be False!"
    assert platform.is_blocking() is False, "Expected Platform to be passable (is_blocking=False)!"
    
    # Try stepping onto platform (9, 5)
    lvl.player.x, lvl.player.y = 8, 5
    msg = lvl.move_player("d")
    print(f"Move player right onto Platform (9,5): msg='{msg}', player pos=({lvl.player.x},{lvl.player.y})")
    assert (lvl.player.x, lvl.player.y) == (9, 5), "Player should successfully step onto Platform!"
    print("\nUSER SCREENSHOT SCENARIO TEST PASSED 100% SUCCESSFUL!")

if __name__ == "__main__":
    test_screenshot_layout()
