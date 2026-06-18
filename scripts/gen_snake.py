#!/usr/bin/env python3
# Generates base/screens/snake.yaml (modular carousel screen, base id 9). Run from anywhere:
#   python scripts/gen_snake.py
#
# Free 360-degree snake (slither-style): the head has a heading angle the knob rotates; it moves
# forward every tick and the body is a chain of segments that each follow the one ahead at a fixed
# distance. Play area = the whole round screen bounded by a green ring; the snake passes under the
# score HUD. Up to 3 fruit (random sprites) are kept on the board, replenished over time (faster
# when only one is left); up to 2 skulls appear for a while and end the game if eaten.
#
# Body/fruit/skull widgets are a fixed pool (LVGL can't address a widget by a runtime index); each
# tick we set their positions/visibility from the float position globals.
import os

POOL = 40          # max body segments = number of segment widgets
SEG  = 9           # segment square (px)
SEGR = 4           # segment corner radius
SEG_DIST = 7.0     # spacing between segments (px)
R    = 168.0       # max head distance from centre (inside the ring)
RING_D = 344       # ring diameter (radius 172) -> sits just inside the 360 round display
SPEED0 = 3.2       # head speed px/tick (50ms tick)
TURN = 0.26        # radians turned per knob detent
EAT  = 12.0        # head-to-fruit distance that counts as eating
SKHIT = 13.0       # head-to-skull distance that kills
SELF_SKIP = 16     # body segments near the head skipped in self-collision (the neck; margin vs tight turns)
SELF_DIST = 6.0    # head-to-body distance that kills

NFRUIT = 12        # fruit sprites in the rotation (img_sn_fruit0..N-1)
NFSLOT = 3         # max fruit on the board at once
NSKULL = 2         # max skulls at once
FRUIT_WAIT = 90    # ticks between fruit top-ups (~4.5s); halved when only 1 fruit is left
SKULL_WAIT = 200   # ticks between skull spawns (~10s)
SKULL_LIFE = 220   # ticks a skull stays (~11s)

# sprites hosted on the beta branch during development (flip to /main/ at merge).
BASE = "https://raw.githubusercontent.com/MichalZaniewicz/esphome-guition-jc3636k718c-va/beta/assets/sprites/snake/"

# --- palette from snake-logo.png (green mosaic + dark navy wordmark) ---
PAGE_BG  = "0x0D1E15"
RING     = "0x3A8C4E"   # boundary ring (clear green)
HEAD     = "0xB8E86A"
BODY     = "0x52A049"
ACCENT   = "0xA6D85F"
ACCENT_TXT = "0x12241A"
BTN2     = "0x244A30"
BTN2_TXT = "0xCFE6C4"
GRAY     = "0x3A3A3D"
TXT      = "0xC6DCC0"
BADGE    = "0x6FB23F"
HUD      = "0xCFEAE4"
WORDMARK = "0x12212D"   # dark navy of the logo "SNAKE" wordmark (readable on the logo backdrop)


def seg_widgets():
    out = []
    for i in range(POOL):
        col = HEAD if i == 0 else BODY
        out.append(
            f"        - obj: {{ id: sn_s{i}, align: CENTER, x: 0, y: 0, width: {SEG}, height: {SEG}, "
            f"radius: {SEGR}, border_width: 0, bg_color: {col}, bg_opa: COVER, hidden: true }}"
        )
    return "\n".join(out)


def seg_updates():
    out = []
    for i in range(POOL):
        out.append(
f"""      - lvgl.widget.update:
          id: sn_s{i}
          hidden: !lambda 'return id(g_sn_len) <= {i};'
          x: !lambda 'return (int) lroundf(id(g_sn_x)[{i}]);'
          y: !lambda 'return (int) lroundf(id(g_sn_y)[{i}]);'""")
    return "\n".join(out)


def item_updates():
    out = []
    for s in range(NFSLOT):
        out.append(
f"""      - lvgl.widget.update:
          id: sn_fruit{s}
          hidden: !lambda 'return !id(g_sn_fon)[{s}];'
          x: !lambda 'return (int) lroundf(id(g_sn_fx)[{s}]);'
          y: !lambda 'return (int) lroundf(id(g_sn_fy)[{s}]);'""")
    for s in range(NSKULL):
        out.append(
f"""      - lvgl.widget.update:
          id: sn_skull{s}
          hidden: !lambda 'return !id(g_sn_skon)[{s}];'
          x: !lambda 'return (int) lroundf(id(g_sn_skx)[{s}]);'
          y: !lambda 'return (int) lroundf(id(g_sn_sky)[{s}]);'""")
    return "\n".join(out)


def clear_hides():
    out = [f"      - lvgl.widget.hide: sn_s{i}" for i in range(POOL)]
    out += [f"      - lvgl.widget.hide: sn_fruit{s}" for s in range(NFSLOT)]
    out += [f"      - lvgl.widget.hide: sn_skull{s}" for s in range(NSKULL)]
    return "\n".join(out)


def fruit_setters():
    blocks = []
    for s in range(NFSLOT):
        lines = [f"  - id: sn_fspr{s}", "    then:"]
        for k in range(NFRUIT):
            lines.append(
                f"      - if: {{ condition: {{ lambda: 'return id(g_sn_fi)[{s}] == {k};' }}, "
                f"then: [ lvgl.image.update: {{ id: sn_fruit{s}, src: img_sn_fruit{k} }} ] }}")
        blocks.append("\n".join(lines))
    return "\n".join(blocks)


def fruit_images():
    out = []
    for k in range(NFRUIT):
        out.append(
f"""  - id: img_sn_fruit{k}
    file: "{BASE}fruit{k}.png"
    type: RGB565
    transparency: alpha_channel""")
    return "\n".join(out)


def fruit_widgets():
    return "\n".join(
        f"        - image: {{ id: sn_fruit{s}, align: CENTER, x: 0, y: 0, src: img_sn_fruit0, hidden: true }}"
        for s in range(NFSLOT))


def skull_widgets():
    return "\n".join(
        f"        - image: {{ id: sn_skull{s}, align: CENTER, x: 0, y: 0, src: img_sn_skull, hidden: true }}"
        for s in range(NSKULL))


def fspr_dispatch():
    return "\n".join(
        f"                        - if: {{ condition: {{ lambda: 'return id(g_sn_newfruit) == {s};' }}, then: [ script.execute: sn_fspr{s} ] }}"
        for s in range(NFSLOT))


YAML = f"""# Snake - optional carousel screen (base id 9). Free 360-degree snake steered by the knob.
# Remove it: drop this file from your config's package "files:" list. Nothing else to edit.
# Scores (g_sn_top / g_sn_best) + the "Reset scores" settings action live here - fully self-contained.
#
# This file is GENERATED by scripts/gen_snake.py (the {POOL}-segment body pool, fruit rotation and
# their per-tick updates are repetitive). Edit the generator, not the blocks.

esphome:
  on_boot:
    - priority: 655
      then:
        - lambda: 'id(g_present)[9] = true;'   # register after clock/player/timer/cars/space
    - priority: 650
      then:
        - lambda: |-
            int g = id(g_wgrp_n)++;
            id(g_wgrp_labels) += (g ? "\\n" : ""); id(g_wgrp_labels) += "Snake";
            int o = id(g_wopt_n)++;
            id(g_wopt_group)[o] = g; id(g_wopt_label)[o] = "Reset scores"; id(g_wopt_kind)[o] = 1; id(g_wopt_ptr)[o] = &id(g_sn_reset);

globals:
  # --- scores (persistent) + reset flag ---
  - id: g_sn_best
    type: int
    restore_value: yes
    initial_value: '0'
  - id: g_sn_top
    type: int[10]
    restore_value: yes
  - id: g_sn_reset
    type: bool
    restore_value: no
    initial_value: 'false'
  # --- game state ---
  - id: g_sn_state    # 0=menu 1=playing 2=game over 3=how-to 4=scores
    type: int
    restore_value: no
    initial_value: '0'
  - id: g_sn_len      # live body segments
    type: int
    restore_value: no
    initial_value: '5'
  - id: g_sn_score
    type: int
    restore_value: no
    initial_value: '0'
  - id: g_sn_x        # segment X (centre coords, px); [0] = head
    type: float[{POOL}]
    restore_value: no
  - id: g_sn_y
    type: float[{POOL}]
    restore_value: no
  - id: g_sn_ang      # heading (radians)
    type: float
    restore_value: no
    initial_value: '0.0'
  - id: g_sn_dead
    type: bool
    restore_value: no
    initial_value: 'false'
  # --- fruit slots (up to {NFSLOT}) ---
  - id: g_sn_fx
    type: float[{NFSLOT}]
    restore_value: no
  - id: g_sn_fy
    type: float[{NFSLOT}]
    restore_value: no
  - id: g_sn_fi       # sprite index per slot
    type: int[{NFSLOT}]
    restore_value: no
  - id: g_sn_fon      # slot occupied
    type: bool[{NFSLOT}]
    restore_value: no
  - id: g_sn_fclk     # fruit spawn clock (ticks)
    type: int
    restore_value: no
    initial_value: '0'
  - id: g_sn_newfruit # slot that just spawned and needs its sprite set (-1 = none)
    type: int
    restore_value: no
    initial_value: '-1'
  # --- skull slots (up to {NSKULL}) ---
  - id: g_sn_skx
    type: float[{NSKULL}]
    restore_value: no
  - id: g_sn_sky
    type: float[{NSKULL}]
    restore_value: no
  - id: g_sn_skon
    type: bool[{NSKULL}]
    restore_value: no
  - id: g_sn_skage    # per-skull lifetime counter (ticks)
    type: int[{NSKULL}]
    restore_value: no
  - id: g_sn_skclk    # skull spawn clock (ticks)
    type: int
    restore_value: no
    initial_value: '0'

script:
{fruit_setters()}
  # HUD: current score.
  - id: sn_hud
    then:
      - lvgl.label.update: {{ id: lbl_sn_score, text: !lambda 'char b[12]; snprintf(b,sizeof(b),"%d",id(g_sn_score)); return std::string(b);' }}
  # Draw the body + fruit + skulls from the position globals (called every tick + on screen change).
  - id: sn_draw
    then:
{item_updates()}
{seg_updates()}
  # Hide all gameplay widgets (when leaving the play state).
  - id: sn_clear
    then:
{clear_hides()}
  # Start / restart a game.
  - id: sn_start
    then:
      - lambda: |-
          id(g_sn_state) = 1; id(g_sn_score) = 0; id(g_sn_dead) = false;
          id(g_sn_len) = 5; id(g_sn_ang) = -1.5708f;   // heading up
          for (int i = 0; i < {POOL}; i++) {{ id(g_sn_x)[i] = 0.0f; id(g_sn_y)[i] = i * {SEG_DIST}f; }}
          for (int s = 0; s < {NFSLOT}; s++) id(g_sn_fon)[s] = false;
          for (int s = 0; s < {NSKULL}; s++) {{ id(g_sn_skon)[s] = false; id(g_sn_skage)[s] = 0; }}
          id(g_sn_fclk) = 0; id(g_sn_skclk) = 0; id(g_sn_newfruit) = -1;
          id(g_knob_capture) = true; id(g_knob_delta) = 0;
          // first fruit in slot 0
          float a = (esp_random() % 62832) / 10000.0f;
          float rad = 60.0f + (esp_random() % 80);
          id(g_sn_fx)[0] = cosf(a) * rad; id(g_sn_fy)[0] = sinf(a) * rad;
          id(g_sn_fi)[0] = esp_random() % {NFRUIT}; id(g_sn_fon)[0] = true;
      - script.execute: sn_fspr0
      - script.execute: sn_screen
      - script.execute: sn_draw
      - script.execute: sn_hud
  # Game over: save the score into best + top 10 (knob stays captured here -> no volume).
  - id: sn_over
    then:
      - lambda: |-
          id(g_sn_state) = 2;
          int s = id(g_sn_score);
          if (s > id(g_sn_best)) id(g_sn_best) = s;
          for (int i = 0; i < 10; i++) {{
            if (s > id(g_sn_top)[i]) {{
              for (int j = 9; j > i; j--) id(g_sn_top)[j] = id(g_sn_top)[j-1];
              id(g_sn_top)[i] = s;
              break;
            }}
          }}
      - script.execute: sn_screen
  # Show the right widgets per state. Also the single knob-capture authority:
  # captured (no volume) only while playing + on game over; free in menu/how-to/scores.
  - id: sn_screen
    then:
      - lambda: 'id(g_knob_capture) = (id(g_sn_state) == 1 || id(g_sn_state) == 2);'
      # 1) hide everything
      - lvgl.widget.hide: sn_ring
      - script.execute: sn_clear
      - lvgl.widget.hide: lbl_sn_score
      - lvgl.widget.hide: sn_logo
      - lvgl.widget.hide: btn_sn_start
      - lvgl.widget.hide: btn_sn_howto
      - lvgl.widget.hide: btn_sn_scores
      - lvgl.widget.hide: lbl_sn_over
      - lvgl.widget.hide: lbl_sn_rec
      - lvgl.widget.hide: btn_sn_replay
      - lvgl.widget.hide: btn_sn_exit
      - lvgl.widget.hide: lbl_sn_howto_t
      - lvgl.widget.hide: sn_b1
      - lvgl.widget.hide: sn_b2
      - lvgl.widget.hide: sn_b3
      - lvgl.widget.hide: sn_b4
      - lvgl.widget.hide: lbl_sn_howto1
      - lvgl.widget.hide: lbl_sn_howto2
      - lvgl.widget.hide: lbl_sn_howto3
      - lvgl.widget.hide: lbl_sn_howto4
      - lvgl.widget.hide: lbl_sn_scores_t
      - lvgl.widget.hide: lbl_sn_scores1
      - lvgl.widget.hide: lbl_sn_scores2
      - lvgl.widget.hide: btn_sn_back
      # 2) show per state
      - if:   # MENU
          condition: {{ lambda: 'return id(g_sn_state) == 0;' }}
          then:
            - lvgl.widget.show: sn_logo
            - lvgl.widget.show: btn_sn_start
            - lvgl.widget.show: btn_sn_howto
            - lvgl.widget.show: btn_sn_scores
      - if:   # PLAY
          condition: {{ lambda: 'return id(g_sn_state) == 1;' }}
          then:
            - lvgl.widget.show: sn_ring
            - lvgl.widget.show: lbl_sn_score
            - script.execute: sn_draw
      - if:   # GAME OVER
          condition: {{ lambda: 'return id(g_sn_state) == 2;' }}
          then:
            - lvgl.widget.show: sn_logo
            - lvgl.widget.show: lbl_sn_over
            - lvgl.widget.show: lbl_sn_rec
            - lvgl.widget.show: btn_sn_replay
            - lvgl.widget.show: btn_sn_exit
            - lvgl.label.update: {{ id: lbl_sn_over, text: !lambda 'char b[24]; snprintf(b,sizeof(b),"Score: %d", id(g_sn_score)); return std::string(b);' }}
            - lvgl.label.update: {{ id: lbl_sn_rec,  text: !lambda 'char b[24]; snprintf(b,sizeof(b),"Best: %d", id(g_sn_best)); return std::string(b);' }}
      - if:   # HOW TO PLAY
          condition: {{ lambda: 'return id(g_sn_state) == 3;' }}
          then:
            - lvgl.widget.show: lbl_sn_howto_t
            - lvgl.widget.show: sn_b1
            - lvgl.widget.show: sn_b2
            - lvgl.widget.show: sn_b3
            - lvgl.widget.show: sn_b4
            - lvgl.widget.show: lbl_sn_howto1
            - lvgl.widget.show: lbl_sn_howto2
            - lvgl.widget.show: lbl_sn_howto3
            - lvgl.widget.show: lbl_sn_howto4
            - lvgl.widget.show: btn_sn_back
      - if:   # SCORES (top 10)
          condition: {{ lambda: 'return id(g_sn_state) == 4;' }}
          then:
            - lvgl.widget.show: lbl_sn_scores_t
            - lvgl.widget.show: lbl_sn_scores1
            - lvgl.widget.show: lbl_sn_scores2
            - lvgl.widget.show: btn_sn_back
            - lvgl.label.update:
                id: lbl_sn_scores1
                text: !lambda |-
                  std::string s; char b[24];
                  for (int i = 0; i < 5; i++) {{ if(i) s += "\\n"; if(id(g_sn_top)[i]>0){{ snprintf(b,sizeof(b),"%d.  %d",i+1,id(g_sn_top)[i]); }} else {{ snprintf(b,sizeof(b),"%d.  -",i+1); }} s += b; }}
                  return s;
            - lvgl.label.update:
                id: lbl_sn_scores2
                text: !lambda |-
                  std::string s; char b[24];
                  for (int i = 5; i < 10; i++) {{ if(i>5) s += "\\n"; if(id(g_sn_top)[i]>0){{ snprintf(b,sizeof(b),"%d.  %d",i+1,id(g_sn_top)[i]); }} else {{ snprintf(b,sizeof(b),"%d.  -",i+1); }} s += b; }}
                  return s;

interval:
  # Reset scores when the Widgets action fired (g_sn_reset) or on factory reset.
  - interval: 250ms
    then:
      - if:
          condition: {{ lambda: 'return id(g_sn_reset) || id(g_factory_reset);' }}
          then:
            - lambda: 'for (int i = 0; i < 10; i++) id(g_sn_top)[i] = 0; id(g_sn_best) = 0; id(g_sn_reset) = false;'
  # nav: show this screen when it is selected in the carousel
  - interval: 50ms
    then:
      - if:
          condition: {{ lambda: 'return id(g_nav_req) && id(g_base)==9;' }}
          then:
            - lambda: 'id(g_nav_req) = false; id(g_sn_state) = 0; id(g_knob_delta) = 0;'
            - if: {{ condition: {{ lambda: 'return id(g_nav_anim)==0;' }}, then: [lvgl.page.show: {{ id: page_snake, animation: move_left,   time: 250ms }}] }}
            - if: {{ condition: {{ lambda: 'return id(g_nav_anim)==1;' }}, then: [lvgl.page.show: {{ id: page_snake, animation: move_right,  time: 250ms }}] }}
            - if: {{ condition: {{ lambda: 'return id(g_nav_anim)==2;' }}, then: [lvgl.page.show: {{ id: page_snake, animation: move_top,    time: 250ms }}] }}
            - if: {{ condition: {{ lambda: 'return id(g_nav_anim)==3;' }}, then: [lvgl.page.show: {{ id: page_snake, animation: move_bottom, time: 250ms }}] }}
            - script.execute: sn_screen
  # Game tick: steer, move the head, drag the body, handle fruit/skulls + collisions.
  - interval: 50ms
    then:
      - if:
          condition: {{ lambda: 'return id(g_base) == 9 && id(g_sn_state) == 1;' }}
          then:
            - lambda: |-
                // steer (knob detents rotate the heading)
                int kd = id(g_knob_delta); id(g_knob_delta) = 0;
                id(g_sn_ang) += kd * {TURN}f;
                float spd = {SPEED0}f + id(g_sn_score) / 400.0f; if (spd > 5.5f) spd = 5.5f;
                // move head forward
                float hx = id(g_sn_x)[0] + cosf(id(g_sn_ang)) * spd;
                float hy = id(g_sn_y)[0] + sinf(id(g_sn_ang)) * spd;
                if (hx*hx + hy*hy > {R}f * {R}f) {{ id(g_sn_dead) = true; }}   // hit the ring
                else {{
                  id(g_sn_x)[0] = hx; id(g_sn_y)[0] = hy;
                  int len = id(g_sn_len);
                  // body chain: each segment trails the previous at SEG_DIST
                  for (int i = 1; i < len; i++) {{
                    float dx = id(g_sn_x)[i-1] - id(g_sn_x)[i], dy = id(g_sn_y)[i-1] - id(g_sn_y)[i];
                    float d = sqrtf(dx*dx + dy*dy);
                    if (d > 0.0001f) {{ id(g_sn_x)[i] = id(g_sn_x)[i-1] - dx/d*{SEG_DIST}f; id(g_sn_y)[i] = id(g_sn_y)[i-1] - dy/d*{SEG_DIST}f; }}
                  }}
                  // self collision (skip the neck)
                  for (int i = {SELF_SKIP}; i < len; i++) {{
                    float dx = hx - id(g_sn_x)[i], dy = hy - id(g_sn_y)[i];
                    if (dx*dx + dy*dy < {SELF_DIST}f * {SELF_DIST}f) {{ id(g_sn_dead) = true; break; }}
                  }}
                  // skull collision (fatal)
                  for (int s = 0; s < {NSKULL}; s++) if (id(g_sn_skon)[s]) {{
                    float dx = hx - id(g_sn_skx)[s], dy = hy - id(g_sn_sky)[s];
                    if (dx*dx + dy*dy < {SKHIT}f * {SKHIT}f) {{ id(g_sn_dead) = true; }}
                  }}
                  // eat fruit
                  for (int s = 0; s < {NFSLOT} && !id(g_sn_dead); s++) if (id(g_sn_fon)[s]) {{
                    float dx = hx - id(g_sn_fx)[s], dy = hy - id(g_sn_fy)[s];
                    if (dx*dx + dy*dy < {EAT}f * {EAT}f) {{
                      id(g_sn_fon)[s] = false;
                      id(g_sn_score) += 10;
                      int nl = id(g_sn_len) + 1; if (nl > {POOL}) nl = {POOL};
                      id(g_sn_x)[nl-1] = id(g_sn_x)[id(g_sn_len)-1]; id(g_sn_y)[nl-1] = id(g_sn_y)[id(g_sn_len)-1];
                      id(g_sn_len) = nl;
                    }}
                  }}
                }}
                if (!id(g_sn_dead)) {{
                  // keep up to {NFSLOT} fruit on the board; sooner when only one is left
                  int fc = 0; for (int s = 0; s < {NFSLOT}; s++) if (id(g_sn_fon)[s]) fc++;
                  id(g_sn_fclk)++;
                  int wait = (fc <= 1) ? {FRUIT_WAIT // 2} : {FRUIT_WAIT};
                  if (fc < {NFSLOT} && id(g_sn_fclk) >= wait) {{
                    id(g_sn_fclk) = 0;
                    int sl = -1; for (int s = 0; s < {NFSLOT}; s++) if (!id(g_sn_fon)[s]) {{ sl = s; break; }}
                    if (sl >= 0) {{
                      float a = (esp_random() % 62832) / 10000.0f; float rad = 25.0f + (esp_random() % 140);
                      id(g_sn_fx)[sl] = cosf(a)*rad; id(g_sn_fy)[sl] = sinf(a)*rad;
                      id(g_sn_fi)[sl] = esp_random() % {NFRUIT}; id(g_sn_fon)[sl] = true; id(g_sn_newfruit) = sl;
                    }}
                  }}
                  // skulls: up to {NSKULL}, each lives a while
                  int sc = 0; for (int s = 0; s < {NSKULL}; s++) if (id(g_sn_skon)[s]) sc++;
                  id(g_sn_skclk)++;
                  if (sc < {NSKULL} && id(g_sn_skclk) >= {SKULL_WAIT}) {{
                    id(g_sn_skclk) = 0;
                    int sl = -1; for (int s = 0; s < {NSKULL}; s++) if (!id(g_sn_skon)[s]) {{ sl = s; break; }}
                    if (sl >= 0) {{
                      float a = (esp_random() % 62832) / 10000.0f; float rad = 30.0f + (esp_random() % 130);
                      id(g_sn_skx)[sl] = cosf(a)*rad; id(g_sn_sky)[sl] = sinf(a)*rad;
                      id(g_sn_skon)[sl] = true; id(g_sn_skage)[sl] = 0;
                    }}
                  }}
                  for (int s = 0; s < {NSKULL}; s++) if (id(g_sn_skon)[s]) {{ id(g_sn_skage)[s]++; if (id(g_sn_skage)[s] >= {SKULL_LIFE}) id(g_sn_skon)[s] = false; }}
                }}
            - if:
                condition: {{ lambda: 'return id(g_sn_dead);' }}
                then:
                  - script.execute: sn_over
                else:
                  - if:
                      condition: {{ lambda: 'return id(g_sn_newfruit) >= 0;' }}
                      then:
{fspr_dispatch()}
                        - lambda: 'id(g_sn_newfruit) = -1;'
                  - script.execute: sn_hud    # every tick: score changes on eat, not only on spawn
                  - script.execute: sn_draw

image:
  - id: img_sn_logo
    # Hosted on the beta branch during development (flip to /main/ when snake is merged to main).
    file: "{BASE}snake-logo.png"
    type: RGB565
{fruit_images()}
  - id: img_sn_skull
    file: "{BASE}skull.png"
    type: RGB565
    transparency: alpha_channel

lvgl:
  pages:
    # --- SNAKE page (base id 9): free 360-degree snake, full round screen bounded by a ring ---
    - id: page_snake
      bg_color: {PAGE_BG}
      scrollbar_mode: "off"
      scrollable: false
      widgets:
        # boundary ring (full-screen circle just inside the round display)
        - obj: {{ id: sn_ring, align: CENTER, x: 0, y: 0, width: {RING_D}, height: {RING_D}, radius: {RING_D // 2}, bg_opa: TRANSP, border_width: 4, border_color: {RING}, hidden: true }}
        # fruit ({NFSLOT}) + skulls ({NSKULL}) + body segment pool ({POOL}). sn_s0 = head.
{fruit_widgets()}
{skull_widgets()}
{seg_widgets()}
        # HUD (snake passes under it)
        - label: {{ id: lbl_sn_score, align: CENTER, x: 0, y: -150, text: "0", text_font: font_med, text_color: {HUD}, hidden: true }}
        # --- MENU (state 0): full-screen logo + 3 stacked buttons ---
        - image: {{ id: sn_logo, align: CENTER, x: 0, y: 0, src: img_sn_logo, hidden: true }}
        - button:
            id: btn_sn_start
            align: CENTER
            y: 4
            width: 150
            height: 44
            radius: 22
            bg_color: {ACCENT}
            bg_opa: COVER
            border_width: 0
            on_click: [ script.execute: sn_start ]
            widgets:
              - label: {{ align: CENTER, text: "Start", text_font: font_med, text_color: {ACCENT_TXT} }}
        - button:
            id: btn_sn_howto
            align: CENTER
            y: 54
            width: 150
            height: 44
            radius: 22
            bg_color: {BTN2}
            bg_opa: COVER
            border_width: 0
            on_click: [ lambda: 'id(g_sn_state) = 3;', script.execute: sn_screen ]
            widgets:
              - label: {{ align: CENTER, text: "How to play?", text_font: font_med, text_color: {BTN2_TXT} }}
        - button:
            id: btn_sn_scores
            align: CENTER
            y: 104
            width: 150
            height: 44
            radius: 22
            bg_color: {BTN2}
            bg_opa: COVER
            border_width: 0
            on_click: [ lambda: 'id(g_sn_state) = 4;', script.execute: sn_screen ]
            widgets:
              - label: {{ align: CENTER, text: "Scores", text_font: font_med, text_color: {BTN2_TXT} }}
        # --- GAME OVER (state 2): dark text over the logo ---
        - label: {{ id: lbl_sn_over, align: CENTER, x: 0, y: -10, text_align: CENTER, text: "", text_font: font_sel, text_color: {WORDMARK}, hidden: true }}
        - label: {{ id: lbl_sn_rec, align: CENTER, x: 0, y: 22, text_align: CENTER, text: "", text_font: font_artist, text_color: {WORDMARK}, hidden: true }}
        - button:
            id: btn_sn_replay
            align: CENTER
            x: -66
            y: 62
            width: 112
            height: 48
            radius: 24
            bg_color: {ACCENT}
            bg_opa: COVER
            border_width: 0
            hidden: true
            on_click: [ script.execute: sn_start ]
            widgets:
              - label: {{ align: CENTER, text: "Play", text_font: font_med, text_color: {ACCENT_TXT} }}
        - button:
            id: btn_sn_exit
            align: CENTER
            x: 66
            y: 62
            width: 112
            height: 48
            radius: 24
            bg_color: {GRAY}
            bg_opa: COVER
            border_width: 0
            hidden: true
            on_click: [ lambda: 'id(g_sn_state) = 0;', script.execute: sn_screen ]
            widgets:
              - label: {{ align: CENTER, text: "Exit", text_font: font_med, text_color: 0xFFFFFF }}
        # --- HOW TO PLAY (state 3): numbered badges + labels ---
        - label: {{ id: lbl_sn_howto_t, align: CENTER, y: -104, text: "HOW TO PLAY?", text_font: font_sel, text_color: {ACCENT}, hidden: true }}
        - obj: {{ id: sn_b1, align: CENTER, x: -96, y: -52, width: 24, height: 24, radius: 12, bg_color: {BADGE}, bg_opa: COVER, border_width: 0, pad_all: 0, hidden: true, widgets: [ label: {{ align: CENTER, text: "1", text_font: font_artist, text_color: 0xFFFFFF }} ] }}
        - obj: {{ id: sn_b2, align: CENTER, x: -96, y: -16, width: 24, height: 24, radius: 12, bg_color: {BADGE}, bg_opa: COVER, border_width: 0, pad_all: 0, hidden: true, widgets: [ label: {{ align: CENTER, text: "2", text_font: font_artist, text_color: 0xFFFFFF }} ] }}
        - obj: {{ id: sn_b3, align: CENTER, x: -96, y: 20, width: 24, height: 24, radius: 12, bg_color: {BADGE}, bg_opa: COVER, border_width: 0, pad_all: 0, hidden: true, widgets: [ label: {{ align: CENTER, text: "3", text_font: font_artist, text_color: 0xFFFFFF }} ] }}
        - obj: {{ id: sn_b4, align: CENTER, x: -96, y: 56, width: 24, height: 24, radius: 12, bg_color: 0xE05A4A, bg_opa: COVER, border_width: 0, pad_all: 0, hidden: true, widgets: [ label: {{ align: CENTER, text: "!", text_font: font_artist, text_color: 0xFFFFFF }} ] }}
        - label: {{ id: lbl_sn_howto1, align_to: {{ id: sn_b1, align: OUT_RIGHT_MID, x: 8 }}, text: "Turn knob to steer", text_font: font_med, text_color: {TXT}, hidden: true }}
        - label: {{ id: lbl_sn_howto2, align_to: {{ id: sn_b2, align: OUT_RIGHT_MID, x: 8 }}, text: "Eat fruit to grow", text_font: font_med, text_color: {TXT}, hidden: true }}
        - label: {{ id: lbl_sn_howto3, align_to: {{ id: sn_b3, align: OUT_RIGHT_MID, x: 8 }}, text: "Avoid the ring & tail", text_font: font_med, text_color: {TXT}, hidden: true }}
        - label: {{ id: lbl_sn_howto4, align_to: {{ id: sn_b4, align: OUT_RIGHT_MID, x: 8 }}, text: "Skulls kill - avoid!", text_font: font_med, text_color: {TXT}, hidden: true }}
        # --- SCORES (state 4): top 10 in two columns ---
        - label: {{ id: lbl_sn_scores_t, align: CENTER, y: -116, text: "SCORES", text_font: font_sel, text_color: {ACCENT}, hidden: true }}
        - label: {{ id: lbl_sn_scores1, align: CENTER, x: -52, y: 0, text: "", text_align: LEFT, text_font: font_artist, text_color: {TXT}, hidden: true }}
        - label: {{ id: lbl_sn_scores2, align: CENTER, x: 56, y: 0, text: "", text_align: LEFT, text_font: font_artist, text_color: {TXT}, hidden: true }}
        # --- Back (state 3/4 -> menu) ---
        - button:
            id: btn_sn_back
            align: CENTER
            y: 120
            width: 130
            height: 42
            radius: 21
            bg_color: {GRAY}
            bg_opa: COVER
            border_width: 0
            hidden: true
            on_click: [ lambda: 'id(g_sn_state) = 0;', script.execute: sn_screen ]
            widgets:
              - label: {{ align: CENTER, text: "Back", text_font: font_med, text_color: 0xFFFFFF }}
"""

here = os.path.dirname(os.path.abspath(__file__))
out = os.path.join(here, "..", "base", "screens", "snake.yaml")
out = os.path.normpath(out)
with open(out, "w", encoding="utf-8", newline="\n") as f:
    f.write(YAML)
print("wrote", out, "(", len(YAML), "bytes )")
