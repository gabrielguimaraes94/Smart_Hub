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

Always launch through `My_Streamlit_app.py`. A page started directly runs without the navigation menu.

There are no tests or linter config. To smoke-test, use `streamlit.testing.v1.AppTest.from_file(<absolute path to My_Streamlit_app.py>)`, then call `.switch_page("app_pages/<name>.py").run()` for each page. Off the corporate network every page stops at its data-loading step. Set `PYTHONIOENCODING=utf-8` when printing page titles, because they contain emoji.

## Architecture

- **Domain**: Gestamp plant GC2 (automotive stamping) operations dashboards. They are interim replacements for Power BI reports and cover EDI demand, press capacity, coil storage, FIFO, and goods receipt.
- **Data comes only from Windows UNC network shares** as Excel/CSV drops. There is no database or API. All data paths live in `config.py`, which holds the network paths and their sample-data equivalents. Pages import their path from there.
- **Never hardcode a path in a page.**
- **When a page reads a new column or sheet**, update `scripts/make_sample_data.py` so the sample files keep matching.
- **Without network access or sample mode**, pages stop with `st.error`. `EDI_VW_view` is the exception: its unguarded `os.listdir` raises an uncaught exception.
- **File discovery.** Pages pick the newest file in a folder by mtime (`get_latest_file` / glob + `os.path.getmtime`). Pages that read the EDI drops (`EDI_VW_view`, `Press_capacity`) expect sheet `PivotData`.
- **Data logic is not shared.** Each dashboard page still duplicates its helpers (`CAR_MODELS`, `map_part_to_model`, `get_week_number`, `get_latest_file`). When you change shared logic such as the part-number → car-model mapping, update every page that holds a copy. Only paths (`config.py`) and UI (`ui.py`) are shared.
- **Navigation** uses `st.navigation` with `st.Page` objects grouped into sidebar sections, all defined in `My_Streamlit_app.py`. The page files live in `app_pages/`, never in a folder named `pages/` (on Windows, `Pages/` counts too). Streamlit auto-discovers such a folder, and then a deep link opened as the first request after a server restart bypasses the entry point: no theme, no menu sections, no sample banner.
  - **Adding a page** means adding a `st.Page` there and a card in `app_pages/Home.py`.
  - **Home cards** use `st.page_link("app_pages/<file>.py")`. That path must match a page registered in `st.navigation`, or Streamlit raises an error.
  - **The entry point runs on every rerun before the page.** Its `set_page_config` sets the app defaults, and each page's own `set_page_config` overrides only the parameters it passes (for example, the tab title).
- **Caching and state**: `Receiving_mat.py` uses `@st.cache_data(ttl=...)`. The other pages re-read their files on every rerun. `Press_capacity.py` (the largest page) keeps manual demand entries and recalculation flags in `st.session_state`.
- **Styling is being standardized.** The theme lives in `.streamlit/config.toml`, which is read only when `streamlit run` starts from this folder. The entry point shows the Gestamp logo in the sidebar with `st.logo`: it uses `assets/gestamp_logo.png` if the file exists, and the Wikimedia URL otherwise. The dashboard pages still have their own `<style>` blocks, titles, and `st.set_page_config`, and some text is still in Portuguese. Pages move to `ui.py` one at a time.
- **All user-facing UI text is in English**: page titles, menu sections, cards, captions, footer. Conversation with the user is in Portuguese.
- **Shared UI lives in `ui.py`.** It has `apply_base_style` (global CSS, called by the entry point), `hero`, `section_label`, `nav_card`, `page_header`, `kpi_card`, and `footer`. Theme colors and fonts are in `.streamlit/config.toml`. `ui.PRIMARY` must match its `primaryColor`.
- **Deprecated API to avoid in Streamlit 1.66:** `use_container_width`. Use `width="stretch"` or `width="content"` instead. `st.dataframe` now defaults to `"stretch"`.
- The finished-goods DOH report now lives only in the sibling project `../DOH_Report`, which has its own CLAUDE.md.

## Contexto do negócio
- Hub interno da Gestamp (NAFTA) com relatórios em Streamlit.
- Usuários: gerentes de planta, logística, TI
- Páginas: 
My_Streamlit_app.py - Pagina principal onde foi transformada num hub com o acesso as paginas
Coil_Storage.py - Uma ideia para organizar o armazem de Bobinas com as posicoes de cada bobina no estoque
EDI_VW_view.py - Nosso mais importante, com a demanda do cliente, temos um grafico para acompanhar como esta o planejamento de producao de nosso cliente 
FIFO_Report.py - Um relatorio ainda em fase de teste para confirmar o fifo na planta 
Press_capacity.py - Calculo para saber como esta a capacidade de cada maquina   
Receiving_mat.py - Um relatorio de recebimento 

## Regras
- NÃO alterar lógica de dados, consultas ou cálculos sem perguntar antes.
- Nunca colocar senhas ou strings de conexão no código.
- Mudanças em etapas pequenas; explicar o que foi alterado em cada uma.

## Objetivo atual
- Modernizar o visual do hub: Streamlit atualizado, navegação nova, tema e logo da Gestamp, layout padronizado entre as páginas.