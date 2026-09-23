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

    --session-badge-ink: var(--color-sand-500);
    --session-badge-label-ink: var(--color-sand-600);

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

[data-testid="stMainBlockContainer"] {
    padding-top: 4rem !important;
    padding-bottom: 1rem !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
    max-width: 1400px !important;
    margin-left: auto !important;
    margin-right: auto !important;
}
[data-testid="stVerticalBlock"] {
    gap: 0.5rem !important;
}
[data-testid="stCaptionContainer"],
[data-testid="stCaptionContainer"] p {
    margin-bottom: 0 !important;
    color: var(--text-black) !important;
    font-size: 18px !important;
    font-weight: 600;
}

[data-testid="stSidebar"] {
    background: var(--sidebar-bg);
    width: 350px !important;
    min-width: 350px !important;
}
[data-testid="stSidebar"] * {
    color: var(--sidebar-ink);
}
.sidebar-brand {
    font-weight: 800;
    font-size: 18px;
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
[data-testid="stSidebar"] .stButton button {
    width: 70%;
    display: block;
    margin-left: auto !important;
    margin-right: auto !important;
    text-align: left;
    background: var(--sidebar-button-bg);
    border: 1px solid var(--sidebar-button-bg);
    color: var(--text-on-accent);
    font-weight: 600;
    font-size: 18px !important;
    padding: var(--space-5) var(--space-6);
    border-radius: 8px;
}
[data-testid="stSidebar"] .stButton button p {
    font-size: 24px !important;
}
[data-testid="stSidebar"] .stButton button:hover {
    background: var(--sidebar-button-hover-bg);
    color: var(--text-on-accent);
    border-color: var(--accent);
}
[data-testid="stSidebar"] .nav-active button {
    background: var(--accent) !important;
    border-color: var(--accent) !important;
    color: var(--text-on-accent) !important;
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
    color: var(--text-subtitle);
    font-size: 15px;
    margin: var(--space-1) 0 var(--space-2);
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
    gap: var(--space-6);
    font-size: 26px;
    padding: var(--space-4) var(--space-10);
    border-radius: 40px;
    margin: var(--space-4) 0 var(--space-9);
}
.status-badge-lg .dot {
    width: 14px;
    height: 14px;
}

[data-testid="stFileUploader"] {
    background: var(--accent-soft) !important;
    border: 2px dashed var(--accent) !important;
    border-radius: 12px !important;
    min-height: 220px;
    padding: var(--space-11) var(--space-9) !important;
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
    color: var(--ink-faint);
    letter-spacing: 0.04em;
    margin-bottom: var(--space-1);
}

.session-badge {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: var(--session-badge-ink);
    margin-top: var(--space-2);
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
    background: var(--secondary-button-bg) !important;
    color: var(--text-on-accent) !important;
    border: 1px solid var(--secondary-button-bg) !important;
    border-radius: 7px !important;
    font-weight: 600 !important;
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
    margin-top: var(--space-12) !important;
}
[data-testid="stRadio"] {
    width: 100% !important;
}
[data-testid="stRadioGroup"] {
    width: 100% !important;
    align-items: stretch !important;
    gap: var(--space-6) !important;
}
[data-testid="stRadioOption"] {
    flex: 1 !important;
    border: 2px solid var(--ink-faint) !important;
    background: transparent !important;
    border-radius: 10px !important;
    padding: var(--space-9) var(--space-8) !important;
    min-height: 90px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}
[data-testid="stRadioOption"] > div > div:first-child p {
    color: var(--danger) !important;
    font-size: 16px !important;
    font-weight: 600 !important;
}
[data-testid="stRadioOption"] > div > div:first-child > div:first-child {
    width: 22px !important;
    height: 22px !important;
}

[data-testid="stRadioOption"]:not([data-selected]) > div > div:first-child > div:first-child {
    background: var(--ink) !important;
    opacity: 1 !important;
}

[data-testid="stRadioOption"]:not([data-selected]) > div > div:first-child > div:first-child > div {
    background: var(--ink) !important;
}
[data-testid="stRadioOption"][data-selected] {
    border: 2px solid var(--danger) !important;
    background: var(--danger-soft) !important;
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
    font-size: 20px;
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

.spacer-24 { height: var(--space-10); }
.spacer-32 { height: var(--space-13); }
.spacer-35 { height: var(--space-14); }
.spacer-36 { height: var(--space-15); }
</style>
"""
