"""
Oct'22 task-trained ephys stimuli
"""
#from psychopy import visual
from camstim import Stimulus, SweepStim
from camstim import Foraging
from camstim import Window, Warp
import numpy as np

import logging
import argparse
import json

# get params for mapping/opto/main from a single json file, specified by command line
# arg 

parser = argparse.ArgumentParser()
parser.add_argument('params_path', nargs='?', type=str, default='', )
args, _ = parser.parse_known_args()

with open(args.params_path, 'r') as f:
    json_params = json.load(f)
    
# setup main stim
# -----------------------------------------------------------------------

main_params = json_params['main']

# Create display window
window = Window(fullscr=True,
                monitor=main_params['monitor'], #MUST CONFIRM: value used in other scripts = 'Gamma1.Luminance50'
                screen=0,
                warp=Warp.Disabled
                )

movie_path = main_params['movie_path']

session = main_params['session']                    #! unused

old, reversed, annotated = (main_params['stim_repeats'][key] for key in ('old', 'reversed', 'annotated'))
segment_secs = (
    [('old_stim.stim', 40)] * old + 
    [('shuffle_reversed.stim', 40), ('shuffle_reversed_1st.stim', 40), ('shuffle_reversed_2nd.stim', 40),] * reversed + 
    [('densely_annotated_%02d.stim'%i, 60) for i in range(19)] * annotated + 
    [('old_stim.stim', 40)] * old + 
    [('shuffle_reversed.stim', 40), ('shuffle_reversed_1st.stim', 40), ('shuffle_reversed_2nd.stim', 40),] * reversed
)

num_segments = len(segment_secs)

frames_per_sec = main_params['frames_per_sec']      #! unused

#build the stimulus array
stim = []
total_movie_sec = 0

for file, length in segment_secs:
    segment = Stimulus.from_file(movie_path+file, window)
    segment_ds = [(total_movie_sec,total_movie_sec+length)]
    segment.set_display_sequence(segment_ds)
    
    total_movie_sec += length
    stim.append(segment)

# create SweepStim instance
main_stim = SweepStim(window,
               stimuli=stim,
               pre_blank_sec=2,
               post_blank_sec=2,
               params=main_params['sweepstim'],
               )

# add in foraging so we can track wheel, potentially give rewards, etc
f = Foraging(window=window,
             auto_update=False,
             params=main_params['sweepstim'],
             nidaq_tasks={'digital_input': main_stim.di,
                          'digital_output': main_stim.do,})  #share di and do with SS

main_stim.add_item(f, "foraging")

# postpone running until we've set up all stim objects


# setup mapping
# ----------------------------------------------------------------------------
mapping_params = json_params['mapping'] # will be empty for some sessions

if mapping_params:
        
    """from spontaneous_stimulus_dv.py"""

    # Create display window
    mapping_window = Window(fullscr=True,
                    monitor=mapping_params['monitor'],
                    screen=0,
                    warp=Warp.Spherical,)

    # load our stimuli
    gabor = Stimulus.from_file(mapping_params['gabor_path'], mapping_window)
    flash = Stimulus.from_file(mapping_params['flash_path'], mapping_window)
    
    gabor_duration_sec = mapping_params['gabor_duration_seconds'] 
    flash_duration_sec = mapping_params['flash_duration_seconds']
    
    # if max total duration is set, and less than original movie length, cut down display sequence:
    max_mapping_duation_minutes = mapping_params["max_total_duration_minutes"] # can be zero, in which case we use the full movie length
    max_mapping_duration_sec = max_mapping_duation_minutes * 60
    if 0 < max_mapping_duration_sec < (gabor_duration_sec + flash_duration_sec):
        
        logging.debug("Mapping duration capped at %s minutes", max_mapping_duation_minutes)
        
        original_duration_sec = gabor_duration_sec + flash_duration_sec
        
        gabor_duration_sec = int((gabor_duration_sec / original_duration_sec) * max_mapping_duration_sec)
        flash_duration_sec = int((flash_duration_sec / original_duration_sec) * max_mapping_duration_sec)
        
    gabor.set_display_sequence([(0, gabor_duration_sec)])
    flash.set_display_sequence([(gabor_duration_sec, gabor_duration_sec + flash_duration_sec)])

    # create SweepStim instance
    mapping_stim = SweepStim(
            mapping_window,
            stimuli=[gabor, flash],
            pre_blank_sec=10,
            post_blank_sec=10,
            params=mapping_params,
        )

    # add in foraging so we can track wheel, potentially give rewards, etc
    f = Foraging(window=mapping_window,
                auto_update=False,
                params=mapping_params,
                nidaq_tasks={'digital_input': mapping_stim.di,
                            'digital_output': mapping_stim.do,})  #share di and do with SS
    
    mapping_stim.add_item(f, "foraging")
    #! equivalent line in mapping_script_v2.py uses 'behavior' instead of 'foraging':
    # ss.add_item(f, 'behavior')  # makes our output structure items:behavior:...
    

# -----------------------------------------------------------------------------------------
# run stims

if mapping_params:
    mapping_stim.run()

main_stim.run()
