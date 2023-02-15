import dataclasses
import datetime
import enum
import pathlib
import threading
import time
from typing import ClassVar, NamedTuple, NoReturn, Optional, TypedDict

import IPython
import IPython.display
import ipywidgets as ipw
import np_config
import np_logging
import np_session
import np_services
import PIL.Image
import pydantic

import np_workflows.npxc as npxc

logger = np_logging.getLogger(__name__)


class TTNSession(enum.Enum):
    """Enum for stimulus sessions."""
    PRETEST = 'pretest'
    HAB_60 = 'hab 60'
    HAB_90 = 'hab 90'
    HAB_120 = 'hab 120'
    ECEPHYS = 'ecephys'


def stim_repeats(old: int, reversed: int, annotated: int) -> dict[str, dict[str, int]]:
    return {'stim_repeats': dict(old=old, reversed=reversed, annotated=annotated)}

def opto_params(pretest=False):
    params = dict(level_list=[1.15, 1.28, 1.345])
    if pretest: 
        params.update(**dict(operation_mode='pretest'))
    else: 
        params.update(**dict(operation_mode='experiment'))
    return {'opto': params}

def mapping_params(pretest=False):
    return {}

class TTNSelectedSession:
    
    common_params: ClassVar[dict] = {}
    "Will be updated with `session_params` when a session is selected."
    
    session_params: ClassVar[dict[TTNSession, dict]] = {
        TTNSession.PRETEST: {**stim_repeats(1, 1, 1), **opto_params(pretest=True), **mapping_params(pretest=True)},
        TTNSession.HAB_60: {**stim_repeats(15, 5, 1)},
        TTNSession.HAB_90: {**stim_repeats(20, 7, 2)},
        TTNSession.HAB_120: {**stim_repeats(25, 8, 2), **mapping_params()}, # stim-only is 103 mins
        TTNSession.ECEPHYS: {**stim_repeats(25, 8, 2),  **opto_params(), **mapping_params()}, 
    }
    
    opto_script: ClassVar[str] = 'C:/ProgramData/StimulusFiles/dev/opto_tagging_v2.py'
    
    def __init__(self, session: str | TTNSession):
        if isinstance(session, str):
            session = TTNSession(session)
        self.session = session
        
    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(session={self.session})'
    
    @property
    def script(self) -> str:
        logger.warning(f'Using hard-coded script in notebooks directory for testing')
        # will eventually point to 'C:/ProgramData/StimulusFiles/dev/oct22_tt_stim_script.py'
        return np_config.local_to_unc(np_config.Rig().sync, pathlib.Path('oct22_tt_stim_script.py').resolve()).as_posix()
    
    @property
    def params(self) -> dict:
        return self.__class__.common_params | self.__class__.session_params[self.session]

        
    
def stim_session_select_widget() -> TTNSelectedSession:
    """Select a stimulus session (hab, pretest, ecephys) to run."""
    
    selection = TTNSelectedSession(TTNSession.PRETEST)
       
    session_dropdown = ipw.Select(
        options = tuple(_.value for _ in TTNSession),
        description = 'Session',
    )
    console = ipw.Output()
    with console:
        print(f'Selected: {selection.session}')
    
    def update(change):
        if change['name'] != 'value':
            return
        if (options := getattr(change['owner'], 'options', None)) and change['new'] not in options:
            return
        if change['new'] == change['old']:
            return
        selection.__init__(str(session_dropdown.value))
        with console:
            print(f'Selected: {selection.session}')
            
    session_dropdown.observe(update)
    
    IPython.display.display(ipw.VBox([session_dropdown, console]))
    
    return selection
