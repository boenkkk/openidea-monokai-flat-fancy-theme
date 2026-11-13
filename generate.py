#!/usr/bin/env python3
"""Generates themes/<variant>.theme.json and themes/<variant>.scheme.json from palette.json.

palette.json is a trimmed copy of the Monokai Flat Fancy palette (MIT, © Budi
Santoso) plus the few UI greys it is built from. Every one of the 252 OpenIDEA
themeable tokens is derived from those colours, so re-running this after a
palette change refreshes all three variants:

    python3 generate.py
    openidea-plugin check .

Not part of the package (plugin.toml does not reference it), so it is not installed.
"""

from __future__ import annotations

import json
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
VARIANTS = {
    "default": "Monokai Flat Fancy Default",
    "darker": "Monokai Flat Fancy Darker",
    "light": "Monokai Flat Fancy Light",
}

# Section order and token names of src/styles/tokens.css in OpenIDEA (the
# Islands Light block), split the way the IDE splits theme and editor scheme.
# generate.py asserts that it writes exactly these names, so a dropped or
# mistyped token cannot slip through.
UI_GROUPS = {
    "Surfaces": [
        "--bg-app", "--bg-elev", "--bg-popup", "--bg-floating-toolbar", "--bg-hover",
        "--bg-selected", "--bg-selected-strong", "--bg-current-line", "--bg-debug-line",
        "--bg-backdrop", "--bg-input",
    ],
    "Lines": ["--border", "--border-popup", "--border-strong", "--border-window", "--control-off"],
    "Text": [
        "--fg-strong", "--fg-emphasis", "--fg", "--fg-secondary", "--fg-muted", "--fg-subtle",
        "--fg-faint", "--fg-gutter", "--fg-icon",
    ],
    "Accent": ["--accent", "--link", "--link-hover"],
    "Charts": ["--chart-series"],
    "Status": ["--danger", "--warning", "--success", "--db-connected", "--db-connected-ring", "--info"],
    "Vcs": [
        "--vcs-modified", "--vcs-added", "--vcs-deleted", "--vcs-untracked", "--vcs-ignored",
        "--vcs-conflict", "--gutter-modified", "--gutter-added", "--gutter-deleted",
        "--diff-modified", "--diff-inserted", "--diff-deleted",
        "--diff-modified-stripe", "--diff-inserted-stripe", "--diff-deleted-stripe",
        "--diff-conflict-stripe",
    ],
    "Shadows and window controls": [
        "--shadow-popup", "--shadow-dialog", "--traffic-close", "--traffic-close-border",
        "--traffic-close-pressed", "--traffic-glyph", "--traffic-off", "--traffic-off-border",
    ],
    "Additive": [
        "--bg-stripe-tooltip", "--fg-stripe-tooltip", "--border-stripe-tooltip",
        "--shadow-stripe-tooltip", "--bg-tooltip", "--fg-tooltip", "--border-tooltip",
        "--bg-control", "--bg-control-hover", "--bg-active", "--bg-scrim", "--fg-on-accent",
        "--shadow-tooltip", "--shadow-balloon",
    ],
    "Islands contract": [
        "--bg-frame", "--bg-island", "--bg-stripe-hover", "--bg-stripe-selected",
        "--fg-stripe-selected-active", "--fg-stripe-label", "--bg-tab-selected",
        "--border-tab-selected", "--bg-tab-selected-inactive", "--border-tab-selected-inactive",
        "--bg-tab-hover", "--border-editor-tabs", "--bg-tree-selected",
        "--bg-tree-selected-inactive", "--bg-tree-hover", "--bg-toolbar-hover",
        "--bg-toolbar-pressed", "--bg-toolbar-selected", "--bg-toolbar-selected-hover",
        "--bg-button-primary-hover", "--fg-button-primary", "--bg-button", "--border-button",
        "--bg-field", "--bg-checkbox", "--border-checkbox", "--bg-toggle-on", "--fg-toggle-on",
        "--bg-toggle-off", "--fg-toggle-off", "--border-toggle", "--bg-toggle-knob",
        "--focus-ring-soft", "--scrollbar-thumb", "--scrollbar-thumb-hover",
        "--bg-search-match", "--bg-search-match-current", "--fg-search-match", "--bg-dialog",
        "--bg-popup-inline", "--bg-popup-advertiser", "--bg-feedback-info",
        "--border-feedback-info", "--bg-feedback-error", "--border-feedback-error",
        "--bg-feedback-warning", "--border-feedback-warning", "--bg-feedback-success",
        "--border-feedback-success", "--bg-counter", "--fg-counter", "--bg-progress-track",
    ],
}

SCHEME_GROUPS = {
    "Syntax": [
        "--syn-keyword", "--syn-string", "--syn-type", "--syn-function",
        "--syn-function-call", "--syn-comment", "--syn-comment-style", "--syn-doc-comment",
        "--syn-doc-comment-tag", "--syn-doc-comment-tag-effect", "--syn-doc-comment-tag-value",
        "--syn-doc-markup", "--syn-doc-markup-bg", "--syn-docstring", "--syn-annotation",
        "--syn-decorator", "--syn-number", "--syn-punct", "--syn-variable", "--syn-global",
        "--syn-namespace", "--syn-param", "--syn-property", "--syn-constant",
        "--syn-python-local-variable", "--syn-python-global-variable",
        "--syn-python-instance-attribute", "--syn-python-class-attribute",
        "--syn-python-constant", "--syn-python-property", "--syn-python-type-parameter",
        "--syn-python-builtin", "--syn-python-predefined-definition",
        "--syn-python-predefined-usage", "--syn-python-fstring", "--syn-python-bytes",
        "--syn-php-variable", "--syn-php-function-call", "--syn-builtin", "--syn-self",
        "--syn-keyword-arg", "--syn-predefined", "--syn-escape", "--syn-regexp", "--syn-tag",
        "--syn-attribute", "--syn-todo", "--syn-link", "--syn-markup-heading",
        "--syn-markup-code", "--syn-invalid", "--syn-inline-value", "--syn-rainbow-1",
        "--syn-rainbow-2", "--syn-rainbow-3", "--syn-rainbow-4", "--syn-rainbow-5",
        "--syn-bracket-1", "--syn-bracket-2", "--syn-bracket-3",
    ],
    "Editor": [
        "--fg-editor", "--caret", "--fg-line-number", "--fg-line-number-current",
        "--border-gutter", "--border-indent-guide", "--border-indent-guide-active",
        "--border-right-margin", "--bg-editor-selection", "--bg-editor-selection-inactive",
        "--bg-text-search-result", "--bg-text-search-result-current", "--bg-matched-brace",
        "--matched-brace-weight", "--bg-matched-tag", "--bg-fold-placeholder",
        "--fg-fold-placeholder", "--fg-fold-marker", "--fg-whitespace", "--fg-unused",
        "--bg-identifier-under-caret", "--bg-identifier-under-caret-write", "--fg-inlay",
        "--bg-inlay", "--wave-error", "--wave-warning", "--editor-error-decoration",
        "--editor-warning-decoration", "--editor-warning-background", "--bg-breakpoint-line",
        "--fg-completion-match", "--bg-editor-inline", "--bg-editor-banner",
        "--fg-weak-warning", "--fg-bulb",
    ],
    "ANSI palette": [
        "--ansi-black", "--ansi-red", "--ansi-green", "--ansi-yellow", "--ansi-blue",
        "--ansi-magenta", "--ansi-cyan", "--ansi-white", "--ansi-bright-black",
        "--ansi-bright-red", "--ansi-bright-green", "--ansi-bright-yellow",
        "--ansi-bright-blue", "--ansi-bright-magenta", "--ansi-bright-cyan",
        "--ansi-bright-white",
    ],
    "Terminal ANSI palette": [
        "--terminal-ansi-black", "--terminal-ansi-red", "--terminal-ansi-green",
        "--terminal-ansi-yellow", "--terminal-ansi-blue", "--terminal-ansi-magenta",
        "--terminal-ansi-cyan", "--terminal-ansi-white", "--terminal-ansi-bright-black",
        "--terminal-ansi-bright-red", "--terminal-ansi-bright-green",
        "--terminal-ansi-bright-yellow", "--terminal-ansi-bright-blue",
        "--terminal-ansi-bright-magenta", "--terminal-ansi-bright-cyan",
        "--terminal-ansi-bright-white",
    ],
}

ANSI_ORDER = [
    "black", "red", "green", "yellow", "blue", "magenta", "cyan", "white",
    "bright-black", "bright-red", "bright-green", "bright-yellow",
    "bright-blue", "bright-magenta", "bright-cyan", "bright-white",
]


def rgb(h: str) -> tuple[int, int, int]:
    return int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)


def hexc(c: tuple[float, float, float]) -> str:
    return "#%02x%02x%02x" % tuple(round(max(0, min(255, v))) for v in c)


def mix(a: str, b: str, t: float) -> str:
    """`t` of b over a."""
    return hexc(tuple(x * (1 - t) + y * t for x, y in zip(rgb(a), rgb(b))))


def alpha(c: str, a: float) -> str:
    return c + "%02x" % round(a * 255)


def ui_tokens(p: dict[str, str], dark: bool) -> dict[str, str]:
    """Values of the 125 UI tokens, in the order of UI_GROUPS."""
    app, text = p["app"], p["text"]
    # Selections stay in the theme's warm neutral family (VS Code's own
    # selection is #75715e); the accent is reserved for controls and syntax.
    selected = mix(app, p["active"], 0.7)
    selected_strong = mix(app, p["active"], 0.85)
    black = "0, 0, 0"
    shadow = (0.45, 0.35, 0.45, 0.4, 0.45) if dark else (0.18, 0.14, 0.18, 0.16, 0.18)
    dialog_edge = 0.6 if dark else 0.25
    return {
        # Surfaces
        "--bg-app": app,
        "--bg-elev": p["elev"],
        "--bg-popup": p["popup"],
        "--bg-floating-toolbar": p["control"],
        "--bg-hover": p["surface"],
        "--bg-selected": selected,
        "--bg-selected-strong": selected_strong,
        "--bg-current-line": p["current_line"],
        "--bg-debug-line": mix(app, p["cyan"], 0.3),
        "--bg-backdrop": p["frame"],
        "--bg-input": p["control"],
        # Lines
        "--border": p["line"],
        "--border-popup": p["line_strong"],
        "--border-strong": p["line_strong"],
        "--border-window": p["line"],
        "--control-off": p["active"],
        # Text
        "--fg-strong": p["text_strong"],
        "--fg-emphasis": text,
        "--fg": text,
        "--fg-secondary": p["text_secondary"],
        "--fg-muted": p["text_muted"],
        "--fg-subtle": p["text_subtle"],
        "--fg-faint": p["text_faint"],
        "--fg-gutter": p["text_gutter"],
        "--fg-icon": p["text_secondary"],
        # Accent
        "--accent": p["accent"],
        "--link": p["link"],
        "--link-hover": p["link_hover"],
        # Charts
        "--chart-series": p["pink"],
        # Status
        "--danger": p["red"],
        "--warning": p["orange"],
        "--success": p["green"],
        "--db-connected": p["green"],
        "--db-connected-ring": mix(app, p["green"], 0.5),
        "--info": p["cyan"],
        # Vcs
        "--vcs-modified": p["accent"],
        "--vcs-added": p["green"],
        "--vcs-deleted": p["text_subtle"],
        "--vcs-untracked": p["purple"],
        "--vcs-ignored": p["comment"],
        "--vcs-conflict": p["pink"],
        "--gutter-modified": p["accent"],
        "--gutter-added": p["green"],
        "--gutter-deleted": p["pink"],
        "--diff-modified": mix(app, p["accent"], 0.2),
        "--diff-inserted": mix(app, p["green"], 0.2),
        "--diff-deleted": mix(app, p["pink"], 0.2),
        "--diff-modified-stripe": mix(app, p["accent"], 0.45),
        "--diff-inserted-stripe": mix(app, p["green"], 0.45),
        "--diff-deleted-stripe": mix(app, p["pink"], 0.45),
        "--diff-conflict-stripe": mix(app, p["orange"], 0.45),
        # Shadows and window controls
        "--shadow-popup": f"0 6px 20px rgba({black}, {shadow[0]})",
        "--shadow-dialog": (
            f"0 0 0 0.5px rgba({black}, {dialog_edge}), "
            f"0 10px 24px rgba({black}, {shadow[1]}), "
            f"0 24px 72px rgba({black}, {shadow[2]})"
        ),
        "--traffic-close": "#ff5f57",
        "--traffic-close-border": "#e0443e",
        "--traffic-close-pressed": "#bf4942",
        "--traffic-glyph": "#4d0000",
        "--traffic-off": p["active"],
        "--traffic-off-border": p["line"],
        # Additive
        "--bg-stripe-tooltip": "var(--bg-tooltip)",
        "--fg-stripe-tooltip": "var(--fg-tooltip)",
        "--border-stripe-tooltip": "var(--border-tooltip)",
        "--shadow-stripe-tooltip": "var(--shadow-tooltip)",
        "--bg-tooltip": p["control"],
        "--fg-tooltip": text,
        "--border-tooltip": p["line_strong"],
        "--bg-control": p["control"],
        "--bg-control-hover": mix(p["control"], text, 0.08),
        "--bg-active": p["active"],
        "--bg-scrim": alpha(p["frame"], 0.55),
        "--fg-on-accent": p["on_accent"],
        "--shadow-tooltip": f"0 4px 12px rgba({black}, {shadow[3]})",
        "--shadow-balloon": f"0 8px 24px rgba({black}, {shadow[4]})",
        # Islands contract
        "--bg-frame": p["frame"],
        "--bg-island": app,
        "--bg-stripe-hover": alpha(text, 0.09),
        "--bg-stripe-selected": alpha(text, 0.16),
        "--fg-stripe-selected-active": p["text_strong"],
        "--fg-stripe-label": p["text_muted"],
        "--bg-tab-selected": p["tab_selected"],
        "--border-tab-selected": text,
        "--bg-tab-selected-inactive": p["elev"],
        "--border-tab-selected-inactive": p["active"],
        "--bg-tab-hover": alpha(text, 0.08),
        "--border-editor-tabs": p["line"],
        "--bg-tree-selected": selected,
        "--bg-tree-selected-inactive": p["surface"],
        "--bg-tree-hover": alpha(text, 0.06),
        "--bg-toolbar-hover": alpha(text, 0.09),
        "--bg-toolbar-pressed": alpha(text, 0.16),
        "--bg-toolbar-selected": selected_strong,
        "--bg-toolbar-selected-hover": mix(app, p["active"], 0.95),
        "--bg-button-primary-hover": mix(p["accent"], text, 0.18),
        "--fg-button-primary": p["on_accent"],
        "--bg-button": "transparent",
        "--border-button": p["active"],
        "--bg-field": p["control"],
        "--bg-checkbox": p["control"],
        "--border-checkbox": p["text_subtle"],
        "--bg-toggle-on": p["green"],
        "--fg-toggle-on": p["on_accent"],
        "--bg-toggle-off": p["control"],
        "--fg-toggle-off": p["text_subtle"],
        "--border-toggle": p["text_subtle"],
        "--bg-toggle-knob": p["text_subtle"],
        "--focus-ring-soft": alpha(p["accent"], 0.6),
        "--scrollbar-thumb": alpha(text, 0.2),
        "--scrollbar-thumb-hover": alpha(text, 0.35),
        "--bg-search-match": mix(app, p["highlight"], 0.6),
        "--bg-search-match-current": p["highlight"],
        "--fg-search-match": app if dark else text,
        "--bg-dialog": app,
        "--bg-popup-inline": p["popup"],
        "--bg-popup-advertiser": p["popup"],
        "--bg-feedback-info": mix(app, p["cyan"], 0.18),
        "--border-feedback-info": mix(app, p["cyan"], 0.42),
        "--bg-feedback-error": mix(app, p["red"], 0.18),
        "--border-feedback-error": mix(app, p["red"], 0.42),
        "--bg-feedback-warning": mix(app, p["orange"], 0.18),
        "--border-feedback-warning": mix(app, p["orange"], 0.42),
        "--bg-feedback-success": mix(app, p["green"], 0.18),
        "--border-feedback-success": mix(app, p["green"], 0.42),
        "--bg-counter": p["text_subtle"],
        "--fg-counter": app if dark else "#ffffff",
        "--bg-progress-track": p["line"],
    }


def scheme_tokens(p: dict[str, str], dark: bool) -> dict[str, str]:
    """Values of the 127 editor scheme tokens, in the order of SCHEME_GROUPS."""
    app = p["app"]
    ansi = {f"--ansi-{n}": p["ansi"][n] for n in ANSI_ORDER}
    ansi |= {f"--terminal-ansi-{n}": p["ansi"][n] for n in ANSI_ORDER}
    return {
        # Syntax. Monokai roles: pink keywords, yellow strings, cyan types,
        # green functions/attributes/tags' names, purple numbers, orange params.
        "--syn-keyword": p["pink"],
        "--syn-string": p["yellow"],
        "--syn-type": p["cyan"],
        "--syn-function": p["green"],
        "--syn-function-call": p["green"],
        "--syn-comment": p["comment"],
        "--syn-comment-style": "normal",
        "--syn-doc-comment": p["comment"],
        "--syn-doc-comment-tag": p["green"],
        "--syn-doc-comment-tag-effect": "none",
        "--syn-doc-comment-tag-value": p["orange"],
        "--syn-doc-markup": p["orange"],
        "--syn-doc-markup-bg": "transparent",
        "--syn-docstring": p["yellow"],
        "--syn-annotation": p["yellow"],
        "--syn-decorator": p["green"],
        "--syn-number": p["purple"],
        "--syn-punct": p["text"],
        "--syn-variable": p["text"],
        "--syn-global": p["text"],
        "--syn-namespace": "var(--fg-editor)",
        "--syn-param": p["orange"],
        "--syn-property": p["text_strong"],
        "--syn-constant": p["purple"],
        "--syn-python-local-variable": "var(--syn-variable)",
        "--syn-python-global-variable": "var(--syn-global)",
        "--syn-python-instance-attribute": "var(--syn-variable)",
        "--syn-python-class-attribute": "var(--syn-property)",
        "--syn-python-constant": "var(--syn-constant)",
        "--syn-python-property": "var(--syn-property)",
        "--syn-python-type-parameter": "var(--syn-type)",
        "--syn-python-builtin": "var(--syn-builtin)",
        "--syn-python-predefined-definition": "var(--syn-predefined)",
        "--syn-python-predefined-usage": "var(--syn-predefined)",
        "--syn-python-fstring": "var(--syn-string)",
        "--syn-python-bytes": "var(--syn-string)",
        "--syn-php-variable": "var(--syn-variable)",
        "--syn-php-function-call": "var(--syn-function)",
        "--syn-builtin": p["cyan"],
        "--syn-self": p["orange"],
        "--syn-keyword-arg": p["orange"],
        "--syn-predefined": p["purple"],
        "--syn-escape": p["purple"],
        "--syn-regexp": p["yellow"],
        "--syn-tag": p["pink"],
        "--syn-attribute": p["green"],
        "--syn-todo": p["yellow"],
        "--syn-link": p["accent"],
        "--syn-markup-heading": p["green"],
        "--syn-markup-code": p["orange"],
        "--syn-invalid": p["red"],
        "--syn-inline-value": p["text_faint"],
        "--syn-rainbow-1": p["cyan"],
        "--syn-rainbow-2": p["orange"],
        "--syn-rainbow-3": p["purple"],
        "--syn-rainbow-4": p["green"],
        "--syn-rainbow-5": p["yellow"],
        "--syn-bracket-1": p["pink"],
        "--syn-bracket-2": p["orange"],
        "--syn-bracket-3": p["yellow"],
        # Editor
        "--fg-editor": p["text"],
        "--caret": p["text_strong"],
        "--fg-line-number": p["text_gutter"],
        "--fg-line-number-current": p["text_secondary"],
        "--border-gutter": p["line"],
        "--border-indent-guide": p["guide"],
        "--border-indent-guide-active": p["guide_active"],
        "--border-right-margin": p["line_soft"],
        "--bg-editor-selection": mix(app, p["text_muted"], 0.3),
        "--bg-editor-selection-inactive": mix(app, p["text_muted"], 0.18),
        "--bg-text-search-result": mix(app, p["cyan"], 0.3),
        "--bg-text-search-result-current": mix(app, p["cyan"], 0.5),
        "--bg-matched-brace": mix(app, p["text_muted"], 0.3),
        "--matched-brace-weight": "700",
        "--bg-matched-tag": mix(app, p["text_muted"], 0.22),
        "--bg-fold-placeholder": p["control"],
        "--fg-fold-placeholder": p["text_muted"],
        "--fg-fold-marker": p["text_faint"],
        "--fg-whitespace": p["line_strong"],
        "--fg-unused": p["text_gutter"],
        "--bg-identifier-under-caret": mix(app, p["text_muted"], 0.2),
        "--bg-identifier-under-caret-write": mix(app, p["pink"], 0.2),
        "--fg-inlay": p["text_muted"],
        "--bg-inlay": p["control"],
        "--wave-error": p["red"],
        "--wave-warning": p["orange"],
        "--editor-error-decoration": f"underline wavy {p['red']}",
        "--editor-warning-decoration": f"underline wavy {p['orange']}",
        "--editor-warning-background": "transparent",
        "--bg-breakpoint-line": mix(app, p["red"], 0.22),
        "--fg-completion-match": p["accent"],
        "--bg-editor-inline": p["elev"],
        "--bg-editor-banner": mix(app, p["cyan"], 0.18),
        "--fg-weak-warning": p["text_faint"],
        "--fg-bulb": p["orange"],
        **ansi,
    }


def grouped(spec: dict[str, list[str]], values: dict[str, str]) -> dict[str, dict[str, str]]:
    names = [n for tokens in spec.values() for n in tokens]
    missing = set(names) - set(values)
    extra = set(values) - set(names)
    if missing or extra:
        raise SystemExit(f"token set mismatch: missing={sorted(missing)} extra={sorted(extra)}")
    return {group: {name: values[name] for name in tokens} for group, tokens in spec.items()}


def render(title: str, intro: str, groups: dict[str, dict[str, str]], head: dict[str, str]) -> str:
    lines = [f"// {title}", *(f"// {l}" for l in intro.splitlines()), "{"]
    for k, v in head.items():
        lines.append(f"  {json.dumps(k)}: {json.dumps(v)},")
    lines.append('  "tokens": {')
    items = list(groups.items())
    for gi, (group, toks) in enumerate(items):
        if gi:
            lines.append("")
        lines.append(f"    // {group}")
        for ti, (k, v) in enumerate(toks.items()):
            last = gi == len(items) - 1 and ti == len(toks) - 1
            lines.append(f"    {json.dumps(k)}: {json.dumps(v)}{'' if last else ','}")
    lines += ["  }", "}", ""]
    return "\n".join(lines)


def check_values(tokens: dict[str, str], where: str) -> None:
    """The plugin host rejects these, and they would break the generated JSON anyway."""
    for name, value in tokens.items():
        if not re.fullmatch(r"--[a-z0-9-]+", name):
            raise SystemExit(f"{where}: invalid token name {name!r}")
        if re.search(r"[;{}<>\\\n]|url\(|image\(", value, re.IGNORECASE) or not value.strip():
            raise SystemExit(f"{where}: unsupported value for {name}: {value!r}")


def main() -> None:
    palette = json.loads((HERE / "palette.json").read_text())
    out = HERE / "themes"
    out.mkdir(exist_ok=True)
    for variant, label in VARIANTS.items():
        entry = palette[variant]
        p, dark = {**entry["colors"], "ansi": entry["ansi"]}, entry["dark"]
        ui = grouped(UI_GROUPS, ui_tokens(p, dark))
        scheme = grouped(SCHEME_GROUPS, scheme_tokens(p, dark))
        check_values({k: v for g in ui.values() for k, v in g.items()}, f"{variant} theme")
        check_values({k: v for g in scheme.values() for k, v in g.items()}, f"{variant} scheme")
        (out / f"{variant}.theme.json").write_text(render(
            f"{label}: UI theme, generated by generate.py from palette.json ({palette['_source']}).",
            "Do not edit by hand; change generate.py and re-run it.",
            ui,
            {"id": variant, "name": label, "kind": "dark" if dark else "light"},
        ))
        (out / f"{variant}.scheme.json").write_text(render(
            f"{label}: editor colour scheme (syntax, editor surfaces, ANSI colours).",
            "Merged over the UI theme's tokens. Generated by generate.py.",
            scheme,
            {"name": label},
        ))
        print(f"wrote {variant}: {sum(len(g) for g in ui.values())} UI + "
              f"{sum(len(g) for g in scheme.values())} scheme tokens")


if __name__ == "__main__":
    main()
