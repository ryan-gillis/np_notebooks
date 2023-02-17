"""
Oct'22 task-trained ephys stimuli
"""

import argparse
import json
import logging
import os
import time

import numpy as np
from camstim import Foraging
# from camstim import Stimulus as Stimulus_v1
from camstim import Stimulus_v2 as Stimulus
# from camstim import SweepStim as SweepStim_v1
from camstim import SweepStim_v2 as SweepStim
from camstim import Warp, Window
from psychopy import visual

# from zro import Proxy
# agent = Proxy('localhost:5000')
# logging.info(agent.get_state())

# get params for mapping/opto/main from a single json file, specified by command line
# arg 

parser = argparse.ArgumentParser()
parser.add_argument('params_path', nargs='?', type=str, default='', )
args, _ = parser.parse_known_args()

with open(args.params_path, 'r') as f:
    json_params = json.load(f)
    
# setup mapping
# ----------------------------------------------------------------------------
mapping_params = json_params['mapping'] # will be empty for some sessions

if mapping_params:
    
    """from mapping_Script_v2.py"""

    # Create display window
    mapping_window = Window(fullscr=True,
                    monitor=mapping_params['monitor'],
                    screen=0,
                    warp=Warp.Spherical,)

    # load our stimuli
    gabor_path = 'gabor_20_deg_250ms.stim' # mapping_params['gabor_path']
    flash_path = 'flash_250ms.stim'
    gabor = Stimulus.from_file(gabor_path, mapping_window)
    flash = Stimulus.from_file(flash_path, mapping_window)
    
    gabor_duration_sec = mapping_params['gabor_duration_seconds'] 
    flash_duration_sec = mapping_params['flash_duration_seconds']
    
    original_duration_sec = gabor_duration_sec + flash_duration_sec
    # if max total duration is set, and less than original movie length, cut down display sequence:
    max_mapping_duation_minutes = mapping_params["max_total_duration_minutes"] # can be zero, in which case we use the full movie length
    max_mapping_duration_sec = max_mapping_duation_minutes * 60
    if 0 < max_mapping_duration_sec < original_duration_sec:
        
        logging.info("Mapping duration capped at %s minutes", max_mapping_duation_minutes)
        
        logging.info('original gabor duration: %s sec', gabor_duration_sec)
        logging.info('original flash duration: %s sec', flash_duration_sec)
        logging.info('max mapping duration: %s sec', max_mapping_duration_sec)
        
        gabor_duration_sec = (max_mapping_duration_sec * gabor_duration_sec) / original_duration_sec
        flash_duration_sec = (max_mapping_duration_sec * flash_duration_sec) / original_duration_sec
        
        logging.info('modified gabor duration: %s sec', gabor_duration_sec)
        logging.info('modified flash duration: %s sec', flash_duration_sec)
  
    gabor.set_display_sequence([(0, gabor_duration_sec)])
    flash.set_display_sequence([(gabor_duration_sec, gabor_duration_sec + flash_duration_sec)])
    
    # create SweepStim instance for mapping
    mapping_stim = SweepStim(
            mapping_window,
            stimuli=[gabor, flash],
            pre_blank_sec=mapping_params['pre_blank_screen_sec'], 
            post_blank_sec=mapping_params['post_blank_screen_sec'],
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
    
    mapping_stim.run()
    time.sleep(60)

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
old_sec, shuffle_sec, annotated_sec = (main_params['stim_lengths_sec'][key] for key in ('old', 'shuffle', 'annotated'))
segment_secs = (
    [('old_stim.stim', old_sec)] * old + 
    [('shuffle_reversed.stim', shuffle_sec), ('shuffle_reversed_1st.stim', shuffle_sec), ('shuffle_reversed_2nd.stim', shuffle_sec),] * reversed + 
    [('densely_annotated_%02d.stim'%i, annotated_sec) for i in range(19)] * annotated + 
    [('old_stim.stim', old_sec)] * old + 
    [('shuffle_reversed.stim', shuffle_sec), ('shuffle_reversed_1st.stim', shuffle_sec), ('shuffle_reversed_2nd.stim', shuffle_sec),] * reversed
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


# create SweepStim instance for main stimulus
main_stim = SweepStim(window,
                stimuli=stim,
                pre_blank_sec=main_params['pre_blank_screen_sec'], 
                post_blank_sec=main_params['post_blank_screen_sec'],
                params=main_params['sweepstim'],
            )  

# add in foraging so we can track wheel, potentially give rewards, etc
f = Foraging(window=window,
             auto_update=False,
             params=main_params['sweepstim'],
             nidaq_tasks={'digital_input': main_stim.di,
                          'digital_output': main_stim.do,})  #share di and do with SS

main_stim.add_item(f, "foraging")

main_stim.run()
