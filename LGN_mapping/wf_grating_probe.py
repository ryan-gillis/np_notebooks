
"""
Wide-field gratings to run while probing areas
"""

import argparse
import json
import logging
import os
import time

import numpy as np
from camstim import Foraging, Stimulus_v2, SweepStim_v2, Warp, Window
from psychopy import visual

# get params ------------------------------------------------------------------
# stored in json file -
# path to json supplied by camstim via command line arg when this script is called

parser = argparse.ArgumentParser()
parser.add_argument(
    "params_path",
    nargs="?",
    type=str,
    default="",
)
args, _ = parser.parse_known_args()

with open(args.params_path, "r") as f:
    json_params = json.load(f)

# Create display window
# ----------------------------------------------------------------------------
window = Window(
    fullscr=True,
    monitor="Gamma1.Luminance50",
    screen=0,
    warp=Warp.Spherical,
)

# patch the Stimulus_v2 class to return empty dict for package()
# ----------------------------------------------------------------------------
class Stimulus_v2_MinusFrameArrays(Stimulus_v2):

    def __init__(self, *args, **kwargs):
        super(Stimulus_v2_MinusFrameArrays, self).__init__(*args, **kwargs)

    def package(self):
        return {}
    
# ----------------------------------------------------------------------------
# setup mapping stim

grating_params = json_params["wf_grating"] 
sweep_params = grating_params["sweep_params"]
for key in sweep_params:
    if not isinstance(sweep_params[key], list):
        sweep_params[key] = [sweep_params[key]]
        
wf_gratings = Stimulus_v2_MinusFrameArrays(
    visual.GratingStim(
        window,
        units='deg',
        size=grating_params['size'],
        mask=grating_params['mask'],
        texRes=256,
        sf=None,
    ),
    sweep_params={
        'Pos':(sweep_params['Pos'], 0),
        'Contrast': (sweep_params['Contrast'], 4),
        'TF': (sweep_params['TF'], 1),
        'SF': (sweep_params['SF'], 2),
        'Ori': (sweep_params['Ori'], 3),
    },
    sweep_length=grating_params['sweep_length'],
    start_time=grating_params['start_time'],
    blank_length=grating_params['blank_length'],
    blank_sweeps=grating_params['blank_sweeps'],
    runs=grating_params['runs'],
    shuffle=grating_params['shuffle'],
    save_sweep_table=False,
    )

# create SweepStim_v2 instance for stimulus and run
ss = SweepStim_v2(
    window,
    stimuli=[wf_gratings],
    pre_blank_sec=0,
    post_blank_sec=0,
    params={},
)
ss.run()