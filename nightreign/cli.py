#!/usr/bin/env python3
"""Single entry point for the project: the `nr` command.

    nr setup            copy the game files into inputs/ (run once, or after a patch)
    nr data             regenerate everything in data/ (relics, params, weapons, rosters)
    nr data <step>      regenerate one step: relics | params | weapons | nightlords | npcs
    nr optimize ...     find the best relics for a character vs a boss (coming)
    nr demo             run the example matchup / pipeline

The CLI stays thin: it only wires arguments to functions in datagen/ and engine/.
"""
import argparse
import runpy
import shutil
import sys
from pathlib import Path

from nightreign.resources import constants

# Ordered so dependencies come first (effects need params+relics; rosters need npc_params).
DATA_STEPS = ["relics", "params", "effects", "weapons", "nightlords", "npcs", "vessels", "scaling"]


def cmd_setup(args):
    constants.INPUTS.mkdir(parents=True, exist_ok=True)

    if args.game_path:
        # accept either the Game/ folder or the regulation.bin file directly
        p = Path(args.game_path).expanduser()
        candidates = [p if p.is_file() else p / "regulation.bin"]
    else:
        candidates = [d / "regulation.bin" for d in constants.STEAM_GAME_DIRS]

    src = next((c for c in candidates if c.is_file()), None)
    if not src:
        print("regulation.bin not found. Pass its location explicitly:")
        print('  nr setup "/path/to/ELDEN RING NIGHTREIGN/Game"')
        print("Tried:")
        for c in candidates:
            print(f"  {c}")
        return 1

    shutil.copy2(src, constants.REGULATION)
    print(f"Copied {src}\n     -> {constants.REGULATION}")
    if not constants.SAVE.exists():
        print(f"NOTE: place your save backup at {constants.SAVE} "
              f"(copy of AppData/Roaming/Nightreign/.../NR0000.sl2).")
    return 0


def cmd_data(args):
    from nightreign.datagen import (params, weapons, relics, nightlords, npcs,
                                    vessels, effects, scaling)
    runners = {"relics": relics.run, "params": params.run, "effects": effects.run,
               "weapons": weapons.run, "nightlords": nightlords.run, "npcs": npcs.run,
               "vessels": vessels.run, "scaling": scaling.run}
    steps = [args.step] if args.step else DATA_STEPS
    for step in steps:
        print(f"[{step}]")
        runners[step]()
    print("data: done.")
    return 0


def cmd_optimize(_args):
    print("optimize: not implemented yet — this is the next milestone.")
    return 0


def cmd_demo(args):
    name = args.name or "pipeline"
    path = constants.ROOT / "examples" / f"{name}_demo.py"
    if not path.exists():
        print(f"no demo '{name}' at {path}")
        return 1
    runpy.run_path(str(path), run_name="__main__")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="nr", description="Nightreign relic build optimizer")
    sub = parser.add_subparsers(dest="command", required=True)

    p_setup = sub.add_parser("setup", help="copy game files into inputs/")
    p_setup.add_argument("game_path", nargs="?",
                         help="path to the game's Game/ folder or regulation.bin "
                              "(auto-detected from common Steam locations if omitted)")
    p_setup.set_defaults(func=cmd_setup)

    p_data = sub.add_parser("data", help="regenerate data/ (all or one step)")
    p_data.add_argument("step", nargs="?", choices=DATA_STEPS, help="a single step (default: all)")
    p_data.set_defaults(func=cmd_data)

    p_opt = sub.add_parser("optimize", help="find the best relics (coming)")
    p_opt.add_argument("character", nargs="?")
    p_opt.add_argument("boss", nargs="?")
    p_opt.add_argument("--deep", action="store_true", help="generalist / Deep of Night")
    p_opt.set_defaults(func=cmd_optimize)

    p_demo = sub.add_parser("demo", help="run an example (matchup | pipeline)")
    p_demo.add_argument("name", nargs="?", choices=["matchup", "pipeline"])
    p_demo.set_defaults(func=cmd_demo)

    args = parser.parse_args(argv)
    return args.func(args) or 0


if __name__ == "__main__":
    sys.exit(main())
