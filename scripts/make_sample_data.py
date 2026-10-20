"""Generate fictitious sample files in sample_data/ for USE_SAMPLE_DATA=1.

Every value is synthetic (random with a fixed seed); nothing is copied from real files.
Dates are relative to today so the pages show current-looking data. Re-run any time:

    python scripts/make_sample_data.py

Schemas mirror what each page reads:
  edi/*.xlsx                  sheet "PivotData": Part, Date From, Release Qty   (EDI_VW_view, EDI_Compare,
                              4 weekly files; creation time = send date           Press_capacity)
  masterdata/Masterdata.xlsx  PROJECT, PRESS, REF STAMP PN, %                   (Press_capacity)
  stock_coil/*.xlsx           LGPLA (RA-01..RH-08), MATNR, LENUM, VERME          (Coil_Storage)
  fifo/*.xlsx                 Data de criacao, Material, Descricao, Lote,
                              Numero da etiqueta, Quantidade                     (FIFO_Report)
  receiving_materials/*.xlsx  12 columns A..L; the page reads D,E,F,G,I,K,L by position:
                              Warehouse, Delivery Date, Material, Quantity,
                              Invoice Number, Supplier Code, Supplier Name      (Receiving_mat)
  doh/                        stock/STOCK_GC2_*.csv, Demand_master_Data.xlsx,
                              sales/GC2_SALES*.XLSX                              (Finish_Goods_DOH)
                              written by ../DOH_Report/scripts/make_sample_data.py, the
                              generator of the project the page is built from
"""
import importlib.util
import os
import random
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent / "sample_data"
TODAY = date.today()
rng = random.Random(42)


def _write(df, path, sheet_name="Sheet1", mtime=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(path, sheet_name=sheet_name, index=False)
    if mtime is not None:  # pages pick the newest file by mtime
        ts = time.mktime(mtime.timetuple())
        os.utime(path, (ts, ts))
    print(f"  {path.relative_to(ROOT.parent)}  ({len(df)} rows)")


def _set_creation_time(path, when):
    """Windows only: set the file creation time (EDI pages order and date EDI files by it)."""
    if os.name != "nt":
        return
    import ctypes
    from ctypes import wintypes
    k32 = ctypes.windll.kernel32
    k32.CreateFileW.restype = wintypes.HANDLE
    ticks = int(time.mktime(when.timetuple()) * 10_000_000) + 116444736000000000
    ft = wintypes.FILETIME(ticks & 0xFFFFFFFF, ticks >> 32)
    handle = k32.CreateFileW(str(path), 0x100, 0, None, 3, 0x80, None)  # FILE_WRITE_ATTRIBUTES, OPEN_EXISTING
    if handle and handle != wintypes.HANDLE(-1).value:
        k32.SetFileTime(handle, ctypes.byref(ft), None, None)
        k32.CloseHandle(handle)


def make_edi():
    # Part numbers contain the CAR_MODELS keys used by the pages; one unmapped part is filtered out.
    parts = {
        "11K 809 605 A": 1400,   # MEB
        "3CM 809 605 B": 650,    # Coupe
        "3CN 809 605 C": 900,    # Atlas
        "3CR 809 605 A": 500,    # Atlas NF
        "3CS 809 605 A": 350,    # Coupe NF
        "5ZZ 999 000": 100,      # not mapped to a model
    }
    # Four weekly EDI files (sent 21, 14, 7 and 0 days ago), each covering 10 weeks from one week
    # before it was sent. All share one underlying plan, so consecutive files differ only by small
    # noise plus the deliberate changes below (for EDI Compare). Each change applies from the given
    # file version on, to delivery dates between the two offsets (days from today).
    edi_rng = random.Random(7)
    first_day = TODAY - timedelta(days=28)
    plan = {(part, first_day + timedelta(days=d)): max(0, edi_rng.gauss(base, base * 0.15))
            for part, base in parts.items() for d in range(100)}
    changes = [
        # (from version, part, first day offset, last day offset, factor)
        (2, "11K 809 605 A", 7, 20, 0.85),    # MEB cut for two weeks
        (3, "3CN 809 605 C", 0, 13, 1.20),    # Atlas pulled up
        (3, "3CS 809 605 A", 21, 41, 0.60),   # Coupe NF big cut
        (4, "11K 809 605 A", 0, 6, 1.10),     # MEB up this week
        (4, "3CM 809 605 B", 14, 34, 0.80),   # Coupe cut
        (4, "3CR 809 605 A", 28, 48, 1.25),   # Atlas NF up
    ]

    edi_dir = ROOT / "edi"
    for old in edi_dir.glob("*.xlsx"):  # start clean so creation times follow the send order
        old.unlink()
    for version, sent_days_ago in ((1, 21), (2, 14), (3, 7), (4, 0)):
        sent = TODAY - timedelta(days=sent_days_ago)
        start = sent - timedelta(days=7)
        rows = []
        for part in parts:
            for d in range(70):
                day = start + timedelta(days=d)
                if day.weekday() == 6:  # no releases on Sundays
                    continue
                qty = plan[(part, day)]
                for v, p, lo, hi, factor in changes:
                    if version >= v and p == part and lo <= (day - TODAY).days <= hi:
                        qty *= factor
                qty *= edi_rng.uniform(0.98, 1.02)
                rows.append({"Part": part, "Date From": pd.Timestamp(day), "Release Qty": int(qty)})
        path = edi_dir / f"EDI_VW_SAMPLE_{sent:%Y%m%d}.xlsx"
        sent_at = datetime.combine(sent, datetime.min.time()) + timedelta(hours=6)
        _write(pd.DataFrame(rows), path, sheet_name="PivotData", mtime=sent_at)
        _set_creation_time(path, sent_at)


def make_masterdata():
    rows = []
    projects = {
        "MEB": [("PRESS1", 1.0), ("PRESS2", 1.0), ("BLNK", 0.5)],
        "Coupe": [("PRESS1", 1.0), ("BLNK", 0.5)],
        "Coupe NF": [("PRESS2", 1.0), ("BLNK", 0.5)],
        "Atlas": [("PRESS1", 1.0), ("PRESS2", 0.5), ("BLNK", 0.5)],
        "Atlas NF": [("PRESS2", 1.0), ("BLNK", 0.5)],
        "MQB": [("PRESS1", 0.5), ("BLNK", 1.0)],
    }
    n = 100
    for project, presses in projects.items():
        for press, pct in presses:
            n += 1
            rows.append({"PROJECT": project, "PRESS": press, "REF STAMP PN": f"SMP-{n:04d}", "%": pct})
    _write(pd.DataFrame(rows), ROOT / "masterdata" / "Masterdata.xlsx")


def make_coil_stock():
    rails = {"A": 7, "B": 7, "C": 7, "D": 7, "E": 7, "F": 8, "G": 7, "H": 7}
    grades = ["DC04", "DC06", "HX340", "CR420", "DX54"]
    rows = []
    for rail, n in rails.items():
        for i in range(1, n + 1):
            if rng.random() < 0.65:
                rows.append({
                    "LGPLA": f"R{rail}-{i:02d}",
                    "MATNR": f"SMP-COIL-{rng.choice(grades)}-{rng.choice([0.7, 0.8, 1.0, 1.2, 1.5])}",
                    "LENUM": f"99{rng.randint(10000000, 99999999)}",
                    "VERME": rng.randint(4500, 14500),
                })
    _write(pd.DataFrame(rows), ROOT / "stock_coil" / "Stock_coil_SAMPLE.xlsx")


def make_fifo():
    materials = [(f"SMP-{n:05d}", f"Sample bracket {n}") for n in range(30100, 30116)]
    rows = []
    for k in range(240):
        mat, desc = rng.choice(materials)
        age = int(rng.triangular(0, 160, 20))
        rows.append({
            "Data de criacao": pd.Timestamp(TODAY - timedelta(days=age)),
            "Material": mat,
            "Descricao": desc,
            "Lote": f"L{rng.randint(1000, 1099)}",
            "Numero da etiqueta": f"ET{700000 + k}",
            "Quantidade": rng.choice([50, 100, 120, 200, 240]),
        })
    _write(pd.DataFrame(rows), ROOT / "fifo" / "FIFO_SAMPLE.xlsx")


def make_receiving():
    suppliers = [("SUP001", "Sample Steel Co."), ("SUP002", "Demo Fasteners Inc."),
                 ("SUP003", "Example Coatings"), ("SUP004", "Fictional Metals"),
                 ("SUP005", "Test Logistics Parts")]
    materials = [f"SMP-RM-{n:04d}" for n in range(1, 21)]
    for month_offset in (1, 0):  # two monthly exports; the page concatenates every file
        rows = []
        for k in range(150):
            day = TODAY - timedelta(days=30 * month_offset + rng.randint(0, 29))
            code, name = rng.choice(suppliers)
            rows.append({
                "Plant": "GC2",                                          # A
                "Document": f"50{rng.randint(1000000, 9999999)}",        # B
                "Item": rng.randint(1, 9),                               # C
                "Warehouse": rng.choice(["RM01", "RM02", "COIL"]),       # D
                "Delivery Date": pd.Timestamp(day),                      # E
                "Material": rng.choice(materials),                       # F
                "Quantity": rng.randint(10, 2000),                       # G
                "Unit": "EA",                                            # H
                "Invoice Number": f"INV-{month_offset}{rng.randint(0, 59):03d}",  # I (repeats = multi-line deliveries)
                "PO Number": f"45{rng.randint(1000000, 9999999)}",       # J
                "Supplier Code": code,                                   # K
                "Supplier Name": name,                                   # L
            })
        _write(pd.DataFrame(rows), ROOT / "receiving_materials" / f"Receiving_SAMPLE_m{month_offset}.xlsx")


def make_doh():
    """Finished Goods DOH files, from the DOH_Report generator so both projects stay in sync."""
    gen = Path(__file__).resolve().parents[2] / "DOH_Report" / "scripts" / "make_sample_data.py"
    if not gen.exists():
        print(f"Skipping doh/: {gen} not found")
        return
    spec = importlib.util.spec_from_file_location("doh_sample_data", gen)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.generate(ROOT / "doh", seed=42)


if __name__ == "__main__":
    print(f"Writing sample data to {ROOT}")
    make_edi()
    make_masterdata()
    make_coil_stock()
    make_fifo()
    make_receiving()
    make_doh()
