"""
For reference:

["VisualBehaviorEPHYS_Task1G_v0.1.2"]["EPHYS_1_images_G_3uL_reward"]["parameters"] = {
  'task_id': 'DoC',
  'catch_frequency': None,
  'failure_repeats': 5,
  'reward_volume': 0.003,
  'volume_limit': 5.0,
  'auto_reward_vol': 0.005,
  'warm_up_trials': 3,
  'auto_reward_delay': 0.15,
  'free_reward_trials': 10000,
  'min_no_lick_time': 0.0,
  'timeout_duration': 0.3,
  'pre_change_time': 0.0,
  'stimulus_window': 6.0,
  'max_task_duration_min': 60.0,
  'periodic_flash': [0.25, 0.5],
  'response_window': [0.15, 0.75],
  'end_after_response': True,
  'end_after_response_sec': 3.5,
  'change_time_dist': 'geometric',
  'change_time_scale': 0.3,
  'change_flashes_min': 4,
  'change_flashes_max': 12,
  'start_stop_padding': 1,
  'stimulus': {'class': 'images',
    'luminance_matching_intensity': -0.46,
    'params': {'image_set': '//allen/programs/braintv/workgroups/nc-ophys/visual_behavior/image_dictionaries/Natural_Images_Lum_Matched_set_ophys_G_2019.05.26.pkl',
    'sampling': 'even'}},
  'mapping': {'flash_path': '//allen/programs/braintv/workgroups/nc-ophys/1022/replay-stim/flash_250ms.stim',
    'gabor_path': '//allen/programs/braintv/workgroups/nc-ophys/1022/replay-stim/gabor_20_deg_250ms.stim'},
  'output_dir': 'C:/ProgramData/camstim/output',
  'agent_socket': '127.0.0.1:5000',
  'stage': 'EPHYS_1_images_G_3uL_reward',
  'flash_omit_probability': 0.05,
  'max_mapping_duration_min': 35,
  'opto_params': {'operation_mode': 'experiment'}
}
"""
import contextlib
import copy
import enum
import functools
import pathlib
import re
import time
import uuid
from typing import Any, Literal, Optional, TypeAlias

import ipywidgets as ipw
import np_config
import np_logging
import np_services
import np_session
import requests

import np_workflows

logger = np_logging.getLogger()

np_workflows.elapsed_time_widget()

ScriptName: TypeAlias = Literal['mapping', 'behavior', 'replay', 'optotagging']

class Workflow(enum.Enum):
    """Enum for the different session types available .
    - can control workflow and paramater sets
    """
    PRETEST = "pretest"
    HAB = "hab"
    EPHYS = "ephys"
    
workflow_select_widget = ipw.Select(options=Workflow._member_names_, description='Workflow:')

class VBNMixin:
    """Provides project-specific methods and attributes, mainly related to camstim scripts."""
    
    workflow: Workflow
    """Enum for particular workflow/session, e.g. PRETEST, HAB_60, HAB_90,
    EPHYS."""
    
    session: np_session.PipelineSession
    mouse: np_session.Mouse
    user: np_session.User
    platform_json: np_session.PlatformJson
    
    commit_hash = 'ec22b933faf026cbecc8ec94cf6e758dc3c1604e'

    task_id = 'replay'
        
    @property
    def script_names(self) -> tuple[ScriptName, ...]:
        if self.workflow == Workflow.HAB:
            return ('mapping', 'behavior', 'replay')
        else:
            return ('mapping', 'behavior', 'replay', 'optotagging')
    
    def get_script_content(self, script_name: str | ScriptName) -> str:
        return requests.get(
            f'http://stash.corp.alleninstitute.org/projects/VB/repos/visual_behavior_scripts/raw/replay_session/{script_name}_script.py?at={self.commit_hash}',
        ).text
        
    @functools.cached_property
    def stage_params(self) -> dict[str, Any]:
        """All parameters returned from mtrain for the mouse's current stage."""
        return self.mouse.mtrain.stage['parameters'] | {'replay_id': self.foraging_id}

    @property
    def ephys_day(self) -> int:
        stage_name: str = self.mouse.mtrain.stage['name']
        match = re.search("(?<=day\_)([0-9])", stage_name.lower())
        if match is None:
            raise ValueError(f"Could not find ephys day in stage name: {stage_name}")
        return int(match.group(0))

    @property
    def foraging_id(self) -> str:
        """Read-only, created on first read"""
        if not getattr(self, "_foraging_id", None):
            self._foraging_id = uuid.uuid4().hex
        return self._foraging_id
    
    @property
    def behavior_params(self) -> dict[str, Any]:
        params = copy.deepcopy(self.stage_params)
        params['foraging_id'] = {
            'value': self.foraging_id,
            'inferrred': False,
        }
        params['task'] = {
            "id": self.task_id,
            "sub_id": "behavior",
            "scripts_hash": self.commit_hash,
        }
        params["mouseID"] = self.mouse.id
        if self.workflow == Workflow.PRETEST:
            params["max_task_duration_min"] = 1
        return params
    
    @property
    def replay_params(self) -> dict[str, Any]:
        """`previous_output_path` will be None until the behavior script has run."""
        params = copy.deepcopy(self.behavior_params)
        params["mouseID"] = self.mouse.id
        params["task"]["sub_id"] = "replay"
        params["previous_output_path"] = self.get_behavior_output_path()
        return params
        
    @property
    def optotagging_params(self) -> dict[str, Any]:
        params = copy.deepcopy(self.stage_params["opto_params"])
        params.setdefault("level_list", [1.0, 1.2, 1.3]) #TODO
        logger.warning("Optotagging levels need updating with non-default values")
        params["mouseID"] = str(self.mouse.id)
        if self.workflow == Workflow.PRETEST:
            params["operation_mode"] = "pretest"
        return params
        
    @property
    def mapping_params(self) -> dict[str, Any]:
        return {
            'foraging_id': self.behavior_params['foraging_id'],
            'gabor_path': self.stage_params['mapping']['gabor_path'],
            'flash_path': self.stage_params['mapping']['flash_path'],
            # "output_path": mapping_output_path,
            "mouseID": self.mouse.id,
            "task": {
                "id": self.task_id,
                "sub_id": "mapping",
                "scripts_hash": self.commit_hash,
            },
            "regimen": self.mouse.mtrain.regimen['name'],
            "stage": self.mouse.mtrain.stage['name'],
            "max_mapping_duration_min": (
                self.stage_params['max_mapping_duration_min']
                if self.workflow != Workflow.PRETEST else 1
            ),
        }
    
    def get_behavior_output_path(self) -> str | None:
        """Return the path to the latest behavior output file, if one has been created."""
        return next(
            (
                np_config.unc_to_local(p).as_posix() for p in reversed(self.stims[0].data_files) 
                if "behavior" in p.name
                and self.session.folder in p.name
            ), 
            None
        )

    def update_state(self) -> None:
        "Store useful but non-essential info."
        self.mouse.state['last_session'] = self.session.id
        self.mouse.state['last_vbn_session'] = str(self.workflow)
        
        if self.mouse == 366122:
            return
        match self.workflow:
            case Workflow.PRETEST:
                return
            case Workflow.HAB:
                self.session.project.state['latest_hab'] = self.session.id
            case Workflow.EPHYS:
                self.session.project.state['latest_ephys'] = self.session.id
                self.session.project.state['sessions'] = self.session.project.state.get('sessions', []) + [self.session.id]
    
    def log(self, message: str, weblog_name: Optional[str] = None) -> None:
        logger.info(message)
        if not weblog_name:
            weblog_name = self.workflow.name
        with contextlib.suppress(AttributeError):
            np_logging.web(f'{weblog_name.lower()}_{self.mouse}').info(message)
    
    def copy_and_rename_latest_pickle_file(self, script_name: str) -> None:
        """Make sure to run after stim.finalize()"""
        latest: pathlib.Path = self.stims[0].data_files[-1]
        latest_start_time = self.stims[0].latest_start
        if latest.stat().st_mtime < latest_start_time:
            raise FileNotFoundError(
                f"Attempting to rename {latest.name}, but its timestamp indicates it was created before the last script run."
                " The previous script either didn't complete or created a pkl file in an unknown location."
            )
        elif latest_start_time == 0:
            raise ValueError(f"latest_start_time is 0: {self.stims[0]} is not correctly logging start times.")
        new_name = f"{self.session.folder}.{script_name}.pkl"
        new = latest.with_name(new_name)
        idx = 0
        while new.exists():
            logger.debug("File %s already exists, adding suffix %s", new.name, idx)
            idx += 1
            new = new.with_stem(f"{new.stem}.{idx}")
        new.write_bytes(latest.read_bytes())
        logger.info("Copied %s to %s", latest.name, new.name)
        self.stims[0].data_files.pop()
        self.stims[0].data_files.append(new)
        if script_name == 'behavior':
            (foraging_pkl := latest.with_stem(f"{self.foraging_id}_{self.mouse.id}_behavior")).write_bytes(latest.read_bytes())
            logger.info("Copied %s to %s", latest.name, foraging_pkl.name)
            self.stims[0].data_files.append(foraging_pkl)
            
    def run_script(self, script_name: str | ScriptName) -> None:

        if script_name == 'replay' and self.get_behavior_output_path() is None:
            raise FileNotFoundError("No behavior output file found: cannot run replay script.")
        elif script_name == 'replay' :
            logger.info(f"Behavior output file found for replay: {self.get_behavior_output_path()}")
            # nothing to add, params already includes self.get_behavior_output_path()
            
        params = copy.deepcopy(getattr(self, f'{script_name.replace(" ", "_")}_params'))
        
        # add mouse and user info for MPE
        params['mouse_id'] = str(self.mouse.id)
        if script_name != "optotagging": # optotagging script doesn't accept extra args
            params['user_id'] = self.user.id if self.user else 'ben.hardcastle'
        
        np_services.ScriptCamstim.script = self.get_script_content(script_name)
        np_services.ScriptCamstim.params = params
        
        self.update_state()
        self.log(f"{script_name} started")

        np_services.ScriptCamstim.start()
        with contextlib.suppress(np_services.resources.zro.ZroError):
            while not np_services.ScriptCamstim.is_ready_to_start():
                time.sleep(1)
            
        self.log(f"{script_name} complete")

        with contextlib.suppress(np_services.resources.zro.ZroError):
            np_services.ScriptCamstim.finalize()
        self.copy_and_rename_latest_pickle_file(script_name)
        
    def run_stim_desktop_theme_script(self, selection: str) -> None:     
        np_services.ScriptCamstim.script = '//allen/programs/mindscope/workgroups/dynamicrouting/ben/change_desktop.py'
        np_services.ScriptCamstim.params = {'selection': selection}
        np_services.ScriptCamstim.start()
        while not np_services.ScriptCamstim.is_ready_to_start():
            time.sleep(0.1)

    set_grey_desktop_on_stim = functools.partialmethod(run_stim_desktop_theme_script, 'grey')
    set_dark_desktop_on_stim = functools.partialmethod(run_stim_desktop_theme_script, 'dark')
    reset_desktop_on_stim = functools.partialmethod(run_stim_desktop_theme_script, 'reset')
        
    @property
    def recorders(self) -> tuple[np_services.Service, ...]:
        """Services to be started before stimuli run, and stopped after. Session-dependent."""
        match self.workflow:
            case Workflow.PRETEST | Workflow.EPHYS:
                return (np_services.Sync, np_services.VideoMVR, np_services.OpenEphys)
            case Workflow.HAB:
                return (np_services.Sync, np_services.VideoMVR)

    @property
    def stims(self) -> tuple[np_services.Service, ...]:
        return (np_services.ScriptCamstim, )
    
    def get_previous_photodocs(self) -> tuple[pathlib.Path, ...]:
        glob_pattern = f"*_{self.mouse.id}_*/*_{self.mouse.id}_*_surface-image3-left*"
        return self.session.npexp_path.parent.glob(glob_pattern)
    
    def get_previous_photodocs_widget(self) -> ipw.Tab:
        tab = ipw.Tab()
        # For each photodoc, create a new VBox to hold the image
        for i, path in enumerate(sorted(self.get_previous_photodocs(), key=lambda p: p.stem)[:4]):
            image = ipw.Image(value=open(path, "rb").read(), format='png')
            title = ipw.Label(value=path.as_posix())
            tab.children += (ipw.VBox([title, image]),)
            tab.set_title(i, " ".join(path.stem.split("_")[1:3]))
        return tab
    
    def initialize_and_test_services(self) -> None:
        """Configure, initialize (ie. reset), then test all services."""
        
        np_services.MouseDirector.user = self.user.id
        np_services.MouseDirector.mouse = self.mouse.id

        np_services.OpenEphys.folder = self.session.folder

        np_services.NewScaleCoordinateRecorder.log_root = self.session.npexp_path
        np_services.NewScaleCoordinateRecorder.log_name = self.platform_json.path.name

        for path in (
            self.stage_params['stimulus']['params']['image_set'],
            self.stage_params['mapping']['flash_path'],
            self.stage_params['mapping']['gabor_path'],
        ):
            if not pathlib.Path(path).exists():
                raise FileNotFoundError(f"{path} doesn't exist or isn't accessible")
        
        self.configure_services()

        super().initialize_and_test_services()

    def start_recording(self) -> None:
        last_exception = Exception()
        attempts = 3
        while attempts:
            np_logging.getLogger().info('Waiting for recorders to finish processing') 
            while not all(r.is_ready_to_start() for r in self.recorders):
                time.sleep(1)
            np_logging.getLogger().info('Recorders ready')     
            try:
                super().start_recording()
            except AssertionError as exc:
                np_logging.getLogger().info('`experiment.start_recording` failed: trying again')
                attempts -= 1
                last_exception = exc              # exc only exists within the try block
            
            else:
                break
        else:
            np_logging.getLogger().error('`experiment.start_recording` failed after multiple attempts', exc_info=last_exception)
            raise last_exception
            

class Hab(VBNMixin, np_workflows.PipelineHab):
    def __init__(self, *args, **kwargs):
        self.services = (
            np_services.MouseDirector,
            np_services.Sync,
            np_services.VideoMVR,
            np_services.NewScaleCoordinateRecorder,
            np_services.SessionCamstim,
        )
        super().__init__(*args, **kwargs)


class Ephys(VBNMixin, np_workflows.PipelineEphys):
    def __init__(self, *args, **kwargs):
        self.services = (
            np_services.MouseDirector,
            np_services.Sync,
            np_services.VideoMVR,
            np_services.NewScaleCoordinateRecorder,
            np_services.SessionCamstim,
            np_services.OpenEphys,
        )
        super().__init__(*args, **kwargs)


# --------------------------------------------------------------------------------------


def new_experiment(
    mouse: int | str | np_session.Mouse,
    user: str | np_session.User,
    workflow: Workflow = Workflow.PRETEST,
) -> Ephys | Hab:
    """Create a new experiment for the given mouse and user."""
    match workflow:
        case Workflow.PRETEST | Workflow.EPHYS:
            experiment = Ephys(mouse, user)
        case Workflow.HAB:
            experiment = Hab(mouse, user)
        case _:
            raise ValueError(f"Invalid workflow type: {workflow}")
    experiment.workflow = workflow
    
    with contextlib.suppress(Exception):
        np_logging.web(f'vbn_{experiment.workflow.name.lower()}').info(f"{experiment} created")
            
    return experiment

