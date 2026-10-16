"""Data source locations for every page.

Set the environment variable USE_SAMPLE_DATA=1 to read the fictitious files in
sample_data/ instead of the network shares (for working off the corporate network).
Regenerate the sample files with:  python scripts/make_sample_data.py
"""
import os
from pathlib import Path

USE_SAMPLE_DATA = os.environ.get("USE_SAMPLE_DATA", "").strip().lower() in {"1", "true", "yes", "on"}

SAMPLE_DIR = Path(__file__).resolve().parent / "sample_data"

# ---- Network locations (production) ----
_NETWORK = {
    # EDI VW drops (sheet "PivotData"), used by EDI_VW_view and Press_capacity
    "EDI_FOLDER": r"\\ch2-python\PowerBI\DATA\Demand\EDI_Converted\sent_email",
    # Press master data (PROJECT, PRESS, REF STAMP PN, %), used by Press_capacity
    "PRESS_MASTER_DATA_FILE": r"\\CH2-PYTHON\PowerBI\DATA\Demand\EDI_Converted\MasterData\Masterdata.xlsx",
    # Coil stock by storage bin, used by Coil_Storage
    "COIL_STOCK_FOLDER": r"\\ch2-python\powerBI\Data\GC2\Stock_coil",
    # Shipping stock with label creation dates, used by FIFO_Report
    "FIFO_FOLDER": r"\\ch2-python\powerBI\Data\GC2\FIFO",
    # Goods receipt exports, used by Receiving_mat
    "RECEIVING_FOLDER": r"\\ch2-file2.us.gestamp.com\PowerBI\DATA\GC2\Receiving_materials",
}

# ---- Sample locations (USE_SAMPLE_DATA=1) ----
_SAMPLE = {
    "EDI_FOLDER": str(SAMPLE_DIR / "edi"),
    "PRESS_MASTER_DATA_FILE": str(SAMPLE_DIR / "masterdata" / "Masterdata.xlsx"),
    "COIL_STOCK_FOLDER": str(SAMPLE_DIR / "stock_coil"),
    "FIFO_FOLDER": str(SAMPLE_DIR / "fifo"),
    "RECEIVING_FOLDER": str(SAMPLE_DIR / "receiving_materials"),
}

_PATHS = _SAMPLE if USE_SAMPLE_DATA else _NETWORK

EDI_FOLDER = _PATHS["EDI_FOLDER"]
PRESS_MASTER_DATA_FILE = _PATHS["PRESS_MASTER_DATA_FILE"]
COIL_STOCK_FOLDER = _PATHS["COIL_STOCK_FOLDER"]
FIFO_FOLDER = _PATHS["FIFO_FOLDER"]
RECEIVING_FOLDER = _PATHS["RECEIVING_FOLDER"]
