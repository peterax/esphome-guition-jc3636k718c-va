# Modular screens (beta)

Goal: pick which carousel screens are compiled in, straight from the YAML - comment a
line in `packages:` and the screen is gone from the firmware (and the flash it used).

This is a **beta** layout on the `beta` branch. It needs to be compiled on a device
(there is no local validation here). Until it is verified, `main` keeps the single-file
config.

## How you choose screens

Top of `guition-va.yaml`:

```yaml
packages:
  # core (clock + player) is always in the main file
  timer: !include screens/timer.yaml
  cars:  !include screens/cool-cars.yaml
  space: !include screens/space-wars.yaml   # comment out to drop Space Wars
```

Remove/comment a line -> that screen's page, scripts, globals and game tick are not
compiled, and its carousel slot disappears. Nothing else to edit.

## How it stays decoupled (the contract)

ESPHome merges package lists (globals/scripts/interval/lvgl.pages/esphome.on_boot all
concatenate), so each screen file is self-contained and the core never names a screen's
symbols. The glue is a few plain globals in the core:

- `g_base` (int) - id of the current carousel screen. Fixed ids: 0=clock, 1=player,
  2=timer, 3=cars, 4=space (an id never changes, even if a screen is absent).
- `g_order[12]`, `g_order_n` - carousel order, built at boot. Core seeds clock+player;
  each screen package appends its id in an `esphome.on_boot` step (priority sets the
  position). Swipe left/right just steps through `g_order` and wraps.
- `g_nav_req` (bool) + `g_nav_anim` (int: 0=right 1=left 2=top 3=bottom) - core sets
  these on a screen change; each screen package owns a small handler that, when
  `g_base == <my id>`, runs its own `lvgl.page.show` with the matching animation and
  clears `g_nav_req`. Core only `page.show`s its own (clock/player).
- `g_knob_capture` (bool) + `g_knob_delta` (int) - when a screen wants the knob (game
  running, timer idle), it sets `g_knob_capture=true`; the core knob handler then just
  accumulates +/-1 into `g_knob_delta` instead of changing volume. The screen reads and
  zeroes `g_knob_delta` in its own tick. Core never names a game variable.
- `g_scores_reset` (bool) - Settings "reset scores" / factory reset set this; each game
  package clears its own score globals when it sees the flag. Core does not touch game
  score arrays.

So a screen package contributes: its `globals`, its `script`s, its game-tick `interval`,
its `lvgl.pages` entry, one `on_boot` step to register its carousel id, and one nav
handler. It reads/writes only the shared core globals above.

## Status

- [ ] core refactor: data-driven carousel (`g_order`), nav via `g_nav_req`, knob via
      `g_knob_capture`/`g_knob_delta`, scores via `g_scores_reset`
- [ ] extract Space Wars -> `screens/space-wars.yaml`
- [ ] extract Cool Cars -> `screens/cool-cars.yaml`
- [ ] extract Timer -> `screens/timer.yaml`
- [ ] verify on device, then consider merging to `main`
