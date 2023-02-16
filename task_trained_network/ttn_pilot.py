import configparser
import dataclasses
import datetime
import enum
import pathlib
import threading
import time
from typing import ClassVar, Literal, NamedTuple, NoReturn, Optional, TypedDict

import IPython
import IPython.display
import ipywidgets as ipw
import np_config
import np_logging
import np_session
import np_services
import PIL.Image
import pydantic
from pyparsing import Any

import np_workflows.npxc as npxc

logger = np_logging.getLogger(__name__)

# --------------------------------------------------------------------------------------

class TTNSession(enum.Enum):
    """Enum for the different TTN sessions available, each with different param sets."""
    PRETEST = 'pretest'
    HAB_60 = 'hab 60'
    HAB_90 = 'hab 90'
    HAB_120 = 'hab 120'
    ECEPHYS = 'ecephys'

# --------------------------------------------------------------------------------------

# setup parameters ---------------------------------------------------------------------
default_ttn_params = {}


# camstim defaults ---------------------------------------------------------------------
# fetched from config file on the Stim computer
parser = configparser.RawConfigParser()
parser.read((np_config.Rig().paths['Camstim'].parent / 'config' / 'stim.cfg').as_posix())

camstim_default_config = {}
for section in parser.sections():
    camstim_default_config[section] = {}
    for k,v in parser[section].items():
        try:
            value = eval(v) # this removes comments in config and converts values to expected datatype
        except:
            continue
        else:
            camstim_default_config[section][k] = value

default_ttn_params['camstim_defaults'] = camstim_default_config

# main stimulus defaults ---------------------------------------------------------------
default_ttn_params['main'] = {}

default_ttn_params['main']['sweepstim'] = {
	    'syncsqr': True,
        'syncsqrloc': (875,550),
        'syncsqrsize': (150,150),
        'syncpulse': True,
        'syncpulseport': 1,
        'syncpulselines': [5, 6],  # frame, start/stop
        'trigger_delay_sec': 5.0,
    }
default_ttn_params['main']['movie_path'] = 'C:/ProgramData/StimulusFiles/dev/'
default_ttn_params['main']['frames_per_sec'] = 30.0         #! unused
default_ttn_params['main']['session'] = 1                   #! unused
default_ttn_params['main']['monitor'] = 'GammaCorrect30'    #! MUST CONFIRM: value used in other scripts = 'Gamma1.Luminance50'

# other parameters that vary depending on session type (pretest, hab, ecephys):

def build_session_stim_repeats(old: int, reversed: int, annotated: int) -> dict[str, dict[str, int]]:
    return {'stim_repeats': dict(old=old, reversed=reversed, annotated=annotated)}

def session_stim_repeats(session: TTNSession) -> dict[str, dict[str, int]]:
    "`'main'` key in params dict should be updated with the returned dict."
    match session:
        case TTNSession.PRETEST:
            return build_session_stim_repeats(1, 0, 0)
        case TTNSession.HAB_60:
            return build_session_stim_repeats(15, 5, 1)
        case TTNSession.HAB_90:
            return build_session_stim_repeats(20, 7, 2)
        case TTNSession.HAB_120 | TTNSession.ECEPHYS:
            return build_session_stim_repeats(25, 8, 2)
        case _:
            raise ValueError(f"Stim repeats not implemented for {session}")
        
# optotagging defaults -----------------------------------------------------------------

default_ttn_params['opto'] = {}
default_ttn_params['opto_script'] = 'C:/ProgramData/StimulusFiles/dev/opto_tagging_v2.py'

# all parameters depend on session type (pretest, hab, ecephys):

def session_opto_params(session: TTNSession, mouse: str | int | np_session.Mouse) -> dict[str, dict[str, str | list[float] | Literal['pretest', 'experiment']]]:
    "`'opto'` key in params dict should be updated with the returned dict (which will be empty for habs)."

    def opto_mouse_id(mouse_id: str | int | np_session.Mouse) -> dict[str, str]:
        return {'mouseID': str(mouse_id)}

    def opto_levels(session: TTNSession) -> dict[str, list[float]]:
        default_opto_levels: list[float] = default_ttn_params['camstim_defaults']['Optogenetics']['level_list']
        match session:
            case TTNSession.PRETEST:
                return {'level_list': [max(default_opto_levels)]}
            case TTNSession.ECEPHYS:
                return {'level_list': default_opto_levels}
            case _:
                raise ValueError(f"Opto levels not implemented for {session}")
            
    def opto_operation_mode(session: TTNSession) -> dict[str, Literal['pretest', 'experiment']]:
        match session:
            case TTNSession.PRETEST:
                return {'operation_mode': 'pretest'}
            case TTNSession.ECEPHYS:
                return {'operation_mode': 'experiment'}
            case _:
                raise ValueError(f"Opto levels not implemented for {session}")
            
    match session:
        case TTNSession.PRETEST | TTNSession.ECEPHYS:
            params = {}
            params.update(opto_mouse_id(mouse))
            params.update(opto_levels(session))
            params.update(opto_operation_mode(session))
            return params
        case TTNSession.HAB_60 | TTNSession.HAB_90 | TTNSession.HAB_120:
            return {}
        case _:
            raise ValueError(f"Opto params not implemented for {session}")
        
        
# mapping defaults ---------------------------------------------------------------------

default_ttn_params['mapping'] = {}

default_ttn_params['mapping']['monitor'] = 'Gamma1.Luminance50'
default_ttn_params['mapping']['gabor_path'] = 'gabor_20_deg_250ms.stim' #? c:/programdata/stimulusfiles/dev/
default_ttn_params['mapping']['flash_path'] = 'flash_250ms.stim'
default_ttn_params['mapping']['gabor_duration_seconds'] = 1200 
default_ttn_params['mapping']['flash_duration_seconds'] = 300 

# two alternative sweepstim paramsets from different scripts:

default_ttn_params['mapping']['sweepstim'] = {
    'syncpulse': True,
    'syncpulseport': 1,
    'syncpulselines': [4, 7],  # frame, start/stop
    'trigger_delay_sec': 0.0,
    'bgcolor': (-1,-1,-1),
    'eyetracker': False,
    'eyetrackerip': "W7DT12722", #! np.0 mon is w10dtsm112722
    'eyetrackerport': 1000,
    'syncsqr': True,
    'syncsqrloc': (0,0),
    'syncsqrfreq': 60,
    'syncsqrsize': (100,100),
    'showmouse': True
} # from dv_spontaneous_stimulus.py

default_ttn_params['mapping']['sweepstim'] = {
    
} # from a DR experiment with mapping_script_v2.py

# all parameters depend on session type (pretest, hab, ecephys):
def session_mapping_params(session: TTNSession) -> dict[str, dict[str, int]]:
    "`'mapping'` key in params dict should be updated with the returned dict (which will be empty for habs)."
    
    def mapping_duration(session: TTNSession) -> dict[str, float]:
        # 0 = full length = gabor_duration + flash_duration = maximum possible
        match session:
            case TTNSession.PRETEST:
                return {'max_total_duration_minutes': 0.5}
            case TTNSession.ECEPHYS:
                return {'max_total_duration_minutes': 10} 
            case _:
                raise ValueError(f"Mapping params not implemented for {session}")
            
    match session:
        case TTNSession.PRETEST | TTNSession.ECEPHYS:
            params = {}
            params.update(mapping_duration(session))
            return params
        case TTNSession.HAB_60 | TTNSession.HAB_90 | TTNSession.HAB_120:
            return {}
        case _:
            raise ValueError(f"Mapping params not implemented for {session}")

 
class TTNSelectedSession:
    
    common_params: ClassVar[dict] = default_ttn_params
    "Will be updated with `session_params` when a session is selected."
    
    opto_script: ClassVar[str] = 'C:/ProgramData/StimulusFiles/dev/opto_tagging_v2.py'
    
    def __init__(self, session: str | TTNSession, mouse: str | int | np_session.Mouse):
        if isinstance(session, str):
            session = TTNSession(session)
        self.session = session
        self.mouse = str(mouse)
        
    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({self.session}, {self.mouse})'
    
    @property
    def script(self) -> str:
        logger.warning(f'Using hard-coded script in notebooks directory for testing')
        # will eventually point to 'C:/ProgramData/StimulusFiles/dev/oct22_tt_stim_script.py'
        return np_config.local_to_unc(np_config.Rig().sync, pathlib.Path('oct22_tt_stim_script.py').resolve()).as_posix()
    
    @property
    def session_params(self) -> dict[Literal['main', 'camstim_defaults', 'mapping', 'opto'], dict[str, Any]]:
        params = self.common_params.copy()
        params['main'].update(session_stim_repeats(self.session))
        params['mapping'].update(session_mapping_params(self.session))
        params['opto'].update(session_opto_params(self.session, self.mouse))
        return params
    
    @property
    def opto_params(self) -> dict[str, Any]:
        return self.session_params['opto']
        
    
def stim_session_select_widget(mouse: str | int | np_session.Mouse) -> TTNSelectedSession:
    """Select a stimulus session (hab, pretest, ecephys) to run."""
    
    selection = TTNSelectedSession(TTNSession.PRETEST, mouse)
       
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
        selection.__init__(str(session_dropdown.value), mouse)
        with console:
            print(f'Selected: {selection.session}')
            
    session_dropdown.observe(update)
    
    IPython.display.display(ipw.VBox([session_dropdown, console]))
    
    return selection
