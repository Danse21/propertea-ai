"""Python-side mirror of styles.py's `:root` color palette.

matplotlib can't read CSS custom properties, so chart colors need their own
copy of the same values — this is that copy. Keep it in sync with the
palette tier in styles.py by hand; only the entries Python code actually
uses are mirrored here, not the full palette (most of it is pure-CSS
concerns like sidebar or input styling that no chart ever touches).
"""

COLORS = {
    "white": "#FFFFFF",
    "black": "#000000",
    "gray-900": "#14202B",
    "teal-600": "#0E7C86",
    "orange-500": "#E8623D",
    "red-600": "#DC2626",
}
