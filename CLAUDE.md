# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this directory is

This folder is a Python virtualenv `Scripts/` directory (it holds `python.exe`, `pip.exe`, `streamlit.exe`, `activate*`). Someone also put a Streamlit multipage app in it. The only source code here is:

- `My_Streamlit_app.py`: the landing page ("Functionality Hub").
- `Pages/*.py`: one self-contained dashboard per file.

Ignore everything else in this folder (venv launchers, `pywin32_*.py`). `.gitignore` excludes them. This folder is its own git repo (`origin` = github.com/gabrielguimaraes94/Smart_Hub, branch `main`). It sits inside an accidental, commit-less repo at the user's home directory, so always run git from here.

The venv is incomplete. There is no `pyvenv.cfg` next to it, and the bundled `python.exe` printed no output when tested. Use a working system or venv Python that has `streamlit`, `pandas`, `openpyxl`, `plotly`, and `numpy`.

## Running

```powershell
streamlit run My_Streamlit_app.py          # hub + all Pages in the sidebar
streamlit run Pages/EDI_VW_view.py         # any page also runs standalone
```

There are no tests, linter config, or requirements file in this folder.

## Architecture

- **Domain**: Gestamp plant GC2 (automotive stamping) operations dashboards. They are interim replacements for Power BI reports and cover EDI demand, press capacity, coil storage, FIFO, goods receipt, and finished-goods days-on-hand (DOH).
- **Data comes only from Windows UNC network shares** as Excel/CSV drops. There is no database or API. Each page hardcodes its own path constants at the top of the file, for example `\\ch2-python\PowerBI\DATA\...`, `\\ch2-file2.us.gestamp.com\...`, and `\\ch2-file3...`. Pages fail (with `st.error`) when they run off the corporate network. To test locally, temporarily repoint these constants.
- **File discovery.** Pages pick the newest file in a folder by mtime (`get_latest_file` / glob + `os.path.getmtime`). Pages that read the EDI drops (`EDI_VW_view`, `Press_capacity`) expect sheet `PivotData`.
- **No shared module.** Each page is copy-paste independent: it calls its own `st.set_page_config`, defines its own CSS, and duplicates helpers (`CAR_MODELS`, `map_part_to_model`, `get_week_number`, `get_latest_file`). When you change shared logic such as the part-number → car-model mapping, update every page that holds a copy.
- **Hub links are hand-written HTML anchors** in `My_Streamlit_app.py` (`create_functionality(..., page)`). The `page` value must match the page file's stem. The hub currently links `Advanced_Search` and `Settings`, which have no page files, and it does not link `FIFO_Report`.
- **Caching and state**: `Receiving_mat.py` uses `@st.cache_data(ttl=...)`. The other pages re-read their files on every rerun. `Press_capacity.py` (the largest page) keeps manual demand entries and recalculation flags in `st.session_state`.
- **Styling is per-page.** Each page injects its own `<style>` block through `st.markdown(..., unsafe_allow_html=True)`. There is no `.streamlit/config.toml` theme. The hub loads the Gestamp logo from a Wikimedia URL.
- **The pages folder is `Pages/` with a capital P.** Streamlit's auto-discovery expects `pages/`, so this only works because Windows paths are case-insensitive. Keep this in mind when moving to `st.navigation` / `st.Page` or deploying on Linux.
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