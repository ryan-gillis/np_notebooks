"""
Oct'22 task-trained ephys stimuli
"""
#from psychopy import visual
from camstim import Stimulus, SweepStim
from camstim import Foraging
from camstim import Window, Warp
import numpy as np

import argparse
import json

parser = argparse.ArgumentParser()
parser.add_argument('params_path', nargs='?', type=str, default='', )
args, _ = parser.parse_known_args()

with open(args.params_path, 'r') as f:
    json_params = json.load(f)
    
# setup main stim ----------------------------------------------------------------------

# Create display window
window = Window(fullscr=True,
                monitor='GammaCorrect30', #MUST CONFIRM: value in `change_detection_extended` = 'Gamma1.Luminance50'
                screen=0,
                warp=Warp.Disabled
                )

movie_path = 'C:\\ProgramData\\StimulusFiles\\dev\\'

session = 1

old, reversed, annotated = (json_params['stim_repeats'][key] for key in ('old', 'reversed', 'annotated'))
segment_secs = (
    [('old_stim.stim', 40)]*old + 
    [('shuffle_reversed.stim', 40), ('shuffle_reversed_1st.stim', 40), ('shuffle_reversed_2nd.stim', 40),]*reversed + 
    [('densely_annotated_%02d.stim'%i, 60) for i in range(19)] * annotated + 
    [('old_stim.stim', 40)]*old + 
    [('shuffle_reversed.stim', 40), ('shuffle_reversed_1st.stim', 40), ('shuffle_reversed_2nd.stim', 40),]*reversed
)

num_segments = len(segment_secs)

#build the stimulus array
frames_per_sec = 30.0
stim = []
total_movie_sec = 0

for file, length in segment_secs:
    segment = Stimulus.from_file(movie_path+file, window)
    segment_ds = [(total_movie_sec,total_movie_sec+length)]
    segment.set_display_sequence(segment_ds)
    
    total_movie_sec += length
    stim.append(segment)

params = {
	    'syncsqr': True,
        'syncsqrloc': (875,550),
        'syncsqrsize': (150,150),
        'syncpulse': True,
        'syncpulseport': 1,
        'syncpulselines': [5, 6],  # frame, start/stop
        'trigger_delay_sec': 5.0,
    }
            
# create SweepStim instance
main_stim = SweepStim(window,
               stimuli=stim,
               pre_blank_sec=2,
               post_blank_sec=2,
               params=params,
               )

# add in foraging so we can track wheel, potentially give rewards, etc
f = Foraging(window=window,
             auto_update=False,
             params=params,
             nidaq_tasks={'digital_input': main_stim.di,
                          'digital_output': main_stim.do,})  #share di and do with SS
main_stim.add_item(f, "foraging")
# postpone running until we've set up the other stim objects


# setup mapping ----------------------------------------------------------------------------
# TODO build mapping object with json_params
if not json_params.get('mapping'):
    RUN_MAPPING = False
else:
    RUN_MAPPING = True
        
    """from spontaneous_stimulus_dv.py"""

    # Create display window
    mapping_window = Window(fullscr=True,
                    monitor= 'Gamma1.Luminance50',
                    screen=0,
                    warp=Warp.Spherical,)


    # paths to our stimuli
    g20_path = 		"C:/ecephys_stimulus_scripts/gabor_20_deg_250ms.stim" # 20 minutes (1200 s)
    fl250_path =	"C:/ecephys_stimulus_scripts/flash_250ms.stim" # 5 minutes (300 s)

    # load our stimuli
    g20 = Stimulus.from_file(g20_path, mapping_window)
    fl250 = Stimulus.from_file(fl250_path, mapping_window)

    g20_ds = [(0, 1200)]
    fl250_ds = [(1200, 1500)]

    g20.set_display_sequence(g20_ds)
    fl250.set_display_sequence(fl250_ds)

    # kwargs
    mapping_params = {
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
    }

    # create SweepStim instance
    mapping_stim = SweepStim(mapping_window,
                stimuli=[g20, fl250],
                pre_blank_sec=0,
                post_blank_sec=0,
                params=mapping_params,
                )

    # add in foraging so we can track wheel, potentially give rewards, etc
    f = Foraging(window=mapping_window,
                auto_update=False,
                params=mapping_params,
                nidaq_tasks={'digital_input': mapping_stim.di,
                            'digital_output': mapping_stim.do,})  #share di and do with SS
    mapping_stim.add_item(f, "foraging")
    

# setup opto -----------------------------------------------------------------------------
# TODO 
if not json_params.get('opto'):
    RUN_OPTO = False
else:
    RUN_OPTO = True
    
# run stims

if RUN_MAPPING:
    mapping_stim.run()

main_stim.run()

if RUN_OPTO:
    pass

#