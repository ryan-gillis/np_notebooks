import concurrent.futures
import contextlib
import functools
import json
import logging
from multiprocessing import Value
import pathlib
from typing import Generator, Iterable

import IPython
import aind_session
import npc_session
import np_tools
import pandas as pd
import param
import polars as pl
import panel as pn

# pn.config.theme = "dark"
pn.config.notifications = True
pn.extension("tabulator")

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

logging.getLogger("aind_session.utils.codeocean_utils").disabled = True

EPHYS = pathlib.Path("//allen/programs/mindscope/workgroups/dynamicrouting/PilotEphys/Task 2 pilot")
assert EPHYS.exists()
UPLOAD = pathlib.Path("//allen/programs/mindscope/workgroups/np-exp/codeocean")
assert UPLOAD.exists()

executor = concurrent.futures.ThreadPoolExecutor()
expected_suffixes = {".h5": "sync", ".hdf5": "stim", ".mp4": "video"}

# def toggle_tracebacks() -> Generator[None, None, None]:
#     if ipython := IPython.get_ipython():
#         show_traceback = ipython.showtraceback
        
#         def hide_traceback(exc_tuple=None, filename=None, tb_offset=None,
#                         exception_only=False, running_compiled_code=False):
#             etype, value, tb = sys.exc_info()
#             return ipython._showtraceback(etype, value, ipython.InteractiveTB.get_exception_only(etype, value))
        
#         hidden = True
#         while True:
#             ipython.showtraceback = hide_traceback if hidden else show_traceback
#             hidden = yield
#     else:
#         raise RuntimeError("Not in IPython")
# toggle_tb = toggle_tracebacks()
# toggle_tb.send(None)
# def show_tracebacks():
#     toggle_tb.send(False)
# def hide_tracebacks():
#     toggle_tb.send(True)
    
def get_folder_contents_df(folder_names: Iterable[str]) -> pl.DataFrame:
    if not folder_names:
        raise ValueError("Select at least one folder")
    folder_contents = []
    for folder_name in folder_names:
        folder_path = EPHYS / folder_name
        
        def add_contents(path: pathlib.Path):
            
            folder_contents.append(
                {
                    "folder": folder_name,
                    "type": expected_suffixes.get(path.suffix) if "Record Node" not in path.name else "ephys",
                    "name": path.stem,
                    "suffix": path.suffix or None,
                    "size MB": (s := np_tools.size(path)) // 1024**2,
                    "size GB": round(s / 1024**3, 1),
                }
            )
            
        for path in folder_path.glob("*"):
            if path.is_dir() or path.suffix in expected_suffixes:
                if path.name == folder_name: # ephys folder 
                    for subpath in path.glob("*"):
                        add_contents(subpath)
                else:
                    add_contents(path)
    return pl.DataFrame(folder_contents).sort("suffix", "name")

def validate_folder_contents(folder_names: Iterable[str]) -> None:
    folder_contents_df = get_folder_contents_df(folder_names)
    for folder_name in folder_names:
        folder_path = EPHYS / folder_name
        missing = []
        if folder_contents_df.get_column("name").str.contains_any(["Record Node"]).any():
            missing.append("ephys")
        for suffix in expected_suffixes:
            if suffix not in folder_contents_df["suffix"]:
                missing.append(expected_suffixes[suffix])
        if missing:
            print(f"{folder_name} missing data:\n\t{missing}")
            print(folder_path)
        else:
            print(f"{folder_name} appears ready for upload")

    
def get_folder_df():
    folders = [p.name for p in EPHYS.glob('DRpilot*') if p.is_dir() and '366122' not in p.name]
    columns = (
        "subject",
        "ephys",
        "date",
        "folder",
        "created",
        "aind ID",
        "uploaded",
    )
    records = []
    logger.info(f"Submitting {len(folders)} jobs to threadpool")
    def get_row(s: str):
        logger.info(f"Fetching info for {s}")
        row = dict.fromkeys(columns, None)
        row["folder"] = s
        row["ephys"] = (EPHYS / s / s).exists()
        row["date"] = npc_session.extract_isoformat_date(s)
        row["subject"] = str(npc_session.extract_subject(s))
        upload = UPLOAD / s / "upload.csv"
        row["created"] = upload.exists()
        if row["created"]:
            df = pl.read_csv(upload)
            if any('acq-datetime' in c for c in df.columns):
                for c in df.columns:
                    if 'acq-datetime' in c:
                        dt = df[c].drop_nulls()[0]
                        break
            elif r'acq-datetime\r' in df.columns:
                dt = df[r'acq-datetime\r'].drop_nulls()[0]
            elif 'acq-date' in df.columns:
                dt = f"{df['acq-date'].drop_nulls()[0]}_{df['acq-time'].drop_nulls()[0]}"
            else:
                raise ValueError(f"no datetime column found in {upload}") 
            if not dt:
                import pdb; pdb.set_trace()
            dt = dt.replace(':', '-').replace(' ', '_')
            row["aind ID"] = npc_session.AINDSessionRecord(f"ecephys_{row['subject']}_{dt}").id
            row["uploaded"] = aind_session.Session(row["aind ID"]).is_uploaded
        return row
    for row in executor.map(get_row, folders):
        records.append(row)
    if not records:
        df = pd.DataFrame(columns=columns)
    else:
        df = pd.DataFrame(records).sort_values("date", ascending=False)
    return df
    # def content_fn(row) -> pn.pane.Str:
    #     try:
    #         output = (
    #             aind_session.Session(row["aind ID"]).ecephys.sorted_data_dir / "output"
    #         ).read_text()

    #     except AttributeError:
    #         txt = "no sorted data found"
    #     else:
    #         txt = (
    #             f"raw asset ID: {aind_session.Session(row['session']).raw_data_asset.id}\n"
    #             f"sorted asset ID: {aind_session.Session(row['session']).ecephys.sorted_data_asset.id}\n"
    #             f"\noutput:\n{output}"
    #         )
    #     return pn.pane.Str(
    #         object=txt,
    #         styles={"font-size": "12pt"},
    #         sizing_mode="stretch_width",
    #     )
    
def get_folder_table(
    ephys_only: bool = False,
    unstarted_only: bool = False,
) -> pn.widgets.Tabulator:
    """Get sessions for a specific subject and date range."""
    # yield pn.indicators.LoadingSpinner(
    #     value=True, size=20, name="Fetching folders..."
    # )
    df = get_folder_df()
    if ephys_only:
        df = df[df["ephys"]]
    if unstarted_only:
        df = df[~df["created"]]
    column_filters = {
        'subject': {'type': 'input', 'func': 'like', 'placeholder': 'like x'},
        'folder': {'type': 'input', 'func': 'like', 'placeholder': 'like x'},
        'ephys': {'type': 'tickCross', 'tristate': True, 'indeterminateValue': None, 'defaultValue': True},
        'created': {'type': 'tickCross', 'tristate': True, 'indeterminateValue': None},
        'uploaded': {'type': 'tickCross', 'tristate': True, 'indeterminateValue': None},
    }
    # Custom formatter to highlight cells with False in the success column
    def color_negative_red(val):
        """
        Takes a scalar and returns a string with
        the css property `'color: red'` for negative
        bools, black otherwise.
        """
        color = (
            "red" if not val else ("white" if pn.config.theme == "dark" else "black")
        )
        return "color: %s" % color

    stylesheet = """
    .tabulator-cell {
        font-size: 12px;
    }
    """
    table = pn.widgets.Tabulator(
        hidden_columns=["date"] + (["ephys"] if ephys_only else []),
        # groupby=["subject"],
        page_size=15,
        value=df,
        selectable='checkbox-single',
        # disabled=True,
        show_index=False,
        sizing_mode="stretch_width",
        # row_content=content_fn,
        widths={'folder': "20%", 'aind ID': "20%"},

        embed_content=False,
        stylesheets=[stylesheet],
        formatters={
            "bool": {"type": "tickCross"},  # not working
        },
        header_filters=column_filters,
    )
    table.style.map(color_negative_red)

    # def callback(event):
    #     if event.column == "trigger":
    #         try_run_sorting(df["session"].iloc[event.row])
    #     ## expand row
    #     # else:
    #     #     table.expanded = [event.row] if event.row not in table.expanded else []
    #     #     table._update_children()

    # table.on_click(callback)
    return table

