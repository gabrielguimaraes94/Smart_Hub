# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this directory is

This folder is a Python virtualenv `Scripts/` directory (it holds `python.exe`, `pip.exe`, `streamlit.exe`, `activate*`). Someone also put a Streamlit multipage app in it. The only source code here is:

- `My_Streamlit_app.py`: the entry point and router (`st.navigation`).
- `app_pages/Home.py`: the landing page ("Functionality Hub").
- `app_pages/*.py`: one self-contained dashboard per file.

Ignore everything else in this folder (venv launchers, `pywin32_*.py`). `.gitignore` excludes them. This folder is its own git repo (`origin` = github.com/gabrielguimaraes94/Smart_Hub). `main` is the stable branch, and the UI modernization work happens on `modernizacao-visual`. It sits inside an accidental, commit-less repo at the user's home directory, so always run git from here.

The venv is broken (there is no `pyvenv.cfg`, and the bundled `python.exe` doesn't run). The app runs on the system **Python 3.11** (`C:\Program Files\Python311`, user site-packages), with the versions pinned in `requirements.txt` (Streamlit 1.66.0).

## Running

```powershell
& "C:\Program Files\Python311\python.exe" -m pip install --user -r requirements.txt
& "C:\Program Files\Python311\python.exe" -m streamlit run My_Streamlit_app.py
```

**Off the corporate network**, use sample data. `USE_SAMPLE_DATA=1` points every path in `config.py` to the fictitious files in `sample_data/`, and the entry point then shows a "Sample data mode" banner. To regenerate the files, run `scripts/make_sample_data.py`; it uses a fixed seed and dates relative to today.

```powershell
$env:USE_SAMPLE_DATA="1"; & "C:\Program Files\Python311\python.exe" -m streamlit run My_Streamlit_app.py
```

**Server check:** `scripts/check_server.py` checks Python, the `requirements.txt` pins, the app files and every network share in `config.py`. It only reads; run it on the server.

Always launch through `My_Streamlit_app.py`. A page started directly runs without the navigation menu.

**Visual check in a browser.** The `chrome-devtools` MCP (ecc plugin) drives a real Chrome from this session. Start the server in the background on `127.0.0.1:8599` with sample data, open each page with `new_page`/`navigate_page`, and capture it with `take_screenshot`. Use `emulate colorScheme=dark|light` to test both themes.

There are no tests or linter config. To smoke-test, use `streamlit.testing.v1.AppTest.from_file(<absolute path to My_Streamlit_app.py>)`, then call `.switch_page("app_pages/<name>.py").run()` for each page. Off the corporate network every page stops at its data-loading step. Set `PYTHONIOENCODING=utf-8` when printing page titles, because they contain emoji.

## Architecture

- **Domain**: Gestamp plant GC2 (automotive stamping) operations dashboards. They are interim replacements for Power BI reports and cover EDI demand, press capacity, coil storage, FIFO, and goods receipt.
- **Data comes only from Windows UNC network shares** as Excel/CSV drops. There is no database or API. All data paths live in `config.py`, which holds the network paths and their sample-data equivalents. Pages import their path from there.
- **Never hardcode a path in a page.**
- **When a page reads a new column or sheet**, update `scripts/make_sample_data.py` so the sample files keep matching.
- **Without network access or sample mode**, pages stop with `st.error`. `EDI_VW_view` is the exception: its unguarded `os.listdir` raises an uncaught exception.
- **File discovery.** Pages pick the newest file in a folder by mtime (`get_latest_file` / glob + `os.path.getmtime`). Pages that read the EDI drops (`EDI_VW_view`, `Press_capacity`) expect sheet `PivotData`.
- **Data logic is not shared.** Each dashboard page still duplicates its helpers (`CAR_MODELS`, `map_part_to_model`, `get_week_number`, `get_latest_file`). When you change shared logic such as the part-number → car-model mapping, update every page that holds a copy. Only paths (`config.py`) and UI (`ui.py`) are shared. The one exception is `EDI_Compare.py`, which imports its loading, mapping and week helpers from `app_pages.EDI_VW_view`, so changing those functions changes both pages.
- **Navigation** uses `st.navigation` with `st.Page` objects grouped into sidebar sections, all defined in `My_Streamlit_app.py`. The page files live in `app_pages/`, never in a folder named `pages/` (on Windows, `Pages/` counts too). Streamlit auto-discovers such a folder, and then a deep link opened as the first request after a server restart bypasses the entry point: no theme, no menu sections, no sample banner.
  - **Adding a page** means adding a `st.Page` there and a card in `app_pages/Home.py`.
  - **Home cards** use `st.page_link("app_pages/<file>.py")`. That path must match a page registered in `st.navigation`, or Streamlit raises an error.
  - **The entry point runs on every rerun before the page.** Its `set_page_config` sets the app defaults, and each page's own `set_page_config` overrides only the parameters it passes (for example, the tab title).
- **Caching and state**: `Receiving_mat.py` uses `@st.cache_data(ttl=...)`. The other pages re-read their files on every rerun. `Press_capacity.py` (the largest page) keeps manual demand entries in `st.session_state` and recalculates saturation from them on every run.
- **Styling is being standardized.** The theme lives in `.streamlit/config.toml`, which is read only when `streamlit run` starts from this folder. The entry point shows the Gestamp logo in the sidebar with `st.logo`: it uses `assets/gestamp_logo.png` if the file exists, and the Wikimedia URL otherwise. Every page uses `ui.py` (`page_header`, `kpi_card`, `footer`) and has no `<style>` block or `st.set_page_config` of its own; charts use the brand colors (`ui.PRIMARY`), `font=ui.CHART_FONT` (Inter, no color) and `gridcolor=ui.GRID_COLOR`.
- **Light and dark theme.** `config.toml` has `[theme.light]` and `[theme.dark]`, so the app follows the OS and Settings. Streamlit exposes no theme CSS variables, so a script in `ui.apply_base_style` sets `<html data-hub-theme="light|dark">` from the app background, and the `--hub-*` CSS tokens (`ui._TOKENS`, light/dark pairs) switch on it. In custom HTML/CSS use `var(--hub-...)`, never a fixed hex. In Plotly, leave text colors unset (the Streamlit chart theme follows the app); the plot area and pie borders are themed by CSS. A fixed text color is fine only on a fixed-color shape (e.g. dark text on a light-yellow box). Thin lines use `ui.LINE_COLOR`, because `PRIMARY` is too dark to read on the dark theme. In the dark theme, CSS turns the logo white. **Fonts:** Inter for text (`font`), Barlow Semi Condensed for titles (`headingFont`) and for big numbers and branded titles through `var(--hub-display-font)` (`ui.DISPLAY_FONT`). TV pages turn off Streamlit's fade on stale elements, so a background refresh (`st.fragment(run_every=...)`) does not dim the screen.
- **TV mode (`?tv=1`)** is for shop-floor TVs. The entry point hides navigation (`position="hidden"`) and applies `ui.apply_tv_style()`, which hides the sidebar and toolbar and compacts the layout.
  - **Fit:** with `?tv=1`, `Coil_Storage` fits a 1920×1080 screen.
  - **Live refresh:** pages shown on TVs use `@st.fragment(run_every="5m")` instead of a `<meta refresh>`, so fullscreen and the search survive refreshes.
  - **Fullscreen:** `ui.fullscreen_button()` binds its click handler in a `<script>`, because `st.html` strips inline `onclick`.
  - **Permanent TV:** use a kiosk browser, `chrome --kiosk "<url>/Coil_Storage?tv=1"`.
- **All user-facing UI text is in English**: page titles, menu sections, cards, captions, footer. Conversation with the user is in Portuguese.
- **Shared UI lives in `ui.py`.** It has `apply_base_style` (global CSS, called by the entry point), `hero` (Home banner with date and watermark), `section_label` (numbered), `nav_card` (custom HTML card with an icon in the Material Symbols font, `accent` blue/orange/green per section, an invisible `st.page_link` stretched over it; never style the icon span with another font, or the icon name shows as text), `page_header`, `kpi_card`, and `footer`, plus the TV helpers (`is_tv_mode`, `apply_tv_style`, `tv_mode_button`, `fullscreen_button`), `sample_data_notice`, and the Coil Storage building blocks (`rail_title`, `slot_card`, `legend`). Check it before writing new HTML/CSS in a page. Theme colors and fonts are in `.streamlit/config.toml`. `ui.PRIMARY` must match `[theme.light] primaryColor`.
- **Deprecated API to avoid in Streamlit 1.66:** `use_container_width`. Use `width="stretch"` or `width="content"` instead. `st.dataframe` now defaults to `"stretch"`.
- **Finished Goods DOH.** The source lives in the sibling project `../DOH_Report`, which has its own CLAUDE.md and parity tests against Power BI. `app_pages/Finish_Goods_DOH.py` is a copy of its generated single-file build (`dist/Finish_Goods_DOH.py`, made by `scripts/build_single_file.py`). Never edit the copy here: change the modules there, run its tests and build, then copy the build over. Because the build cannot import this hub's `config.py`, that file exports the DOH paths as the environment variables `DOH_STOCK_FOLDER`, `DOH_DEMAND_FILE` and `DOH_SALES_FOLDER`, which the build reads. Its sample files (`sample_data/doh/`) come from DOH_Report's own generator, which `scripts/make_sample_data.py` calls (`make_doh`). The DOH table is wide: it scrolls sideways while the sidebar is open, and fits a 1920 px screen with `?tv=1`.
- `Erros/` (untracked) holds the user's screenshots of UI issues (light and dark versions). It is reference material, not source.

## Contexto do negócio
- Hub interno da Gestamp (NAFTA) com relatórios em Streamlit.
- Usuários: gerentes de planta, logística, TI
- Páginas: 
My_Streamlit_app.py - Pagina principal onde foi transformada num hub com o acesso as paginas
Coil_Storage.py - Uma ideia para organizar o armazem de Bobinas com as posicoes de cada bobina no estoque
EDI_VW_view.py - Nosso mais importante, com a demanda do cliente, temos um grafico para acompanhar como esta o planejamento de producao de nosso cliente 
EDI_Compare.py - Compara as liberações EDI entre arquivos (reaproveita as funções do EDI_VW_view)
FIFO_Report.py - Um relatorio ainda em fase de teste para confirmar o fifo na planta 
Press_capacity.py - Calculo para saber como esta a capacidade de cada maquina   
Receiving_mat.py - Um relatorio de recebimento 
Finish_Goods_DOH.py - Estoque de produto acabado, DOH e vendas da semana (build do ../DOH_Report)

## Regras
- NÃO alterar lógica de dados, consultas ou cálculos sem perguntar antes.
- Nunca colocar senhas ou strings de conexão no código.
- Mudanças em etapas pequenas; explicar o que foi alterado em cada uma.

## Objetivo atual
- Modernizar o visual do hub: Streamlit atualizado, navegação nova, tema e logo da Gestamp, layout padronizado entre as páginas.
## Progress
@PROGRESS.md
