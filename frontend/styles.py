CSS = """
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap">
<style>
:root {
    color-scheme: light;

    --color-white: #FFFFFF;
    --color-black: #000000;

    --color-clay-50: #FBF8F1;
    --color-clay-100: #EDE4D2;
    --color-clay-200: #E8DEC9;
    --color-clay-300: #D8CBB2;
    --color-clay-400: #BCAC8E;
    --color-clay-500: #9C8C6E;
    --color-clay-600: #786A51;
    --color-clay-700: #554A3C;
    --color-clay-750: #43392D;
    --color-clay-800: #362E24;
    --color-clay-900: #2A241C;

    --color-sand-400: #A8997C;
    --color-sand-500: #8C7B5E;
    --color-sand-600: #6F6250;

    --color-matcha-100: #E7EFD9;
    --color-matcha-500: #6E8F45;
    --color-matcha-600: #5F7F3A;
    --color-matcha-700: #4C6A2E;
    --color-matcha-900: #3C5424;

    --color-brew-750: #4A3726;
    --color-brew-800: #3A2B1D;
    --color-brew-900: #241A11;

    --color-cream-50: #FBF3E4;
    --color-cream-300: #C3A87A;

    --color-rooibos-600: #C0472B;
    --color-rooibos-700: #96301C;
    --color-amber-500: #C2761F;

    --bg: var(--color-clay-50);
    --surface: var(--color-white);
    --ink: var(--color-clay-900);
    --ink-soft: var(--color-clay-700);
    --ink-faint: var(--color-sand-400);
    --ink-muted: var(--color-clay-700);
    --border: var(--color-clay-100);
    --accent: var(--color-matcha-600);
    --accent-soft: var(--color-matcha-100);
    --accent-dark: var(--color-matcha-700);
    --highlight: var(--color-amber-500);
    --danger: var(--color-rooibos-700);
    --danger-soft: color-mix(in srgb, var(--danger) 6%, transparent);

    --text-black: var(--color-black);
    --text-strong: var(--color-clay-800);
    --text-subtitle: var(--color-clay-750);
    --text-on-accent: var(--color-white);

    --sidebar-bg: var(--color-brew-900);
    --sidebar-ink: var(--color-cream-50);
    --sidebar-ink-soft: var(--color-cream-300);
    --sidebar-button-bg: var(--color-matcha-600);
    --sidebar-button-hover-bg: var(--color-brew-800);
    --sidebar-divider: var(--color-brew-750);

    --secondary-button-bg: var(--color-matcha-900);

    --input-border: var(--color-clay-500);
    --input-muted-ink: var(--color-clay-600);

    --uploader-button-bg: var(--color-clay-200);
    --uploader-button-border: var(--color-clay-300);
    --uploader-button-hover-border: var(--color-clay-400);

    --session-badge-ink: var(--color-cream-300);
    --session-badge-label-ink: var(--color-sand-400);

    --space-1: 2px;
    --space-2: 4px;
    --space-3: 6px;
    --space-4: 8px;
    --space-5: 10px;
    --space-6: 12px;
    --space-7: 14px;
    --space-8: 16px;
    --space-9: 20px;
    --space-10: 24px;
    --space-11: 28px;
    --space-12: 40px;
    --space-13: 32px;
    --space-14: 35px;
    --space-15: 36px;
}

html, body, [class*="css"] {
    font-family: 'Manrope', 'Helvetica Neue', Arial, sans-serif;
}

[data-testid="stAppViewContainer"] {
    background: var(--bg);
}
[data-testid="stHeader"] {
    background: var(--bg) !important;
}

[data-testid="stMainBlockContainer"] {
    padding-top: 4.5rem !important;
    padding-bottom: 3rem !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
    max-width: 1120px !important;
    margin-left: auto !important;
    margin-right: auto !important;
}
[data-testid="stVerticalBlock"] {
    gap: 0.6rem !important;
}
[data-testid="stMain"] [data-testid="stHeading"] h1 {
    font-size: 30px !important;
    margin-bottom: var(--space-2) !important;
    padding-top: 0 !important;
}
[data-testid="stMain"] [data-testid="stHeading"] h3 {
    font-size: 17px !important;
}
[data-testid="stMain"] [data-testid="stVerticalBlockBorderWrapper"] {
    margin-bottom: var(--space-3);
}
[data-testid="stCaptionContainer"],
[data-testid="stCaptionContainer"] p {
    margin-bottom: 0 !important;
    color: var(--ink-muted) !important;
    font-size: 13px !important;
    font-weight: 400 !important;
    line-height: 1.5;
}

[data-testid="stSidebar"] {
    background: var(--sidebar-bg);
    width: 250px !important;
    min-width: 250px !important;
}
[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {
    padding-top: var(--space-9);
}
[data-testid="stSidebar"] * {
    color: var(--sidebar-ink);
}
.sidebar-brand {
    font-weight: 800;
    font-size: 16px;
    color: var(--text-on-accent);
    padding-bottom: var(--space-8);
    border-bottom: 1px solid var(--sidebar-divider);
    margin-bottom: var(--space-5);
}
.note {
    background: var(--accent-soft);
    border: 1px solid var(--border);
    border-left: 3px solid var(--accent);
    border-radius: 6px;
    padding: var(--space-6) var(--space-8);
    color: var(--ink-soft);
    font-size: 14px;
}
.auth-brand {
    font-weight: 800;
    font-size: 22px;
    color: var(--text-strong);
    padding-bottom: var(--space-8);
    border-bottom: 1px solid var(--color-clay-200);
    margin-bottom: var(--space-5);
}
.nav-group {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--session-badge-label-ink);
    margin: var(--space-9) 0 var(--space-3) var(--space-7);
}
.nav-group:first-of-type {
    margin-top: var(--space-4);
}
[data-testid="stSidebar"] .stButton button {
    width: 100%;
    display: flex;
    justify-content: flex-start !important;
    text-align: left;
    font-weight: 600;
    padding: var(--space-4) var(--space-7);
    border-radius: 8px;
    min-height: 0;
}
[data-testid="stSidebar"] .stButton button p {
    font-size: 15px !important;
    font-weight: 600 !important;
}

/* inactive nav: quiet */
[data-testid="stSidebar"] .stButton button[kind="tertiary"] {
    background: transparent !important;
    border: 1px solid transparent !important;
    color: var(--sidebar-ink-soft) !important;
}
[data-testid="stSidebar"] .stButton button[kind="tertiary"] p {
    color: var(--sidebar-ink-soft) !important;
    font-weight: 500 !important;
}
[data-testid="stSidebar"] .stButton button[kind="tertiary"]:hover {
    background: var(--sidebar-button-hover-bg) !important;
    color: var(--sidebar-ink) !important;
}
[data-testid="stSidebar"] .stButton button[kind="tertiary"]:hover p {
    color: var(--sidebar-ink) !important;
}

/* active nav: accent block with an edge indicator */
[data-testid="stSidebar"] .stButton button[kind="primary"] {
    background: var(--accent) !important;
    border: 1px solid var(--accent) !important;
    border-left: 3px solid var(--color-cream-50) !important;
    color: var(--text-on-accent) !important;
}
[data-testid="stSidebar"] .stButton button[kind="primary"] p {
    color: var(--text-on-accent) !important;
    font-weight: 700 !important;
}
[data-testid="stSidebar"] .stButton button[kind="primary"]:hover {
    background: var(--accent-dark) !important;
    border-color: var(--accent-dark) !important;
    border-left-color: var(--color-cream-50) !important;
}

/* log out: subdued utility */
[data-testid="stSidebar"] .st-key-nav-logout button p {
    font-size: 12px !important;
    font-weight: 500 !important;
    color: var(--session-badge-ink) !important;
}
[data-testid="stSidebar"] .st-key-nav-logout button {
    padding: var(--space-2) var(--space-7);
}
[data-testid="stSidebar"] .st-key-nav-logout button:hover p {
    color: var(--sidebar-ink) !important;
}

h1, h2, h3,
[data-testid="stHeading"] h1,
[data-testid="stHeading"] h2,
[data-testid="stHeading"] h3,
[data-testid="stMarkdownContainer"] h1,
[data-testid="stMarkdownContainer"] h2,
[data-testid="stMarkdownContainer"] h3 {
    letter-spacing: -0.01em;
    color: var(--text-black) !important;
}

.subtitle {
    color: var(--ink-muted);
    font-size: 14px;
    line-height: 1.5;
    margin: 0 0 var(--space-6);
}
.section-hint {
    color: var(--ink-muted);
    font-size: 13px;
    margin: 0 0 var(--space-5);
}

.status-badge {
    display: inline-flex;
    align-items: center;
    gap: var(--space-3);
    background: var(--accent-soft);
    color: var(--accent-dark);
    font-size: 13px;
    font-weight: 600;
    padding: var(--space-2) var(--space-6);
    border-radius: 20px;
    margin: var(--space-2) 0 var(--space-5);
}
.status-badge .dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--accent-dark);
    flex-shrink: 0;
}
.status-badge-lg {
    font-size: 14px;
    padding: var(--space-3) var(--space-8);
    margin: var(--space-3) 0 var(--space-6);
}
.status-badge-lg .dot {
    width: 8px;
    height: 8px;
}

[data-testid="stFileUploader"] {
    background: var(--accent-soft) !important;
    border: 2px dashed var(--accent) !important;
    border-radius: 12px !important;
    min-height: 150px;
    padding: var(--space-9) var(--space-9) !important;
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    justify-content: center !important;
    text-align: center !important;
    gap: var(--space-5);
    margin-bottom: var(--space-2);
}
[data-testid="stFileUploader"] * {
    color: var(--ink) !important;
}
[data-testid="stFileUploader"] [data-testid="stWidgetLabel"] {
    justify-content: center !important;
}
[data-testid="stFileUploader"] [data-testid="stWidgetLabel"],
[data-testid="stFileUploader"] [data-testid="stWidgetLabel"] p {
    text-align: center !important;
    font-size: 15px !important;
    font-weight: 600 !important;
    width: 100% !important;
    margin: 0 !important;
}
[data-testid="stFileUploaderDropzone"] {
    background: transparent !important;
    border: none !important;
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    gap: var(--space-5);
    width: 100%;
}
[data-testid="stFileUploaderDropzoneInstructions"] {
    font-size: 13px !important;
    color: var(--ink-soft) !important;
}
[data-testid="stFileUploaderDropzone"] button {
    background: var(--uploader-button-bg) !important;
    color: var(--text-strong) !important;
    border: 1px solid var(--uploader-button-border) !important;
    border-radius: 7px !important;
    font-weight: 600 !important;
}
[data-testid="stFileUploaderDropzone"] button:hover {
    background: var(--uploader-button-border) !important;
    border-color: var(--uploader-button-hover-border) !important;
}

.crumb {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: var(--color-clay-500);
    letter-spacing: 0.04em;
    margin-bottom: var(--space-2);
}

.context-bar {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: var(--space-3) var(--space-8);
    background: var(--surface);
    border: 1px solid var(--border);
    border-left: 3px solid var(--accent);
    border-radius: 8px;
    padding: var(--space-5) var(--space-8);
    margin-bottom: var(--space-6);
}
.context-bar .ctx-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--color-clay-500);
    margin-right: var(--space-3);
}
.context-bar .ctx-value {
    font-size: 14px;
    font-weight: 700;
    color: var(--text-strong);
}
.context-bar .ctx-meta {
    font-size: 13px;
    color: var(--ink-muted);
}
.context-bar.is-stale {
    border-left-color: var(--highlight);
}

.session-badge {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: var(--session-badge-ink);
    margin: var(--space-12) 0 var(--space-2) var(--space-7);
    border-top: 1px solid var(--sidebar-divider);
    padding-top: var(--space-6);
}
.session-badge .lbl {
    color: var(--session-badge-label-ink);
    letter-spacing: 0.06em;
    display: block;
    font-size: 10px;
}

div[data-testid="stMetric"] {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: var(--space-7) var(--space-8);
}
div[data-testid="stMetricValue"] {
    font-family: 'JetBrains Mono', monospace;
    color: var(--accent-dark);
}

.stButton > button[kind="primary"] {
    background: var(--accent);
    border-color: var(--accent);
}
.stButton > button[kind="primary"]:hover {
    background: var(--accent-dark);
    border-color: var(--accent-dark);
}

[data-testid="stMain"] .stButton > button[kind="secondary"] {
    background: var(--surface) !important;
    color: var(--accent-dark) !important;
    border: 1px solid var(--color-clay-300) !important;
    border-radius: 7px !important;
    font-weight: 600 !important;
}
[data-testid="stMain"] .stButton > button[kind="secondary"]:hover {
    background: var(--accent-soft) !important;
    border-color: var(--accent) !important;
    color: var(--accent-dark) !important;
}
[data-testid="stMain"] .stButton > button[kind="tertiary"] {
    color: var(--ink-muted) !important;
    font-weight: 500 !important;
}
[data-testid="stMain"] .stButton > button:disabled,
[data-testid="stMain"] .stButton > button:disabled p {
    opacity: 0.55 !important;
}

[data-testid="stTextInputRootElement"] {
    background: var(--surface) !important;
    border: 1px solid var(--input-border) !important;
    border-radius: 7px !important;
}
[data-testid="stTextInputField"] {
    background: transparent !important;
    color: var(--ink) !important;
}
[data-testid="stTextInputField"]::placeholder {
    color: var(--input-muted-ink) !important;
    opacity: 1 !important;
}
[data-testid="stTextInputField"][disabled],
[data-testid="stTextInputField"][disabled]::placeholder {
    color: var(--input-muted-ink) !important;
    -webkit-text-fill-color: var(--input-muted-ink) !important;
    opacity: 1 !important;
}
[data-testid="stMain"] [data-testid="stWidgetLabel"],
[data-testid="stMain"] [data-testid="stWidgetLabel"] p {
    color: var(--text-strong) !important;
    font-weight: 600 !important;
    font-size: 14px !important;
}

[data-testid="stElementContainer"]:has([data-testid="stRadio"]) {
    width: 100% !important;
    margin-top: var(--space-4) !important;
}
[data-testid="stRadio"] {
    width: 100% !important;
}
[data-testid="stRadioGroup"] {
    width: 100% !important;
    align-items: stretch !important;
    gap: var(--space-6) !important;
}
[data-testid="stRadioGroup"] > * {
    flex: 1 !important;
    min-width: 0 !important;
}
[data-testid="stRadioOption"] {
    flex: 1 !important;
    border: 1px solid var(--color-clay-300) !important;
    background: var(--surface) !important;
    border-radius: 10px !important;
    padding: var(--space-6) var(--space-8) !important;
    min-height: 60px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}
[data-testid="stRadioOption"] > div > div:first-child p {
    color: var(--text-strong) !important;
    font-size: 15px !important;
    font-weight: 600 !important;
}
[data-testid="stRadioOption"] > div > div:first-child > div:first-child {
    width: 18px !important;
    height: 18px !important;
}
[data-testid="stRadioOption"]:not([data-selected]) > div > div:first-child > div:first-child,
[data-testid="stRadioOption"]:not([data-selected]) > div > div:first-child > div:first-child > div {
    background: var(--color-clay-400) !important;
    opacity: 1 !important;
}
[data-testid="stRadioOption"]:hover {
    border-color: var(--color-clay-400) !important;
}
[data-testid="stRadioOption"][data-selected] {
    border: 2px solid var(--accent) !important;
    background: var(--accent-soft) !important;
}
[data-testid="stRadioOption"][data-selected] > div > div:first-child p {
    color: var(--accent-dark) !important;
}
[data-testid="stRadioOption"][data-selected] > div > div:first-child > div:first-child,
[data-testid="stRadioOption"][data-selected] > div > div:first-child > div:first-child > div {
    background: var(--accent) !important;
}
[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .rmse-box-label) {
    border: 1px solid var(--ink-faint) !important;
    border-radius: 8px !important;
    min-height: 72px !important;
    display: flex !important;
    align-items: center !important;
}

.rmse-box-label {
    text-align: left;
    font-size: 16px;
    font-weight: 700;
    font-family: 'JetBrains Mono', monospace;
    color: var(--accent-dark);
}

.legend-item {
    font-size: 13px;
    color: var(--ink);
    margin-bottom: var(--space-2);
}
.legend-item b {
    font-family: 'JetBrains Mono', monospace;
}
.legend-raw {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: var(--ink-faint);
}

.divider {
    display: flex;
    align-items: center;
    gap: var(--space-6);
    margin: var(--space-4) 0;
    color: var(--ink-faint);
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    letter-spacing: 0.08em;
}
.divider::before, .divider::after {
    content: "";
    flex: 1;
    height: 1px;
    background: var(--border);
}

@media (max-width: 1200px) {
    [data-testid="stSidebar"] {
        width: 220px !important;
        min-width: 220px !important;
    }
    [data-testid="stMainBlockContainer"] {
        padding-left: 1.25rem !important;
        padding-right: 1.25rem !important;
    }
}
@media (max-width: 820px) {
    [data-testid="stMainBlockContainer"] {
        padding-top: 3.25rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }
    [data-testid="stMain"] [data-testid="stHeading"] h1 {
        font-size: 24px !important;
    }
    [data-testid="stRadioGroup"] {
        flex-wrap: wrap !important;
    }
    [data-testid="stRadioOption"] {
        flex: 1 1 100% !important;
    }
    [data-testid="stFileUploader"] {
        min-height: 120px;
        padding: var(--space-8) var(--space-6) !important;
    }
    .context-bar {
        flex-direction: column;
        gap: var(--space-2);
    }
    [data-testid="stMain"] [data-testid="stHorizontalBlock"] {
        flex-wrap: wrap !important;
    }
}

.jump-link {
    display: inline-block;
    font-size: 13px;
    font-weight: 600;
    color: var(--accent-dark);
    text-decoration: none;
    border: 1px solid var(--color-clay-300);
    border-radius: 7px;
    padding: var(--space-4) var(--space-7);
    background: var(--surface);
}
.jump-link:hover {
    background: var(--accent-soft);
    border-color: var(--accent);
}

.spacer-24 { height: var(--space-10); }
.spacer-32 { height: var(--space-13); }
.spacer-35 { height: var(--space-14); }
.spacer-36 { height: var(--space-15); }
</style>
"""
