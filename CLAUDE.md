# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this directory is

This folder is a Python virtualenv `Scripts/` directory (it holds `python.exe`, `pip.exe`, `streamlit.exe`, `activate*`). Someone also put a Streamlit multipage app in it. The only source code here is:

- `My_Streamlit_app.py`: the entry point and router (`st.navigation`).
- `Pages/Home.py`: the landing page ("Functionality Hub").
- `Pages/*.py`: one self-contained dashboard per file.

Ignore everything else in this folder (venv launchers, `pywin32_*.py`). `.gitignore` excludes them. This folder is its own git repo (`origin` = github.com/gabrielguimaraes94/Smart_Hub). `main` is the stable branch, and the UI modernization work happens on `modernizacao-visual`. It sits inside an accidental, commit-less repo at the user's home directory, so always run git from here.

The venv is broken (there is no `pyvenv.cfg`, and the bundled `python.exe` doesn't run). The app runs on the system **Python 3.11** (`C:\Program Files\Python311`, user site-packages), with the versions pinned in `requirements.txt` (Streamlit 1.66.0).

## Running

```powershell
& "C:\Program Files\Python311\python.exe" -m pip install --user -r requirements.txt
& "C:\Program Files\Python311\python.exe" -m streamlit run My_Streamlit_app.py
```

Always launch through `My_Streamlit_app.py`. A page started directly runs without the navigation menu.

There are no tests or linter config. To smoke-test, use `streamlit.testing.v1.AppTest.from_file(<absolute path to My_Streamlit_app.py>)`, then call `.switch_page("Pages/<name>.py").run()` for each page. Off the corporate network every page stops at its data-loading step. Set `PYTHONIOENCODING=utf-8` when printing page titles, because they contain emoji.

## Architecture

- **Domain**: Gestamp plant GC2 (automotive stamping) operations dashboards. They are interim replacements for Power BI reports and cover EDI demand, press capacity, coil storage, FIFO, goods receipt, and finished-goods days-on-hand (DOH).
- **Data comes only from Windows UNC network shares** as Excel/CSV drops. There is no database or API. Each page hardcodes its own path constants at the top of the file, for example `\\ch2-python\PowerBI\DATA\...`, `\\ch2-file2.us.gestamp.com\...`, and `\\ch2-file3...`. Pages fail with `st.error` when they run off the corporate network. `EDI_VW_view` is the exception: its unguarded `os.listdir` raises an uncaught exception. To test locally, temporarily repoint these constants.
- **File discovery.** Pages pick the newest file in a folder by mtime (`get_latest_file` / glob + `os.path.getmtime`). Pages that read the EDI drops (`EDI_VW_view`, `Press_capacity`) expect sheet `PivotData`.
- **No shared module.** Each page is copy-paste independent: it calls its own `st.set_page_config`, defines its own CSS, and duplicates helpers (`CAR_MODELS`, `map_part_to_model`, `get_week_number`, `get_latest_file`). When you change shared logic such as the part-number → car-model mapping, update every page that holds a copy.
- **Navigation** uses `st.navigation` with `st.Page` objects grouped into sidebar sections, all defined in `My_Streamlit_app.py`. Because `st.navigation` is in use, Streamlit's `pages/` auto-discovery is off, so the capital-P `Pages/` folder name doesn't matter.
  - **Adding a page** means adding a `st.Page` there and a card in `Pages/Home.py`.
  - **Home cards** use `st.page_link("Pages/<file>.py")`. That path must match a page registered in `st.navigation`, or Streamlit raises an error.
  - **The entry point runs on every rerun before the page.** Its `set_page_config` sets the app defaults, and each page's own `set_page_config` overrides only the parameters it passes (for example, the tab title).
- **Caching and state**: `Receiving_mat.py` uses `@st.cache_data(ttl=...)`. The other pages re-read their files on every rerun. `Press_capacity.py` (the largest page) keeps manual demand entries and recalculation flags in `st.session_state`.
- **Styling is per-page.** Each page injects its own `<style>` block through `st.markdown(..., unsafe_allow_html=True)`. There is no `.streamlit/config.toml` theme. `Home.py` loads the Gestamp logo from a Wikimedia URL.
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