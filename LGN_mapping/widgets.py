import time

import ipywidgets as ipw
import np_services

SWEEP_PARAMS = ('position', 'temporal freq', 'spatial freq', 'contrast', 'orientation step')
NON_SWEEP_PARAMS = ('size', 'stim length', 'delay start', 'grey screen', 'repeats')
ODD_PARAMS = ('mask', 'shuffle')
BUTTONS = ('run',)
# 'total_duration_sec'

param_keys = {
    'position': 'Pos',
    'contrast': 'Contrast',
    'temporal freq': 'TF',
    'spatial freq': 'SF',
    'orientation': 'Ori',
    'orientation step': 'Ori',
    'size': 'size',
    'mask': 'mask',
    'stim length': 'sweep_length',
    'delay start': 'start_time',
    'grey screen': 'blank_length',
    'repeats': 'runs',
    'shuffle': 'shuffle',
}

types = {
    'position': ipw.IntSlider,
    'contrast': ipw.FloatSlider,
    'temporal freq': ipw.FloatSlider,
    'spatial freq': ipw.FloatSlider, 
    'orientation': ipw.IntSlider,
    'orientation step': ipw.IntSlider,
    'size': ipw.IntSlider,
    'mask': ipw.Dropdown,
    'stim length': ipw.FloatSlider,
    'delay start': ipw.IntSlider,
    'grey screen': ipw.FloatSlider,
    'repeats': ipw.IntSlider,
    'shuffle': ipw.Checkbox,
    'run': ipw.Button,
    }

kwargs = {
    'contrast': {'value': 1.0, 'min': 0.0, 'max': 1.0, 'step': 0.1, 'readout_format': '.1f', 'description': 'contrast', 'tooltip': 'Contrast of grating, from 0 to 1'},
    'temporal freq': {'value': 4.0, 'min': 0.0, 'max': 6.0, 'step': 0.5, 'readout_format': '.1f', 'description': 'temp freq', 'tooltip': 'Temporal frequency of grating in cycles per second'},
    'spatial freq': {'value': 0.04, 'min': 0.000, 'max': 0.05, 'step': 0.001, 'readout_format': '.3f', 'description': 'spatial freq', 'tooltip': 'Spatial frequency of grating in cycles per degree'},
    'orientation step': {'value': 60, 'min': 0, 'max': 180, 'step': 10, 'description': 'orientation step', 'tooltip': 'Step size between each grating orientation, in degrees'},
    'position': {'value': 0, 'min': -60, 'max': 60, 'step': 10, 'description': 'position', 'tooltip': 'Position of grating center on screen, in degrees from center [not sure if horiz or vertical]'},
    'size': {'value': 200, 'min': 0, 'max': 200, 'step': 1, 'description': 'size', 'tooltip': 'Size of grating in degrees'},
    'stim length': {'value': 0.5, 'min': 0.0, 'max': 60.0, 'step': 0.1, 'readout_format': '.1f', 'description': 'stim length', 'tooltip': 'Duration each grating orientation appears on screen, in seconds'},
    'delay start': {'value': 0, 'min': 0, 'max': 60, 'step': 1, 'description': 'delay start', 'tooltip': 'Delay start of stimulus by this many seconds'},
    'grey screen': {'value': 0.5, 'min': 0.0, 'max': 60.0, 'step': 0.1, 'readout_format': '.1f', 'description': 'grey screen', 'tooltip': 'Duration of grey screen between each grating'},
    'repeats': {'value': 1, 'min': 0, 'max': 10, 'step': 1, 'description': 'repeats', 'tooltip': 'Number of times to repeat each grating orientation'},
    'mask': {'options': ['none', 'circle'], 'layout': ipw.Layout(width='150px'), 'description': 'mask', 'tooltip': 'Apply a mask to the gratings'},
    'shuffle': {'value': True, 'description': 'shuffle', 'tooltip': 'Shuffle order of grating orientations'},
    'run': {'description': 'Run', 'tooltip': 'Run wide-field grating script in camstim'},
}
common_kwargs = {'disabled': False, 'continuous_update': False, 'orientation': 'vertical', 'readout': True,}

def wf_grating_widget() -> ipw.VBox:
    np_services.ScriptCamstim.initialize()
    np_services.ScriptCamstim.script = 'c:/ProgramData/StimulusFiles/dev/wf_grating_probe.py'
    
    widgets: dict[str, ipw.Widget] = {
        item: types[item](**{**kwargs[item], **common_kwargs}) for item in SWEEP_PARAMS + NON_SWEEP_PARAMS + ODD_PARAMS + BUTTONS
    }
    widget_rows = [ipw.HBox([widgets[item] for item in items]) for items in (SWEEP_PARAMS, NON_SWEEP_PARAMS, ODD_PARAMS, BUTTONS)]

    def set_button_running():
        widgets['run'].disabled = True
        widgets['run'].button_style = 'warning'
        widgets['run'].description = 'Running...'
        widgets['run'].icon = 'stop'
    
    def set_button_ready():
        widgets['run'].disabled = False
        widgets['run'].button_style = 'success'
        widgets['run'].description = 'Run'
        widgets['run'].icon = 'play'
        
    def run_stim(*args):
        set_button_running()
        np_services.ScriptCamstim.params = {
            "wf_grating": {
                "sweep_params": { # any of these can be a list
                    param_keys[item]: [widgets[item].value] 
                    if item != 'orientation step'
                    else [ori for ori in range(0, 360 - widgets[item].value, widgets['orientation step'].value)]
                    for item in SWEEP_PARAMS
                },
                **{
                    param_keys[item]: widgets[item].value 
                   for item in NON_SWEEP_PARAMS + ODD_PARAMS
                   },
                'total_duration_sec': None,
                'blank_sweeps': 0,
            },
        }
        np_services.ScriptCamstim.start()
        while not np_services.ScriptCamstim.is_ready_to_start():
            time.sleep(0.1)
        set_button_ready()

    set_button_ready()
    widgets['run'].on_click(run_stim)

    return ipw.VBox(widget_rows)