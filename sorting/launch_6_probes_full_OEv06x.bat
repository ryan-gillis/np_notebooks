ECHO off

set session_name=%1
set probe_letters=%2

set session_name_probe_list=%session_name% %probe_letters%
echo Session, probes: %session_name_probe_list%

title 6 probe sorting 
ECHO navigating to code directory
cd C:\Users\svc_neuropix\Documents\GitHub\ecephys_spike_sorting
ECHO activating environment and starting ecephys_spike_sorting\scripts\full_from_extraction.py
call "C:\Users\svc_neuropix\Anaconda3\Scripts\activate.bat" "C:\Users\svc_neuropix\Anaconda3"
call conda activate sorting
call python ecephys_spike_sorting\scripts\full_from_extraction.py %session_name_probe_list%
cmd \k