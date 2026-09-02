#!/usr/bin/env python3
"""interiors_verify.py — D-009 checkpoint checks for interiors.html.

Own verification script for this task, per the file scope. Loads
interiors.html from file:// with Playwright (Chromium), exactly as a student
would open it — no server, no build step. Run from the repo root:

    ./.venv/bin/python docs/design-explorations/interiors_verify.py --all
    ./.venv/bin/python docs/design-explorations/interiors_verify.py --section options

Requires PLAYWRIGHT_BROWSERS_PATH set to wherever the Chromium build already
installed for this machine lives (see the task dispatch for the exact path);
this script does not install a browser itself.

Each section is a real measurement, not a label check:
  - options            C1: >= 2 [data-option] roots, exactly one
                        [data-recommended="true"].
  - kinds               C2: every option's [data-kind] set is exactly the
                        seven canonical kinds; no more, no fewer.
  - states              C3: for every (option, kind) pair, the collapsed and
                        opened exemplars' rendered heights are measured, and
                        opened must be strictly taller.
  - selection-dual      C4: every option's Selection interior holds labelled
                        guided controls AND exactly one free-text expression
                        field, both reachable by Tab, neither disabled nor
                        inside an aria-hidden subtree.
"""

import argparse
import pathlib
import sys

from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
PAGE_URL = (HERE / "interiors.html").as_uri()

CANONICAL_KINDS = sorted(
    [
        "Multiplicity",
        "Selection",
        "ObsGlobal",
        "ObsObject",
        "ObsVectorSum",
        "ObsCustom",
        "Histogram",
    ]
)


def fail(msg):
    print(f"FAIL: {msg}")
    sys.exit(1)


def check_options(page):
    options = page.locator("[data-option]")
    n = options.count()
    print(f"[data-option] roots found: {n}")
    if n < 2:
        fail(f"expected >= 2 [data-option] roots, found {n}")

    recommended = page.locator('[data-option][data-recommended="true"]')
    n_rec = recommended.count()
    print(f'[data-recommended="true"] roots found: {n_rec}')
    if n_rec != 1:
        fail(f"expected exactly 1 [data-recommended=true] root, found {n_rec}")

    print("PASS: options")


def check_kinds(page):
    option_ids = page.locator("[data-option]").evaluate_all(
        "els => els.map(e => e.getAttribute('data-option'))"
    )
    all_ok = True
    for opt in option_ids:
        kinds = page.locator(f'[data-option="{opt}"] [data-kind]').evaluate_all(
            "els => els.map(e => e.getAttribute('data-kind'))"
        )
        found = sorted(set(kinds))
        print(f"option={opt}: kinds found = {found}")
        if found != CANONICAL_KINDS:
            all_ok = False
            print(f"  MISMATCH: expected {CANONICAL_KINDS}")
        if len(kinds) != len(CANONICAL_KINDS):
            all_ok = False
            print(f"  MISMATCH: expected exactly {len(CANONICAL_KINDS)} [data-kind] elements, found {len(kinds)}")
    if not all_ok:
        fail("kind set mismatch — see MISMATCH lines above")
    print("PASS: kinds")


def check_states(page):
    option_ids = page.locator("[data-option]").evaluate_all(
        "els => els.map(e => e.getAttribute('data-option'))"
    )
    rows = 0
    all_ok = True
    for opt in option_ids:
        for kind in CANONICAL_KINDS:
            scope = f'[data-option="{opt}"] .kind-demo[data-kind="{kind}"]'
            collapsed = page.locator(f'{scope} .exemplar[data-state="collapsed"]')
            opened = page.locator(f'{scope} .exemplar[data-state="opened"]')
            if collapsed.count() != 1 or opened.count() != 1:
                fail(
                    f"option={opt} kind={kind}: expected exactly one collapsed "
                    f"and one opened exemplar, found {collapsed.count()}/{opened.count()}"
                )
            c_box = collapsed.bounding_box()
            o_box = opened.bounding_box()
            c_h = c_box["height"] if c_box else 0
            o_h = o_box["height"] if o_box else 0
            rows += 1
            ok = o_h > c_h and c_h > 0 and o_h > 0
            print(
                f"option={opt} kind={kind}: collapsed={c_h:.1f}px "
                f"opened={o_h:.1f}px opened>collapsed={ok}"
            )
            if not ok:
                all_ok = False
                if c_h <= 0:
                    print(f"  MISMATCH: collapsed exemplar renders at zero height (option={opt} kind={kind})")
                if o_h <= 0:
                    print(f"  MISMATCH: opened exemplar renders at zero height (option={opt} kind={kind})")
    print(f"rows measured: {rows}")
    if not all_ok:
        fail("at least one (option, kind) pair did not have opened > collapsed > 0")
    print("PASS: states")


def _tab_order(page):
    """Return the page's focusable elements, in the order Tab reaches them, as
    a list of element ids, by walking with real Tab presses from a stable
    start (document body) rather than trusting DOM order alone — this is what
    a keyboard user actually experiences. Real Tab presses land only on
    elements the browser itself treats as focusable, so anything disabled,
    aria-hidden, or removed from the tab order (e.g. tabindex="-1") is
    excluded from the walk — which is exactly why such a control's
    tab_index_of() lookup below comes back None. An element with no id is
    given a temporary one so it can still be matched positionally; every
    control this check actually cares about (the guided fields, the raw
    expression field) already has a real id."""
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


def check_selection_dual(page):
    option_ids = page.locator("[data-option]").evaluate_all(
        "els => els.map(e => e.getAttribute('data-option'))"
    )
    tab_order = _tab_order(page)

    def tab_index_of(locator):
        ctrl_id = locator.get_attribute("id")
        if not ctrl_id:
            return None
        try:
            return tab_order.index(ctrl_id) + 1
        except ValueError:
            return None

    all_ok = True
    for opt in option_ids:
        scope = f'[data-option="{opt}"] .kind-demo[data-kind="Selection"] .exemplar[data-state="opened"]'
        opened = page.locator(scope)
        if opened.count() != 1:
            fail(f"option={opt}: expected exactly one opened Selection exemplar, found {opened.count()}")

        guided_inputs = page.locator(f'{scope} .io-guided input, {scope} .io-guided select')
        n_guided = guided_inputs.count()
        labelled = 0
        guided_indices = []
        for i in range(n_guided):
            ctrl = guided_inputs.nth(i)
            ctrl_id = ctrl.get_attribute("id")
            has_label = bool(ctrl_id) and page.locator(f'label[for="{ctrl_id}"]').count() == 1
            if has_label:
                labelled += 1
            idx = tab_index_of(ctrl)
            guided_indices.append(idx)
            aria_hidden = ctrl.evaluate(
                "el => { let n = el; while (n) { if (n.getAttribute && "
                "n.getAttribute('aria-hidden') === 'true') return true; n = n.parentElement; } "
                "return false; }"
            )
            disabled = ctrl.evaluate("el => el.disabled === true")
            print(
                f"option={opt} guided[{i}] id={ctrl_id} labelled={has_label} "
                f"tab_index={idx} aria_hidden={aria_hidden} disabled={disabled}"
            )
            if aria_hidden or disabled:
                all_ok = False
            if idx is None:
                all_ok = False
                print(f"  MISMATCH: guided[{i}] id={ctrl_id} is unreachable by Tab (tab_index=None)")

        print(f"option={opt}: labelled guided controls = {labelled} (of {n_guided} total)")
        if n_guided != 4:
            all_ok = False
            print(f"  MISMATCH: expected exactly 4 guided controls, found {n_guided}")
        if labelled != n_guided:
            all_ok = False
            print(f"  MISMATCH: expected all {n_guided} guided controls labelled, found {labelled}")

        raw_fields = page.locator(f"{scope} .io-raw .io-raw__input")
        n_raw = raw_fields.count()
        print(f"option={opt}: free-text expression fields = {n_raw}")
        if n_raw != 1:
            all_ok = False
            print(f"  MISMATCH: expected exactly 1 free-text expression field, found {n_raw}")
        else:
            raw = raw_fields.first
            raw_id = raw.get_attribute("id")
            raw_has_label = bool(raw_id) and page.locator(f'label[for="{raw_id}"]').count() == 1
            idx = tab_index_of(raw)
            aria_hidden = raw.evaluate(
                "el => { let n = el; while (n) { if (n.getAttribute && "
                "n.getAttribute('aria-hidden') === 'true') return true; n = n.parentElement; } "
                "return false; }"
            )
            disabled = raw.evaluate("el => el.disabled === true")
            print(
                f"option={opt} raw id={raw_id} labelled={raw_has_label} "
                f"tab_index={idx} aria_hidden={aria_hidden} disabled={disabled}"
            )
            if aria_hidden or disabled:
                all_ok = False
            if idx is None:
                all_ok = False
                print(f"  MISMATCH: raw field id={raw_id} is unreachable by Tab (tab_index=None)")

    if not all_ok:
        fail("selection-dual check failed — see MISMATCH / aria_hidden / disabled lines above")
    print("PASS: selection-dual")


SECTIONS = {
    "options": check_options,
    "kinds": check_kinds,
    "states": check_states,
    "selection-dual": check_selection_dual,
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
