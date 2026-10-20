# Progress: UI modernization (branch `modernizacao-visual`)

Keep this list current: tick an item in the same commit that finishes it, and add new items as they come up.
History details are in `git log main..HEAD`.

## Done
- [x] Streamlit 1.66, `st.navigation` with sidebar sections, corporate theme, Gestamp logo, shared `ui.py`
- [x] Sample-data mode (`USE_SAMPLE_DATA=1`, `config.py`, `scripts/make_sample_data.py`)
- [x] Standard layout on every page: Home, EDI VW View, EDI Compare, Press Capacity, Goods Receipt, Coil Storage, FIFO Report
- [x] Coil Storage TV mode (`?tv=1`), fullscreen, 5-minute in-place refresh
- [x] 2026-10-20: all 7 pages validated in the browser with sample data, light theme, no errors

## In progress
- [ ] Light **and** dark theme: `[theme.light]`/`[theme.dark]` in config.toml, theme-aware CSS in `ui.py`, theme-neutral chart colors in every page
- [ ] Finished Goods DOH in the hub: change the visuals in `../DOH_Report` (source of truth, parity tests), rebuild, copy to `app_pages/`, register in `st.navigation` + Home card, sample data
- [ ] Validate every page in both themes (browser), then merge `modernizacao-visual` into `main`

## Known issues
- `EDI_VW_view`: unguarded `os.listdir` raises when the network share is unreachable (data loading; ask before changing)
