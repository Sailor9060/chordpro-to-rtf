"""Core ChordPro -> RTF conversion logic (no external dependencies)."""

import re

CHORD_RE = re.compile(r"\[[^\]]*\]")
CHORD_CAPTURE_RE = re.compile(r"\[([^\]]*)\]")
DIRECTIVE_RE = re.compile(r"^\{(.*)\}\s*$")

TITLE_DIRECTIVES = {"title", "t"}
SUBTITLE_DIRECTIVES = {"subtitle", "st"}
COMMENT_DIRECTIVES = {"comment", "c", "comment_italic", "ci", "comment_box", "cb"}
LABEL_DIRECTIVES = {"label", "highlight"}

START_SECTION_DIRECTIVES = {
    "start_of_verse": "sov",
    "start_of_chorus": "soc",
    "start_of_bridge": "sob",
    "start_of_tab": "sot",
    "start_of_grid": "sog",
}
END_SECTION_DIRECTIVES = {
    "end_of_verse": "eov",
    "end_of_chorus": "eoc",
    "end_of_bridge": "eob",
    "end_of_tab": "eot",
    "end_of_grid": "eog",
}
# alias -> canonical
START_ALIASES = {}
for full, short in START_SECTION_DIRECTIVES.items():
    START_ALIASES[full] = full
    START_ALIASES[short] = full
END_ALIASES = {}
for full, short in END_SECTION_DIRECTIVES.items():
    END_ALIASES[full] = full
    END_ALIASES[short] = full

# Sections whose body is chord/tab notation, not lyrics -- skip their content entirely.
SKIP_CONTENT_SECTIONS = {"start_of_tab", "start_of_grid"}

# Grid section values often start with a bar-count layout hint like "0+4+4" or
# "4+4", optionally followed by a real label (e.g. "0+4+4 Instrumental") --
# strip that numeric prefix, keeping any label text that follows it.
GRID_NUMERIC_PREFIX_RE = re.compile(r"^[\d+]+(?=\s|$)")

# Directives that should be silently ignored (metadata, chord defs, formatting)
IGNORED_PREFIXES = (
    "define", "chord", "capo", "key", "time", "tempo", "duration",
    "album", "artist", "composer", "lyricist", "copyright", "year",
    "key_of", "new_song", "ns", "meta", "instrument",
    "textfont", "textsize", "chordfont", "chordsize", "titlefont",
    "titlesize", "columns", "col", "pagetype", "grid", "no_grid",
    "image", "footer", "header", "x_",
)


class Block:
    """A piece of output: kind is one of title/subtitle/label/comment/lyric/blank."""

    def __init__(self, kind, text=""):
        self.kind = kind
        self.text = text


def strip_chords(line):
    return CHORD_RE.sub("", line)


def parse_directive(body):
    """Split a directive body 'name: value' or 'name value' or 'name' into (name, value)."""
    if ":" in body:
        name, _, value = body.partition(":")
    else:
        parts = body.split(None, 1)
        name = parts[0] if parts else ""
        value = parts[1] if len(parts) > 1 else ""
    return name.strip().lower(), value.strip()


def parse_chordpro(text, mode="lyrics"):
    """Parse ChordPro source text into a list of Block objects.

    mode="lyrics": strip chords, keep the words; tab/grid section bodies
    (pure chord/tab notation) are skipped, only their label is kept.
    mode="chords": keep only the chord symbols from each line (words
    dropped); tab/grid section bodies are kept verbatim since they're
    already just chords/tab notation.
    """
    blocks = []
    in_gridtab = False  # inside a start_of_tab/start_of_grid section

    for raw_line in text.splitlines():
        line = raw_line.rstrip("\n\r")

        m = DIRECTIVE_RE.match(line.strip())
        if m:
            name, value = parse_directive(m.group(1))

            if name in START_ALIASES:
                canonical = START_ALIASES[name]
                in_gridtab = canonical in SKIP_CONTENT_SECTIONS
                if canonical == "start_of_grid":
                    value = GRID_NUMERIC_PREFIX_RE.sub("", value).strip()
                    label = value if value else "Instruments"
                else:
                    label = value if value else canonical.replace("start_of_", "").capitalize()
                blocks.append(Block("label", label))
                continue

            if name in END_ALIASES:
                in_gridtab = False
                blocks.append(Block("blank"))
                continue

            if in_gridtab:
                # inside a tab/grid block, ignore all other directives too
                continue

            if name in TITLE_DIRECTIVES:
                blocks.append(Block("title", value))
                continue
            if name in SUBTITLE_DIRECTIVES:
                blocks.append(Block("subtitle", value))
                continue
            if name in COMMENT_DIRECTIVES:
                blocks.append(Block("comment", value))
                continue
            if name in LABEL_DIRECTIVES:
                blocks.append(Block("label", value))
                continue
            if name == "chorus":
                blocks.append(Block("label", value if value else "Chorus"))
                continue

            # anything else (metadata, chord defs, formatting) is ignored
            continue

        if in_gridtab:
            # raw tablature/chord-grid content, not lyrics
            if mode == "chords":
                content = line.strip()
                blocks.append(Block("lyric", content) if content else Block("blank"))
            continue

        if line.strip().startswith("#"):
            # ChordPro line comment -- discarded, not shown in either output
            continue

        if line.strip() == "":
            blocks.append(Block("blank"))
            continue

        if mode == "chords":
            chords = CHORD_CAPTURE_RE.findall(line)
            content = "  ".join(c for c in chords if c.strip())
            if content:
                blocks.append(Block("lyric", content))
        else:
            lyric = strip_chords(line).strip()
            if lyric:
                blocks.append(Block("lyric", lyric))
            else:
                blocks.append(Block("blank"))

    return _collapse_blanks(blocks)


def _collapse_blanks(blocks):
    """Collapse runs of consecutive blank blocks into a single blank, and trim ends."""
    result = []
    for b in blocks:
        if b.kind == "blank" and result and result[-1].kind == "blank":
            continue
        result.append(b)
    while result and result[0].kind == "blank":
        result.pop(0)
    while result and result[-1].kind == "blank":
        result.pop()
    return result


# ---------------------------------------------------------------------------
# RTF generation
# ---------------------------------------------------------------------------

def rtf_escape(text):
    """Escape a plain unicode string for inclusion in RTF text."""
    out = []
    for ch in text:
        code = ord(ch)
        if ch == "\\":
            out.append("\\\\")
        elif ch == "{":
            out.append("\\{")
        elif ch == "}":
            out.append("\\}")
        elif code < 0x80:
            out.append(ch)
        else:
            # RTF unicode escape; signed 16-bit value expected by most readers
            if code > 0x7FFF:
                code -= 0x10000
            out.append("\\u%d?" % code)
    return "".join(out)


def _group_into_segments(blocks):
    """Group blocks into RTF paragraphs.

    A label or comment opens a new paragraph and absorbs any lyric lines
    that immediately follow it (joined with a line break, not a new
    paragraph) until the next title/subtitle/label/comment or a blank line
    closes it. Title/subtitle always stand alone in their own paragraph
    (they use a different, centered alignment).
    """
    segments = []
    current = None

    def close_current():
        nonlocal current
        if current is not None:
            segments.append(current)
            current = None

    for b in blocks:
        if b.kind == "lyric":
            if current is None:
                current = {"kind": None, "header": None, "lyrics": []}
            current["lyrics"].append(b.text)
        elif b.kind == "blank":
            close_current()
        elif b.kind in ("title", "subtitle"):
            close_current()
            segments.append({"kind": b.kind, "header": b.text, "lyrics": []})
        else:  # label or comment
            close_current()
            current = {"kind": b.kind, "header": b.text, "lyrics": []}

    close_current()
    return segments


def blocks_to_rtf(blocks):
    lines = []
    lines.append(
        r"{\rtf1\ansi\ansicpg1252\deff0"
        r"{\fonttbl{\f0\fswiss\fcharset0 Calibri;}{\f1\fswiss\fcharset0 Calibri Light;}}"
    )
    lines.append(r"{\colortbl;\red0\green0\blue0;\red90\green90\blue90;}")
    lines.append(r"\viewkind4\uc1\pard\sa200\sl276\slmult1\f0\fs22")

    for seg in _group_into_segments(blocks):
        kind = seg["kind"]
        header = seg["header"]
        lyric_parts = [rtf_escape(t) for t in seg["lyrics"]]

        if kind == "title":
            lines.append(r"\pard\qc\b\fs40 " + rtf_escape(header) + r"\b0\fs22\par")
        elif kind == "subtitle":
            lines.append(r"\pard\qc\i\fs26 " + rtf_escape(header) + r"\i0\fs22\par")
        elif kind == "label":
            head = r"\b\fs24\cf1 " + rtf_escape(header) + r"\b0\fs22\cf0"
            lines.append(r"\pard\ql " + r"\line ".join([head] + lyric_parts) + r"\par")
        elif kind == "comment":
            head = r"\i\cf2 " + rtf_escape(header) + r"\i0\cf0"
            lines.append(r"\pard\ql " + r"\line ".join([head] + lyric_parts) + r"\par")
        elif lyric_parts:
            lines.append(r"\pard\ql " + r"\line ".join(lyric_parts) + r"\par")

    lines.append("}")
    return "\r\n".join(lines)


def convert(text, mode="lyrics"):
    """Convert ChordPro source text to an RTF document string.

    mode is "lyrics" (words only, chords stripped) or "chords" (chord
    symbols only, words stripped). See parse_chordpro for details.
    """
    blocks = parse_chordpro(text, mode=mode)
    return blocks_to_rtf(blocks)


def convert_file(input_path, output_path, mode="lyrics"):
    with open(input_path, "r", encoding="utf-8-sig", errors="replace") as f:
        text = f.read()
    rtf = convert(text, mode=mode)
    with open(output_path, "w", encoding="ascii", errors="backslashreplace") as f:
        f.write(rtf)
