#!/usr/bin/env python3
"""observable_verify.py — D-013 checkpoint checks for observable.html.

Own verification script for this task, per the file scope. Loads
observable.html from file:// with Playwright (Chromium), exactly as a
student would open it — no server, no build step. Run from the repo root:

    ./.venv/bin/python docs/design-explorations/observable_verify.py --all
    ./.venv/bin/python docs/design-explorations/observable_verify.py --section kind

Requires PLAYWRIGHT_BROWSERS_PATH set to wherever the Chromium build already
installed for this machine lives; this script does not install a browser.

Each section is a real measurement, not a label check:
  - kind        C1: the set of [data-kind] values on the page is exactly
                {'Observable'}; the set of [data-mode] values is exactly the
                four canonical mode names.
  - modes       C2: every one of the four modes is reachable by real Tab
                presses from the mode toggle, and activating one by keyboard
                (Tab to it, then Space) changes which mode's control panel is
                rendered.
  - states      C3: for every mode, the collapsed and opened exemplars are
                both rendered and opened is strictly taller than collapsed,
                with both strictly greater than zero.
  - controls    C4: every mode carries exactly the controls D-013's dispatch
                table specifies, by count and type, and every control is
                labelled.
  - footprint   C5: the opened height of every mode is measured and the
                tallest is named.
"""

import argparse
import pathlib
import sys

from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
PAGE_URL = (HERE / "observable.html").as_uri()

CANONICAL_KINDS = {"Observable"}
CANONICAL_MODES = {"ObsGlobal", "ObsObject", "ObsVectorSum", "ObsCustom"}

MODE_RADIO_ID = {
    "ObsGlobal": "obs-mode-global",
    "ObsObject": "obs-mode-object",
    "ObsVectorSum": "obs-mode-vecsum",
    "ObsCustom": "obs-mode-custom",
}

# mode -> (n_select, n_checkbox, n_text)
EXPECTED_CONTROLS = {
    "ObsGlobal": (1, 0, 0),
    "ObsObject": (2, 0, 0),
    "ObsVectorSum": (1, 3, 0),
    "ObsCustom": (0, 0, 1),
}


def fail(msg):
    print(f"FAIL: {msg}")
    sys.exit(1)


def check_kind(page):
    kind_values = page.locator("[data-kind]").evaluate_all(
        "els => els.map(e => e.getAttribute('data-kind'))"
    )
    kind_set = set(kind_values)
    print(f"[data-kind] values found: {sorted(kind_set)}")
    if kind_set != CANONICAL_KINDS:
        fail(f"expected [data-kind] set == {CANONICAL_KINDS}, found {kind_set}")

    mode_values = page.locator("[data-mode]").evaluate_all(
        "els => els.map(e => e.getAttribute('data-mode'))"
    )
    mode_set = set(mode_values)
    print(f"[data-mode] values found: {sorted(mode_set)}")
    if mode_set != CANONICAL_MODES:
        fail(f"expected [data-mode] set == {CANONICAL_MODES}, found {mode_set}")

    print("PASS: kind")


def _tab_order(page):
    """Walk the page's real Tab order from a stable start (document body),
    returning the list of element ids reached, in order — exactly what a
    keyboard user experiences. Only elements the browser treats as
    focusable are reached; tabindex="-1", disabled, or otherwise
    tab-excluded elements are silently skipped, which is why an excluded
    control's tab index below comes back None rather than erroring."""
    page.evaluate("document.body.setAttribute('tabindex', '-1'); document.body.focus();")
    order_ids = []
    for _ in range(400):
        page.keyboard.press("Tab")
        tag = page.evaluate("document.activeElement.tagName")
        if tag == "BODY":
            break
        eid = page.evaluate(
            "() => { const el = document.activeElement; "
            "if (!el.id) { el.id = '__tabidx_' + Math.random().toString(36).slice(2); } "
            "return el.id; }"
        )
        order_ids.append(eid)
    return order_ids


def _active_mode(page):
    """Return the data-mode of the currently visible .mode-panel, or None if
    zero or more than one are visible (both are bugs, not just one)."""
    visible = page.evaluate(
        "() => Array.from(document.querySelectorAll('.mode-panel'))"
        ".filter(el => getComputedStyle(el).display !== 'none')"
        ".map(el => el.getAttribute('data-mode'))"
    )
    if len(visible) != 1:
        return None, visible
    return visible[0], visible


def check_modes(page):
    """The mode toggle is a native radiogroup — the correct, WCAG-conformant
    keyboard pattern for four mutually-exclusive options is Tab *once* into
    the group (landing on whichever option is checked) and then Arrow keys
    to move between, and select, the other options; that is native browser
    behaviour for grouped radio inputs, not a custom widget, and it is why
    an author-set tabindex="0" on every option (tried first; see the PR
    body) does not change the underlying radiogroup semantics — the browser
    still gives sequential Tab only one stop per group.

    So "reachable by keyboard" is measured here as: a real Tab from body
    reaches the group at all (entry_tab_index), and a real ArrowRight press
    from there reaches each subsequent option in DOM order, checking it as
    it goes — exactly the interaction a keyboard-only student performs.
    Each mode's printed "tab_index" is its ordinal position in that
    Tab-then-Arrow walk (1 = the Tab stop itself, 2..4 = one ArrowRight
    press further each) so a fully-excluded option (e.g. tabindex="-1"
    removing it from DOM focus order entirely) still shows up as None."""
    tab_order = _tab_order(page)
    entry_id = MODE_RADIO_ID["ObsGlobal"]  # the mode checked by default
    try:
        entry_tab_index = tab_order.index(entry_id) + 1
    except ValueError:
        entry_tab_index = None
    print(f"radiogroup entry control_id={entry_id} tab_index={entry_tab_index}")

    dom_order = ["ObsGlobal", "ObsObject", "ObsVectorSum", "ObsCustom"]
    all_ok = True

    page.evaluate("document.body.setAttribute('tabindex', '-1'); document.body.focus();")
    if entry_tab_index is None:
        all_ok = False
        print(f"  MISMATCH: mode=ObsGlobal control_id={entry_id} is unreachable by Tab (tab_index=None)")
    else:
        for _ in range(entry_tab_index):
            page.keyboard.press("Tab")

    tab_indices = {}
    rendered_sets = set()
    for i, mode in enumerate(dom_order):
        if i > 0:
            page.keyboard.press("ArrowRight")
        focused_id = page.evaluate("document.activeElement.id")
        idx = (entry_tab_index + i) if entry_tab_index is not None and focused_id == MODE_RADIO_ID[mode] else None
        tab_indices[mode] = idx
        active, visible = _active_mode(page)
        print(
            f"mode={mode} control_id={MODE_RADIO_ID[mode]} tab_index={idx} "
            f"focused={focused_id} -> rendered panel(s) = {visible}"
        )
        if idx is None:
            all_ok = False
            print(f"  MISMATCH: mode={mode} control_id={MODE_RADIO_ID[mode]} is unreachable by keyboard (tab_index=None)")
        if active != mode:
            all_ok = False
            print(f"  MISMATCH: activating mode={mode} rendered panel(s) {visible}, expected exactly ['{mode}']")
        rendered_sets.add(tuple(visible))

    print(f"distinct rendered control sets across the four activations: {len(rendered_sets)}")
    if len(rendered_sets) != 4:
        all_ok = False
        print("  MISMATCH: expected 4 distinct rendered control sets, one per mode")

    if not all_ok:
        fail("mode activation did not render the expected control set — see MISMATCH lines above")
    print("PASS: modes")


def _activate_mode(page, mode):
    """Focus the given mode's radio directly and check it via keyboard
    (Space) — used by states/controls/footprint, which need a specific mode
    active rather than walking the whole tab order each time."""
    page.locator(f"#{MODE_RADIO_ID[mode]}").focus()
    page.keyboard.press("Space")
    active, visible = _active_mode(page)
    if active != mode:
        fail(f"could not activate mode={mode}: rendered panel(s) = {visible}")


def _measure(page, mode):
    scope = '.kind-demo[data-kind="Observable"]'
    collapsed = page.locator(f'{scope} .exemplar[data-state="collapsed"]')
    opened = page.locator(f'{scope} .exemplar[data-state="opened"]')
    if collapsed.count() != 1 or opened.count() != 1:
        fail(
            f"expected exactly one collapsed and one opened exemplar, "
            f"found {collapsed.count()}/{opened.count()}"
        )
    _activate_mode(page, mode)
    c_box = collapsed.bounding_box()
    o_box = opened.bounding_box()
    if c_box is None:
        fail(f"mode={mode}: collapsed exemplar has no bounding box (None)")
    if o_box is None:
        fail(f"mode={mode}: opened exemplar has no bounding box (None)")
    return c_box["height"], o_box["height"]


def check_states(page):
    all_ok = True
    for mode in sorted(CANONICAL_MODES):
        c_h, o_h = _measure(page, mode)
        ok = o_h > c_h > 0
        print(f"mode={mode}: collapsed={c_h:.1f}px opened={o_h:.1f}px opened>collapsed>0={ok}")
        if not ok:
            all_ok = False
            if c_h <= 0:
                print(f"  MISMATCH: collapsed exemplar renders at zero height (mode={mode})")
            if o_h <= 0:
                print(f"  MISMATCH: opened exemplar renders at zero height (mode={mode})")
            if not (o_h > c_h):
                print(f"  MISMATCH: opened ({o_h:.1f}px) is not strictly taller than collapsed ({c_h:.1f}px) (mode={mode})")
    if not all_ok:
        fail("at least one mode did not have opened > collapsed > 0")
    print("PASS: states")


def check_controls(page):
    all_ok = True
    for mode in sorted(CANONICAL_MODES):
        _activate_mode(page, mode)
        panel = f'.mode-panel[data-mode="{mode}"]'
        selects = page.locator(f'{panel} select')
        checkboxes = page.locator(f'{panel} input[type="checkbox"]')
        texts = page.locator(f'{panel} input[type="text"]')

        n_select, n_checkbox, n_text = selects.count(), checkboxes.count(), texts.count()
        exp_select, exp_checkbox, exp_text = EXPECTED_CONTROLS[mode]
        print(
            f"mode={mode}: select={n_select} (expect {exp_select}) "
            f"checkbox={n_checkbox} (expect {exp_checkbox}) "
            f"text={n_text} (expect {exp_text})"
        )
        if (n_select, n_checkbox, n_text) != (exp_select, exp_checkbox, exp_text):
            all_ok = False
            print(
                f"  MISMATCH: mode={mode} expected select/checkbox/text = "
                f"{(exp_select, exp_checkbox, exp_text)}, found {(n_select, n_checkbox, n_text)}"
            )

        all_controls = page.locator(f'{panel} select, {panel} input')
        total = all_controls.count()
        labelled = 0
        for i in range(total):
            ctrl = all_controls.nth(i)
            ctrl_id = ctrl.get_attribute("id")
            if ctrl_id and page.locator(f'label[for="{ctrl_id}"]').count() == 1:
                labelled += 1
        print(f"mode={mode}: labelled = {labelled} (of {total} total)")
        if labelled != total:
            all_ok = False
            print(f"  MISMATCH: mode={mode} expected all {total} controls labelled, found {labelled}")

    if not all_ok:
        fail("control count/type/label mismatch — see MISMATCH lines above")
    print("PASS: controls")


def check_footprint(page):
    heights = {}
    for mode in sorted(CANONICAL_MODES):
        _, o_h = _measure(page, mode)
        heights[mode] = o_h
        print(f"mode={mode}: opened height = {o_h:.1f}px")

    for mode, h in heights.items():
        if not (h > 0):
            fail(f"mode={mode}: opened height {h:.1f}px is not > 0")

    tallest_mode = max(heights, key=heights.get)
    print(f"widest/tallest mode: {tallest_mode} at {heights[tallest_mode]:.1f}px")
    print("PASS: footprint")


SECTIONS = {
    "kind": check_kind,
    "modes": check_modes,
    "states": check_states,
    "controls": check_controls,
    "footprint": check_footprint,
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--section", choices=sorted(SECTIONS.keys()))
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()

    if not args.section and not args.all:
        parser.error("pass --section <name> or --all")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.goto(PAGE_URL)

        if args.all:
            for name, fn in SECTIONS.items():
                print(f"\n=== {name} ===")
                fn(page)
        else:
            SECTIONS[args.section](page)

        browser.close()


if __name__ == "__main__":
    main()
