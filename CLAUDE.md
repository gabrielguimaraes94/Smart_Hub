# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this directory is

This folder is a Python virtualenv `Scripts/` directory (it holds `python.exe`, `pip.exe`, `streamlit.exe`, `activate*`). Someone also put a Streamlit multipage app in it. The only source code here is:

- `My_Streamlit_app.py`: the landing page ("Functionality Hub").
- `Pages/*.py`: one self-contained dashboard per file.

Ignore everything else in this folder (venv launchers, `pywin32_*.py`). The git root is the user's home directory (`C:\Users\gguimaraes`), not this folder, so `git status` shows unrelated files.

The venv is incomplete. There is no `pyvenv.cfg` next to it, and the bundled `python.exe` printed no output when tested. Use a working system or venv Python that has `streamlit`, `pandas`, `openpyxl`, `plotly`, and `numpy`.

## Running

```powershell
streamlit run My_Streamlit_app.py          # hub + all Pages in the sidebar
streamlit run Pages/Finish_Goods_DOH.py    # any page also runs standalone
```

There are no tests, linter config, or requirements file in this folder.

## Architecture

- **Domain**: Gestamp plant GC2 (automotive stamping) operations dashboards. They are interim replacements for Power BI reports and cover EDI demand, press capacity, coil storage, FIFO, goods receipt, and finished-goods days-on-hand (DOH).
- **Data comes only from Windows UNC network shares** as Excel/CSV drops. There is no database or API. Each page hardcodes its own path constants at the top of the file, for example `\\ch2-python\PowerBI\DATA\...`, `\\ch2-file2.us.gestamp.com\...`, and `\\ch2-file3...`. Pages fail (with `st.error`) when they run off the corporate network. To test locally, temporarily repoint these constants.
- **Pages load files in one of two ways.** Most pick the newest file in a folder by mtime (`get_latest_file` / glob + `os.path.getmtime`). `Finish_Goods_DOH.py` instead parses `STOCK_GC2_DDMMYYYY_HHMM.csv` filenames (`;`-separated). Pages that read the EDI drops (`EDI_VW_view`, `Press_capacity`) expect sheet `PivotData`.
- **No shared module.** Each page is copy-paste independent: it calls its own `st.set_page_config`, defines its own CSS, and duplicates helpers (`CAR_MODELS`, `map_part_to_model`, `get_week_number`, `get_latest_file`). When you change shared logic such as the part-number → car-model mapping, update every page that holds a copy.
- **Hub links are hand-written HTML anchors** in `My_Streamlit_app.py` (`create_functionality(..., page)`). The `page` value must match the page file's stem. The hub currently links `Advanced_Search` and `Settings`, which have no page files, and it does not link `FIFO_Report` or `Finish_Goods_DOH`.
- **Caching and state**: newer pages use `@st.cache_data(ttl=...)`, and `Finish_Goods_DOH` passes file mtimes as cache-key arguments so a new file invalidates the cache. `Press_capacity.py` (the largest page) keeps manual demand entries and recalculation flags in `st.session_state`.
- **`Finish_Goods_DOH.py` is built for a factory TV display.** It renders an HTML table through `components.html`, auto-reloads every `AUTO_REFRESH_MINUTES`, persists UI choices in URL query params (`qp_get`/`qp_set`, with a fallback for Streamlit < 1.30), and puts DOH thresholds and storage-location (LGORT) groupings in constants at the top. A fuller modular version of this report lives in the sibling project `../DOH_Report` (it has its own CLAUDE.md). Keep the two in sync deliberately.
