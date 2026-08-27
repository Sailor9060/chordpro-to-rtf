# ChordPro → RTF Converter — User Guide

Turns a ChordPro song file (`.cho`, `.crd`, `.pro`) into clean, print-ready
RTF documents — one with just the **lyrics**, one with just the **chords** —
so you don't have to manually strip a song sheet down to what you need.

## Installing

No installation required. Download `ChordProToRTF.exe` and run it — it's a
single, self-contained file for Windows.

The first time you run it, Windows SmartScreen may show
**"Windows protected your PC"** because the app isn't signed by a
recognized publisher. Click **More info → Run anyway** to continue.

### Optional: install it properly (Program Files + PATH)

If you'd rather have it live in `C:\Program Files` and be runnable from any
terminal, download `install_to_program_files.ps1` from the same release and
put it in the same folder as `ChordProToRTF.exe`. Then, from an
**elevated** ("Run as administrator") PowerShell window, run:

```powershell
powershell -ExecutionPolicy Bypass -File "install_to_program_files.ps1"
```

This moves the exe into `C:\Program Files\Franz Weber Software`, updates
the Desktop shortcut to point there, adds a matching shortcut inside that
folder, and adds the folder to your system `PATH` — so after opening a new
terminal, typing `ChordProToRTF` launches it from anywhere.

## Using the app

1. **Choose your source file**, either:
   - Click **Browse...** next to *Source file* and pick a `.cho`/`.crd`/`.pro` file, or
   - Drag the file from Explorer and drop it onto the **"Drag & drop a ChordPro file here"** box.
2. The two output paths under **Output files** fill in automatically, next
   to your source file:
   - `<song name>  (Lyrics).rtf`
   - `<song name>  (Chords).rtf`
   You can edit either path directly, or click its **Browse...** button to
   choose a different name or folder.
3. Untick **Lyrics file** or **Chords file** if you only want one of the two.
4. Click **⚡ Convert**. If an output file already exists, you'll be asked
   before it's overwritten.
5. The **Log** at the bottom shows what was created; a summary popup
   confirms when it's done.

### Drag-and-drop from the desktop

A shortcut icon named **ChordProToRTF** is placed on your Desktop. Drag a
ChordPro file straight onto that icon (no need to open the app first) and
it will launch with the file already loaded as the source — just click
Convert.

## What goes into each file

Both files keep:
- **Title** and subtitle
- **Section labels** — Verse, Chorus, Bridge, or any custom name you gave a
  section (e.g. `{start_of_verse: Pre-Chorus 1}`), shown in bold
- **Comments** — `{comment: ...}` / `{ci: ...}` / `{cb: ...}` directives,
  shown in italics. Lines starting with `#` are ChordPro's own line-comment
  syntax and are discarded from both files, not shown.

They differ in the body text:

| | Lyrics file | Chords file |
|---|---|---|
| Words | kept | dropped |
| Chord symbols like `[Ab7]` | dropped | kept (plain text) |
| Chord grid / tab sections (`{start_of_grid}`, `{start_of_tab}`) | only the section label is shown | the chord grid / tab lines are kept as-is |

A grid section's label is taken from its directive text with any leading
bar-count numbers stripped — `{start_of_grid: 0+4+4 Instrumental}` becomes
just **Instrumental**. If a grid section has no real label at all, it's
labeled **Instruments**.

Metadata directives that don't belong on a lyric/chord sheet — `{key}`,
`{capo}`, `{tempo}`, `{define}` chord diagrams, font/formatting directives,
etc. — are ignored in both files.

## Troubleshooting

- **"This file already exists"** — you'll be asked to confirm before an
  output file is overwritten. If the file is open in another program
  (e.g. Word), close it first or the write will fail.
- **No drag-and-drop box / it says "unavailable"** — this means the
  drag-and-drop component didn't load; browsing for the file with the
  **Browse...** button still works normally.
