import os
from enum import Enum
from datetime import datetime

from pathlib import Path

import numpy as np

from bluesky.run_engine import RunEngine
from bluesky.utils import MsgGenerator, Msg
import bluesky.plan_stubs as bps

from ophyd_async.core import (
    DetectorTrigger,
    StandardDetector,
    StandardFlyer,
    TriggerInfo,
	wait_for_value,
	AsyncStatus,
	YamlSettingsProvider)

from ophyd_async.core import PathProvider


from ophyd_async.fastcs.panda import (
    HDFPanda,
    SeqTable,
    SeqTableInfo,
    SeqTrigger,
    StaticSeqTableTriggerLogic,
)
from ophyd_async.plan_stubs import (apply_panda_settings, 
									retrieve_settings, 
									store_settings, 
									get_current_settings, 
									apply_settings_if_different, 
									ensure_connected)

from ophyd_async.plan_stubs import (
    fly_and_collect,
)

from ophyd_async.epics.adpilatus import PilatusTriggerMode

from dodal.beamlines.i22 import saxs, waxs, i0, it, TetrammDetector, panda1


from dodal.beamlines import module_name_for_beamline
from dodal.utils import make_device, make_all_devices

from dodal.common.beamlines.beamline_utils import (
    get_path_provider,
    set_path_provider,
)

from ProfileGroups import (Profile, 
                           Group, 
                           PandaTriggerConfig, time_units)

from dodal.plan_stubs.data_session import attach_data_session_metadata_wrapper

from dodal.common.visit import RemoteDirectoryServiceClient, StaticVisitPathProvider


#: Buffer added to deadtime to handle minor discrepencies between detector
#: and panda clocks
DEADTIME_BUFFER = 20e-6
DEFAULT_SEQ = 1 
PULSEBLOCK = 4
GENERAL_TIMEOUT = 10


RE = RunEngine(call_returns_result=True) 

class PANDA(Enum):
    Enable = "ONE"
    Disable = "ZERO"


def return_connected_device(beamline: str, device_name: str) -> StandardDetector:

    """

    Takes the name of the beamline, and the name of the device, connects to it immediately and returns a connected device
    
    Stalls inside run engine, for that use make_all_devices or don't connect immediately
    
    """
	
    module_name = module_name_for_beamline(beamline)
    devices = make_device(f"dodal.beamlines.{module_name}", device_name, connect_immediately=True)
    connected_device = devices[device_name]

    return connected_device

def return_module_name(beamline: str) -> str:
    """
    Takes the name of a beamline, and returns the name of the Dodal module where all the devices for that module are stored
    """
    
    module_name = module_name_for_beamline(beamline)
    return f"dodal.beamlines.{module_name}"


def make_beamline_devices(beamline: str) -> list:
    """
    Takes the name of a beamline and async creates all the devices for a beamline, whether they are connected or not. 
    """

    module = return_module_name(beamline)
    beamline_devices = make_all_devices(module)[0]

    return beamline_devices


def wait_until_complete(pv_obj, waiting_value=0, timeout=None) -> MsgGenerator:
    """
    An async wrapper for the ophyd async wait_for_value function, to allow it to run inside the bluesky run engine
    Typical use case is waiting for an active pv to change to 0, indicating that the run has finished, which then allows the
    run plan to disarm all the devices.
    """

    async def _wait():
        await wait_for_value(pv_obj, waiting_value, timeout=None)

    yield from bps.wait_for([_wait])



def set_panda_directory(panda_directory: Path) -> MsgGenerator:
    """Updates the root folder"""

    suffix = datetime.now().strftime("_%Y%m%d%H%M%S")

    async def set_panda_dir():
        await get_path_provider().update(directory=panda_directory, suffix=suffix)

    yield from bps.wait_for([set_panda_dir])




def upload_yaml_to_panda(yaml_directory: str, yaml_file_name: str, panda: HDFPanda) -> None:

    """
    
    Takes a folder of the directory where the yaml is saved, the name of the yaml file and the panda we want 

    to apply the settings to, and uploaded the ophyd async settings pv yaml to the panda
    
    """

    provider = YamlSettingsProvider(yaml_directory)
    settings = yield from retrieve_settings(provider, yaml_file_name, panda)
    yield from apply_panda_settings(settings)
	


def save_device_to_yaml(yaml_directory: str, yaml_file_name: str, device) -> MsgGenerator:

    """
    
    Takes a folder of the directory where the yaml will be saved, the name of the yaml file and the panda we want 

    then saves the ophyd async pv yaml to the given path
    
    """

    provider = YamlSettingsProvider(yaml_directory)
    yield from store_settings(provider, yaml_file_name, device)



def modify_panda_seq_table(panda: HDFPanda, profile: Profile, n_seq=1):

    """
    
    Modifies the panda sequencer table, the default sequencer table to modify is the first one.

    Takes the panda and a Profile and then uses this to apply the sequencer table
    
    """

    seq_table = profile.seq_table()
    n_cycles = profile.cycles
    time_unit = profile.best_time_unit
    

    group = "modify-seq"
    # yield from bps.stage(panda, group=group) ###maybe need this
    yield from bps.abs_set(panda.seq[int(n_seq)].table, seq_table, group=group)
    yield from bps.abs_set(panda.seq[int(n_seq)].repeats, n_cycles, group=group)
    yield from bps.abs_set(panda.seq[int(n_seq)].prescale, 1, group=group)
    yield from bps.abs_set(panda.seq[int(n_seq)].prescale_units, 's', group=group)
    yield from bps.wait(group=group, timeout=GENERAL_TIMEOUT)


def set_pulses(panda: HDFPanda, n_pulse: int, pulse_step: int, frequency_multiplier: int, step_units="ms", width_unit="ms"):

    group = "modify-pulse"
    # yield from bps.abs_set(panda.pulse[int(n_pulse)].trig_edge, "Rising", group=group)
    yield from bps.abs_set(panda.pulse[int(n_pulse)].delay, 0, group=group)
    yield from bps.abs_set(panda.pulse[int(n_pulse)].width, 1, group=group)
    yield from bps.abs_set(panda.pulse[int(n_pulse)].width_units, width_unit, group=group)
    yield from bps.abs_set(panda.pulse[int(n_pulse)].pulses, frequency_multiplier, group=group)
    yield from bps.abs_set(panda.pulse[int(n_pulse)].step, pulse_step, group=group)
    yield from bps.abs_set(panda.pulse[int(n_pulse)].step_units, step_units, group=group)
    yield from bps.wait(group=group, timeout=GENERAL_TIMEOUT)



def arm_panda_pulses(panda: HDFPanda, pulses: list = [1,2,3,4], n_seq=1, group="arm_panda")  -> MsgGenerator:

    """
    
    Takes a HDFPanda and a list of integers corresponding to the number of the pulse blocks.

    Iterates through the numbered pulse blocks and arms them and then waits for all to be armed.
    
    """

    # yield from wait_until_complete(panda.seq[n_seq].enable, PANDA.Enable.value)


    for n_pulse in pulses:
        yield from bps.abs_set(panda.pulse[int(n_pulse)].enable, PANDA.Enable.value, group=group)  # type: ignore

    yield from bps.wait(group=group, timeout=GENERAL_TIMEOUT)



def disarm_panda_pulses(panda: HDFPanda, pulses: list = [1,2,3,4], n_seq = 1, group="disarm_panda") -> MsgGenerator:
    

    """
    
    Takes a HDFPanda and a list of integers corresponding to the number of the pulse blocks.

    Iterates through the numbered pulse blocks and disarms them and then waits for all to be disarmed.
    
    """


    for n_pulse in pulses:
        yield from bps.abs_set(panda.pulse[n_pulse].enable, PANDA.Disable.value, group=group)

    yield from bps.wait(group=group, timeout=GENERAL_TIMEOUT)



def start_sequencer(panda: HDFPanda, n_seq: int = 1, group="start"):


    """
    
    Takes an HDFPanda, the number of the sequencer block and sets the sequencer block to enable, waits for it to complete and then if

    conintuous is not True, it will wait for the sequnce to finish and disable the sequencer
    
    """

    yield from bps.abs_set(panda.seq[n_seq].enable, PANDA.Enable.value, group=group)  # type: ignore
    yield from bps.wait(group=group, timeout=GENERAL_TIMEOUT) 
    yield from wait_until_complete(panda.seq[DEFAULT_SEQ].active, True) #even though the signal might be sent it may not actually have happened yet, so so until it's true before continuing



def disable_sequencer(panda: HDFPanda, n_seq: int = 1,  wait: bool = False, group="stop"):

    """
    
    Disables the HDFPanda sequencer block.

    Takes an HDF panda and the number fo the sequencer block
    
    """

    if wait:
        yield from wait_until_complete(panda.seq[n_seq].active, False) #wait for this value to be true

    yield from bps.abs_set(panda.seq[n_seq].enable, PANDA.Disable.value, group=group, GENERAL_TIMEOUT) 
    yield from bps.wait(group=group, timeout=GENERAL_TIMEOUT)



def prepare_and_stage_detectors(detectors: list, max_deadtime: float,  profile: Profile, panda: HDFPanda, n_seq = 1, group="det_atm"):

    """
    
    Iterates through all of the detectors specified and prepares them.
    
    """

    n_cycles = profile.cycles
    seq_table = profile.seq_table()
    n_triggers = [group.frames for group in profile.groups] #[3, 1, 1, 1, 1] or something
    duration = profile.duration

    # ###setup triggering of detectors
    table_info = SeqTableInfo(sequence_table=seq_table, repeats=n_cycles)


    # trigger_info = TriggerInfo(number_of_triggers=n_triggers*n_cycles, 
    #                             trigger=DetectorTrigger.CONSTANT_GATE, 
    #                             deadtime=max_deadtime,
    #                             multiplier=1,
    #                             frame_timeout=None)
    
    trigger_info = TriggerInfo(number_of_triggers=n_triggers*n_cycles, 
                            trigger=DetectorTrigger.CONSTANT_GATE, 
                            deadtime=max_deadtime,
                            livetime=duration,
                            multiplier=1,
                            frame_timeout=None)


    flyer = StandardFlyer(StaticSeqTableTriggerLogic(panda.seq[n_seq])) #flyer and prepare fly, sets the sequencers table

    for det in detectors:

        if 'Tetramm' in str(type(det)):
            print("Tetramm is currently freezing it")
            continue

        yield from bps.stage(det, group=group,wait=False) #this sets the HDF capture mode to active, MUST BE DONE FIRST
        yield from bps.prepare(det, trigger_info, wait=False, group=group) ###this tells the detector how may triggers to expect and sets the CAN aquire on


    # yield from bps.prepare(panda, trigger_info, wait=True, group=group)
    yield from bps.prepare(flyer, table_info, wait=True, group=group)
    yield from bps.wait(group=group, timeout=GENERAL_TIMEOUT)

    return flyer



def return_deadtime(detectors: list, exposure=1) -> np.ndarray:

    """
    Given a list of connected detector devices, and an exposure time, it returns an array of the deadtime for each detector
    """

    deadtime = np.array(list(det._controller.get_deadtime(exposure) for det in detectors)) + DEADTIME_BUFFER
    return deadtime



def switch_output(panda: HDFPanda, output_type="TTL", output=1, onoff='ON', group="switch"):

    """
    
    Manual set an output to high or low. This will destroy the links between panda blocks, so any profile will need to be reloaded

    in order to use the outputs again in a panda wiring
    
    """

    output_type = output_type.upper()
    onoff = onoff.upper()

    if onoff == "ON":

        if (output_type == "TTL"):
            yield from bps.abs_set(panda.ttlout[int(output)].val, PANDA.Enable.value, group=group)
        elif output_type == "LVDS":
            yield from bps.abs_set(panda.lvdsout[int(output)].val, PANDA.Enable.value, group=group)
    
    else:

        if (output_type == "TTL"):
            yield from bps.abs_set(panda.ttlout[int(output)].val, PANDA.Disable.value, group=group)
        elif output_type == "LVDS":
            yield from bps.abs_set(panda.lvdsout[int(output)].val, PANDA.Disable.value, group=group)

    yield from bps.wait(group=group, timeout=GENERAL_TIMEOUT)

@AsyncStatus.wrap
async def update_path():

    path_provider = get_path_provider()
    await path_provider.update()

    return path_provider


# @attach_data_session_metadata_wrapper
def setup_panda(beamline: str, experiment: str, profile: Profile, active_detector_names: list = ["saxs","it"], panda_name="panda1", force_load=True) -> MsgGenerator:

    yield from bps.open_run()
    
    visit_path = os.path.join("/dls/i22/data",str(datetime.now().year),experiment)
    print(f"Data will be saved in {visit_path}")

    set_path_provider(
    StaticVisitPathProvider(
        beamline,
        Path(visit_path),
        client=RemoteDirectoryServiceClient("http://i22-control:8088/api"),
        )
    )

    yield from set_panda_directory(visit_path)

    CONFIG_NAME = 'PandaTrigger'

    beamline_devices = make_beamline_devices(beamline)
    panda = beamline_devices[panda_name]
    yield from ensure_connected(panda)

    for available_det in beamline_devices:
        print(available_det)


    active_detectors = tuple([beamline_devices[det_name] for det_name in active_detector_names]) ###must be a tuple to be hashable and therefore work with bps.stage_all or whatever
    # active_detectors = active_detectors + (panda,)

    print("\n",active_detectors,"\n")

    for device, device_name in zip(active_detectors, active_detector_names):
        yield from ensure_connected(device)
        print(f"{device_name} is connected")

    
    detector_deadtime = return_deadtime(detectors=active_detectors, exposure=1)
    max_deadtime = max(detector_deadtime)

    for dt, dn in zip(detector_deadtime, active_detector_names):
        print(f"deadtime for {dn} is {dt}")
    

    #load Panda setting to panda
    if force_load == True:
        yaml_directory = os.path.join(os.path.dirname(os.path.realpath(__file__)),"ophyd_panda_yamls")
        yaml_file_name = f"{beamline}_{CONFIG_NAME}_{panda_name}"
        print(f"{yaml_file_name}.yaml has been uploaded to PandA")
        ######### make sure correct yaml is loaded
        yield from upload_yaml_to_panda(yaml_directory=yaml_directory,yaml_file_name=yaml_file_name,panda=panda)

    
    # yield from modify_panda_seq_table(panda, profile, n_seq=DEFAULT_SEQ) #this actually isn't require if a seq table flyer is applied
    active_pulses = profile.active_out+1 #because python counts from 0, but panda coutns from 1
    ###########################
    # #arm the panda
    yield from arm_panda_pulses(panda=panda, pulses=active_pulses)
    ###change the sequence table
    #set up trigger info etc
    flyer = yield from prepare_and_stage_detectors(active_detectors, max_deadtime, profile, panda)


    hdf = yield from bps.rd(panda.data.hdf_directory)
    print(hdf)

    ###########################

    # yield from fly_and_collect(
    #     stream_name='primary',
    #     detectors=active_detectors,
    #     flyer=flyer,
    # )


    
    ###########################
    ###########################
    #arm the detectors we want to use
    yield from start_sequencer(panda=panda, n_seq=DEFAULT_SEQ)
    ###########################
    ###########################



    ###########################
    ###########################
    #wait for the sequencer table to finish before continuing
    yield from wait_until_complete(panda.seq[DEFAULT_SEQ].active, False, GENERAL_TIMEOUT)
    ###########################
    ###########################


    ###########################
    ####start diabling and unstaging everything
    ####
    yield from disable_sequencer(panda=panda, n_seq=DEFAULT_SEQ, wait=True)
    yield from disarm_panda_pulses(panda=panda, pulses=active_pulses) #start set to false because currently don't actually want to collect data
    yield from bps.unstage_all(active_detectors)  #stops the hdf capture mode
    yield from bps.close_run()
    ###########################
    ###########################


def setup_pilatus_trigger(saxs):

    """
    
    IF HDF capture is set to stream, and lazy and capture is on,  

    If acquire is on then it will accept the number of triggers before dumping data.
    
    """
        
    # trigger_mode = yield from bps.rd(saxs.driver.trigger_mode)
    yield from bps.abs_set(saxs.driver.trigger_mode, PilatusTriggerMode.EXT_TRIGGER)

    print(saxs.driver)
    # yield from bps.abs_set(saxs.driver.armed, "Armed")
    # BL22I-EA-PILAT-01:CAM:Acquire
    armed = yield from bps.rd(saxs.driver.armed)
    trigger_mode = yield from bps.rd(saxs.driver.trigger_mode)
    
    desc = saxs._metadata_holder.description





if __name__ == "__main__":



    # # Profile(id=0, cycles=1, in_trigger='IMMEDIATE', out_trigger='TTLOUT1', groups=[Group(id=0, frames=1, wait_time=100, wait_units='ms', run_time=100, run_units='ms', wait_pause=False, run_pause=False, wait_pulses=[1, 0, 0, 0, 0, 0, 0, 0], run_pulses=[0, 0, 0, 0, 0, 0, 0, 0])], multiplier=[1, 2, 4, 8, 16])

    default_config_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),"panda_config.yaml")
    configuration = PandaTriggerConfig.read_from_yaml(default_config_path)
    profile = configuration.profiles[0]
    seq_table = profile.seq_table()
    cycles = profile.cycles





    RE(setup_panda("i22", "cm40643-2/bluesky", profile, force_load=False))



