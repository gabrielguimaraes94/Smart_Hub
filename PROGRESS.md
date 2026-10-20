# Progress: UI modernization (branch `modernizacao-visual`)

Keep this list current: tick an item in the same commit that finishes it, and add new items as they come up.
History details are in `git log main..HEAD`.

## Done
- [x] Streamlit 1.66, `st.navigation` with sidebar sections, corporate theme, Gestamp logo, shared `ui.py`
- [x] Sample-data mode (`USE_SAMPLE_DATA=1`, `config.py`, `scripts/make_sample_data.py`)
- [x] Standard layout on every page: Home, EDI VW View, EDI Compare, Press Capacity, Goods Receipt, Coil Storage, FIFO Report
- [x] Coil Storage TV mode (`?tv=1`), fullscreen, 5-minute in-place refresh
- [x] 2026-10-20: all 7 pages validated in the browser with sample data, light theme, no errors
- [x] 2026-10-20: light **and** dark theme (`[theme.light]`/`[theme.dark]`, `--hub-*` tokens, theme-neutral charts); all 7 pages checked in dark, live switch works
- [x] 2026-10-20: Finished Goods DOH in the hub (hub look made in `../DOH_Report`, parity tests green, also on the hub's pandas 2.1.1), "Finished Goods" menu section + Home card, sample data, checked light/dark/TV

## In progress
- [ ] Validate every page in both themes (browser), then merge `modernizacao-visual` into `main`

## Known issues
- `EDI_VW_view`: unguarded `os.listdir` raises when the network share is unreachable (data loading; ask before changing)
