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

# Ordered so dependencies come first (effects need params+relics; rosters need
# npc_params; accessories need effect_params from the params step).
DATA_STEPS = ["relics", "params", "effects", "weapons", "magic", "sword_arts",
              "accessories", "goods", "motion_values", "weapon_affixes",
              "characters", "nightlords", "npcs", "vessels", "scaling", "animations"]
# opt-in steps, excluded from the default "nr data" run (need extra tooling):
#   icons -> game item icons for the web UI (needs Pillow; writes gitignored assets)
#   art   -> hero renders + scenario illustrations for the web UI (needs Pillow)
EXTRA_STEPS = ["icons", "art"]


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
                                    vessels, effects, scaling, characters,
                                    weapon_affixes, motion_values, animations,
                                    magic, sword_arts, accessories, goods, icons, art)
    runners = {"relics": relics.run, "params": params.run, "effects": effects.run,
               "weapons": weapons.run, "weapon_affixes": weapon_affixes.run,
               "magic": magic.run, "sword_arts": sword_arts.run,
               "accessories": accessories.run, "goods": goods.run,
               "motion_values": motion_values.run,
               "animations": animations.run, "icons": icons.run, "art": art.run,
               "characters": characters.run, "nightlords": nightlords.run,
               "npcs": npcs.run, "vessels": vessels.run, "scaling": scaling.run}
    steps = [args.step] if args.step else DATA_STEPS
    for step in steps:
        print(f"[{step}]")
        runners[step]()
    print("data: done.")
    return 0


def cmd_optimize(args):
    from nightreign.optimize import runner
    from nightreign.resources import actions
    wtype = args.weapon_type
    if wtype and wtype.lower() in ("generic", "générique", "any", "toute"):
        wtype = runner.GENERIC
    results = runner.optimize(
        args.character, boss=args.boss, weapon_type=wtype,
        level=args.level, weight=args.weight, don=args.don,
        toggles=tuple(args.toggle or ()), beam_k=args.beam, top=args.top,
        play=actions.parse_play_profile(args.play), types_count=args.types,
        max_weapon_level=args.max_weapon_level)
    print(runner.format_report(results, args.weight))
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
    p_data.add_argument("step", nargs="?", choices=DATA_STEPS + EXTRA_STEPS,
                        help="a single step (default: all standard steps; 'icons' is opt-in)")
    p_data.set_defaults(func=cmd_data)

    p_opt = sub.add_parser("optimize", help="find the best relic build")
    p_opt.add_argument("character", help="Nightfarer (e.g. Wylder, Duchess)")
    p_opt.add_argument("boss", nargs="?",
                       help="target Nightlord (omit = generalist vs all 8)")
    p_opt.add_argument("--weapon-type", help='fix the weapon type (e.g. "Greatsword"), '
                                             '"generic" for a weapon-agnostic relic '
                                             "build, or omit to try the best types")
    p_opt.add_argument("--level", type=int, default=15, help="character level (default 15)")
    p_opt.add_argument("--weight", type=float, default=0.5,
                       help="offense<->survival slider, 1.0 = pure offense (default 0.5)")
    p_opt.add_argument("--don", type=int, default=0,
                       help="Deep of Night level 1-5 (0 = normal expedition, no deep slots)")
    p_opt.add_argument("--toggle", action="append",
                       help="commit a playstyle toggle: caster, low_hp, situational, "
                            "status_build, starting_loadout, coop, triple_loadout "
                            "(repeatable)")
    p_opt.add_argument("--play", help='play profile, e.g. "melee=0.7,skill=0.2,crit=0.1" '
                                      "(default: melee=1 — action-gated buffs count only "
                                      "for the actions you declare)")
    p_opt.add_argument("--types", type=int, default=5,
                       help="weapon types to explore when none is fixed (default 5)")
    p_opt.add_argument("--max-weapon-level", type=int, default=25,
                       help="cap on droppable weapon levels (in-run progression; "
                            "default 25 = everything)")
    p_opt.add_argument("--beam", type=int, default=12, help="beam width (default 12)")
    p_opt.add_argument("--top", type=int, default=3, help="gameplans to show (default 3)")
    p_opt.set_defaults(func=cmd_optimize)

    p_ui = sub.add_parser("ui", help="local web UI for the optimizer")
    p_ui.add_argument("--port", type=int, default=8377)
    p_ui.add_argument("--no-browser", action="store_true")
    p_ui.set_defaults(func=lambda a: __import__("nightreign.ui.server", fromlist=["serve"])
                      .serve(a.port, not a.no_browser))

    p_demo = sub.add_parser("demo", help="run an example (matchup | pipeline)")
    p_demo.add_argument("name", nargs="?", choices=["matchup", "pipeline"])
    p_demo.set_defaults(func=cmd_demo)

    args = parser.parse_args(argv)
    return args.func(args) or 0


if __name__ == "__main__":
    sys.exit(main())
