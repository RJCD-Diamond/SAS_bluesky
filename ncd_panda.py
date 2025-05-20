import os
from enum import Enum
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any

import numpy as np
from bluesky.run_engine import RunEngine
from bluesky.utils import MsgGenerator, short_uid
import bluesky.plan_stubs as bps
import bluesky.preprocessors as bpp
from pydantic import Field, NonNegativeFloat, validate_call

from dodal.log import LOGGER
from dodal.utils import make_device, make_all_devices
from dodal.common.visit import RemoteDirectoryServiceClient, StaticVisitPathProvider

from ophyd_async.plan_stubs._wait_for_awaitable import wait_for_awaitable

from ophyd_async.core import (
    DetectorTrigger,
    StandardDetector,
    StandardFlyer,
    TriggerInfo,
	wait_for_value,
	AsyncStatus,
	YamlSettingsProvider)


from ophyd_async.fastcs.panda import (
    HDFPanda,
    SeqTable,
    SeqTableInfo,
    SeqTrigger,
    StaticSeqTableTriggerLogic,
    PandaPcompDirection,
    PcompInfo,
)

from ophyd_async.plan_stubs import (apply_panda_settings, 
									retrieve_settings, 
									store_settings,
									ensure_connected, fly_and_collect)


from ophyd_async.epics.adpilatus import PilatusDetector, PilatusTriggerMode

from dodal.beamlines.i22 import saxs, waxs, i0, it, TetrammDetector, panda1
from dodal.plan_stubs.data_session import attach_data_session_metadata_decorator
from dodal.devices.oav.oav_detector import OAV

from dodal.devices.areadetector.plugins.CAM import ColorMode
from dodal.devices.oav.oav_parameters import OAVParameters

from dodal.beamlines import module_name_for_beamline

from dodal.common.beamlines.beamline_utils import (
    get_path_provider,
    set_path_provider)

from ProfileGroups import (Profile, 
                           Group, 
                           PandaTriggerConfig)


#: Buffer added to deadtime to handle minor discrepencies between detector
#: and panda clocks
DEADTIME_BUFFER = 20e-6
DEFAULT_SEQ = 1 #default sequencer is this one, pandas can have 2
PULSEBLOCKS = 4 #number of pulseblocks available for the panda, for standard panda this is 4
GENERAL_TIMEOUT = 30 #seconds before each wait times out


RE = RunEngine(call_returns_result=True) 

class PANDA(Enum):
    Enable = "ONE"
    Disable = "ZERO"


def fly_and_collect_with_wait(
    stream_name: str,
    flyer: StandardFlyer[SeqTableInfo] | StandardFlyer[PcompInfo],
    detectors: list[StandardDetector],
):
    """Kickoff, complete and collect with a flyer and multiple detectors.

    This stub takes a flyer and one or more detectors that have been prepared. It
    declares a stream for the detectors, then kicks off the detectors and the flyer.
    The detectors are collected until the flyer and detectors have completed.

    """
    yield from bps.declare_stream(*detectors, name=stream_name, collect=True)
    yield from bps.kickoff(flyer, wait=True)
    for detector in detectors:
        yield from bps.kickoff(detector)

    # collect_while_completing
    group = short_uid(label="complete")

    yield from bps.complete(flyer, wait=False, group=group)
    for detector in detectors:
        yield from bps.complete(detector, wait=False, group=group)

    done = False
    while not done:
        try:
            yield from bps.wait(group=group, timeout=0.5)
        except TimeoutError:
            pass
        else:
            done = True
        yield from bps.collect(
            *detectors,
            return_payload=False,
            name=stream_name,
        )
    yield from bps.wait(group=group)
    yield from bps.sleep(2)



def return_connected_device(beamline: str, device_name: str) -> StandardDetector:
    """
    Connect to a device on the specified beamline and return the connected device.

    Args:
        beamline (str): Name of the beamline.
        device_name (str): Name of the device to connect to.

    Returns:
        StandardDetector: The connected device.
    """
    module_name = module_name_for_beamline(beamline)
    devices = make_device(f"dodal.beamlines.{module_name}", device_name, connect_immediately=True)
    return devices[device_name]

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


def wait_until_complete(pv_obj, waiting_value=0, timeout=300):
    """
    An async wrapper for the ophyd async wait_for_value function, to allow it to run inside the bluesky run engine
    Typical use case is waiting for an active pv to change to 0, indicating that the run has finished, which then allows the
    run plan to disarm all the devices.
    """

    async def _wait():
        await wait_for_value(pv_obj, waiting_value, timeout=None)

    yield from bps.wait_for([_wait])



def set_experiment_directory(beamline: str, visit_path: Path):
    """Updates the root folder"""

    set_path_provider(
    StaticVisitPathProvider(
        beamline,
        Path(visit_path),
        client=RemoteDirectoryServiceClient(f"http://{beamline}-control:8088/api"),
        )
    )

    suffix = datetime.now().strftime("_%Y%m%d%H%M%S")

    async def set_panda_dir():
        await get_path_provider().update(directory=visit_path, suffix=suffix)

    yield from bps.wait_for([set_panda_dir])


def load_settings_from_yaml(yaml_directory: str, yaml_file_name: str):

    provider = YamlSettingsProvider(yaml_directory)
    settings = yield from wait_for_awaitable(provider.retrieve(yaml_file_name))

    return settings


def upload_modified_settings_to_panda(yaml_directory: str, yaml_file_name: str, panda: HDFPanda):

    settings = yield from retrieve_settings(provider, yaml_file_name, panda)
    yield from apply_panda_settings(settings)


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



def arm_panda_pulses(panda: HDFPanda, pulses: list = list(np.arange(PULSEBLOCKS)+1), n_seq=1, group="arm_panda"):

    """
    
    Takes a HDFPanda and a list of integers corresponding to the number of the pulse blocks.

    Iterates through the numbered pulse blocks and arms them and then waits for all to be armed.
    
    """

    # yield from wait_until_complete(panda.seq[n_seq].enable, PANDA.Enable.value)


    for n_pulse in pulses:
        yield from bps.abs_set(panda.pulse[int(n_pulse)].enable, PANDA.Enable.value, group=group)  # type: ignore

    yield from bps.wait(group=group, timeout=GENERAL_TIMEOUT)



def disarm_panda_pulses(panda: HDFPanda, pulses: list = list(np.arange(PULSEBLOCKS)+1), n_seq = 1, group="disarm_panda"):
    

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

    yield from bps.abs_set(panda.seq[n_seq].enable, PANDA.Disable.value, group=group) 
    yield from bps.wait(group=group, timeout=GENERAL_TIMEOUT)


def setup_oav(oav: OAV,  parameters: OAVParameters, group="oav_setup"):

    yield from bps.abs_set(oav.cam.color_mode, ColorMode.RGB1, group=group)
    yield from bps.abs_set(oav.cam.acquire_period, parameters.acquire_period, group=group)
    yield from bps.abs_set(oav.cam.acquire_time, parameters.exposure, group=group)
    yield from bps.abs_set(oav.cam.gain, parameters.gain, group=group)

    # zoom_level_str = f"{float(parameters.zoom)}x"
    # yield from bps.abs_set(
    #     oav.zoom_controller,
    #     zoom_level_str,
    #     wait=True,
    # )

# def setup_pilatus(pilatus: PilatusDetector, trigger_info: TriggerInfo, group="setup_pilatus"):

#     yield from bps.stage(pilatus, group=group, wait=False) #this sets the HDF capture mode to active, MUST BE DONE FIRST
#     yield from bps.prepare(pilatus, trigger_info, wait=False, group=group) ###this tells the detector how may triggers to expect and sets the CAN aquire on


# def setup_pilatus_trigger(saxs):

#     """
    
#     IF HDF capture is set to stream, and lazy and capture is on,  

#     If acquire is on then it will accept the number of triggers before dumping data.
    
#     """
        
#     # trigger_mode = yield from bps.rd(saxs.driver.trigger_mode)
#     yield from bps.abs_set(saxs.driver.trigger_mode, PilatusTriggerMode.EXT_TRIGGER)

#     print(saxs.driver)
#     # yield from bps.abs_set(saxs.driver.armed, "Armed")
#     # BL22I-EA-PILAT-01:CAM:Acquire
#     armed = yield from bps.rd(saxs.driver.armed)
#     trigger_mode = yield from bps.rd(saxs.driver.trigger_mode)
    
#     desc = saxs._metadata_holder.description


def stage_and_prepare_detectors(detectors: list, flyer: StandardFlyer, trigger_info: TriggerInfo, group="det_atm"):

    """
    
    Iterates through all of the detectors specified and prepares them.
    
    """

    yield from bps.stage_all(*detectors, flyer, group=group)

    for det in detectors:
        yield from bps.prepare(det, trigger_info, wait=False, group=group) ###this tells the detector how may triggers to expect and sets the CAN aquire on

    yield from bps.wait(group=group, timeout=GENERAL_TIMEOUT)



def return_deadtime(detectors: list, exposure=1) -> np.ndarray:

    """
    Given a list of connected detector devices, and an exposure time, it returns an array of the deadtime for each detector
    """

    deadtime = np.array(list(det._controller.get_deadtime(exposure) for det in detectors)) + DEADTIME_BUFFER
    return deadtime



def set_panda_output(panda: HDFPanda, output_type: str, output: int, state: str, group="switch"):
    """
    Set a Panda output (TTL or LVDS) to a specified state (ON or OFF).

    Args:
        panda (HDFPanda): The Panda device.
        output_type (str): Type of output ("TTL" or "LVDS").
        output (int): Output number.
        state (str): Desired state ("ON" or "OFF").
        group (str): Bluesky group name.
    """
    state_value = PANDA.Enable.value if state.upper() == "ON" else PANDA.Disable.value
    output_attr = getattr(panda, f"{output_type.lower()}out")[int(output)]
    yield from bps.abs_set(output_attr.val, state_value, group=group)
    yield from bps.wait(group=group, timeout=GENERAL_TIMEOUT)



@AsyncStatus.wrap
async def update_path():

    path_provider = get_path_provider()
    await path_provider.update()

    return path_provider


@AsyncStatus.wrap
async def return_run_number():

    path_provider = get_path_provider()
    run = await path_provider.data_session()

    return run

def generate_repeated_trigger_info(profile: Profile, max_deadtime: float, livetime: float, trigger = DetectorTrigger.CONSTANT_GATE):

    repeated_trigger_info = []

    n_triggers = [group.frames for group in profile.groups] #[3, 1, 1, 1, 1] or something
    n_cycles = profile.cycles


    for pulse_block, multiplier in enumerate(profile.multiplier):

        trigger_info = TriggerInfo(number_of_triggers=n_triggers*n_cycles, 
                                trigger=trigger, 
                                deadtime=max_deadtime,
                                livetime=duration,
                                multiplier=multiplier,
                                frame_timeout=None)

        repeated_trigger_info.append(trigger_info)

def prepare_pulses(panda: HDFPanda):
    """
    
    Takes a panda and prepares the pulses, this is the last thing to do before starting the run
    
    """

    group = "panda_pulses"
    for pulse in range(1, PULSEBLOCKS + 1):
        yield from bps.prepare(panda.pulse[pulse], group=group)

    pulse_data = yield from bps.rd(panda.seq[DEFAULT_SEQ])

    yield from bps.wait(group=group, timeout=GENERAL_TIMEOUT)





@attach_data_session_metadata_decorator()
@bpp.run_decorator()
@validate_call(config={"arbitrary_types_allowed": True})
def setup_panda(beamline: Annotated[str, "Name of the beamline to run the scan on eg. i22 or b21."], 
    experiment: Annotated[str, "Experiment name eg. cm12345. This will go into /dls/data/beamline/experiment"], 
    profile: Annotated[Profile, "Profile containing the infomation required to setup the panda, triggers, times etc"], 
    active_detector_names: Annotated[list, "List of str of the detector names, eg. saxs, waxs, i0, it"] = ["saxs","waxs"], 
    panda_name="panda1", 
    force_load=True) -> MsgGenerator:

    TRIGGER_METHOD = 'Fly' #"MANUAL"
    CONFIG_NAME = 'PandaTrigger'

    visit_path = os.path.join(f"/dls/{beamline}/data",str(datetime.now().year), experiment)
    

    LOGGER.info(f"Data will be saved in {visit_path}")
    print(f"Data will be saved in {visit_path}")

    yield from set_experiment_directory(beamline, visit_path)

    beamline_devices = make_beamline_devices(beamline)
    panda = beamline_devices[panda_name]
    
    try:
        yield from ensure_connected(panda)
    except Exception as e:
        LOGGER.error(f"Failed to connect to PandA: {e}")
        raise

    # for available_det in beamline_devices:
    #     print(available_det)

    ####################

    # v CHECK TO SEE IF THIS CAN BE PERFORMED IN A SMARTER WAY v

    active_detectors = tuple([beamline_devices[det_name] for det_name in active_detector_names]) ###must be a tuple to be hashable and therefore work with bps.stage_all or whatever
    # active_detectors = active_detectors + (panda,)
    
    ######################3

    # yield from bps.declare_stream(*active_detectors, name="main_stream", collect=True)

    print("\n",active_detectors,"\n")
    LOGGER.info("\n",active_detectors,"\n")


    for device, device_name in zip(active_detectors, active_detector_names):
        yield from ensure_connected(device)
        print(f"{device_name} is connected")

    
    detector_deadtime = return_deadtime(detectors=active_detectors, exposure=profile.duration)
    max_deadtime = max(detector_deadtime)

    for dt, dn in zip(detector_deadtime, active_detector_names):
        print(f"deadtime for {dn} is {dt}")
        LOGGER.info(f"deadtime for {dn} is {dt}")

    

    #load Panda setting to panda
    if force_load == True:
        yaml_directory = os.path.join(os.path.dirname(os.path.realpath(__file__)),"ophyd_panda_yamls")
        yaml_file_name = f"{beamline}_{CONFIG_NAME}_{panda_name}"
        print(f"{yaml_file_name}.yaml has been uploaded to PandA")
        ######### make sure correct yaml is loaded
        yield from upload_yaml_to_panda(yaml_directory=yaml_directory,yaml_file_name=yaml_file_name,panda=panda)

    
    # yield from modify_panda_seq_table(panda, profile, n_seq=DEFAULT_SEQ) #this actually isn't require if a seq table flyer is applied
    active_pulses = profile.active_out+1 #because python counts from 0, but panda coutns from 1


    n_cycles = profile.cycles
    seq_table = profile.seq_table() #seq table should be grabbed from the panda and used instead, in order to decouple run from setup panda
    n_triggers = [group.frames for group in profile.groups] #[3, 1, 1, 1, 1] or something
    duration = profile.duration

    ############################################################

    # ###setup triggering of detectors
    table_info = SeqTableInfo(sequence_table=seq_table, repeats=n_cycles)

    # for pulse in PULSEBLOCKS
    #   get the pulse block, find out what is attached to it
    #   set the multiplier and possibly duration accordingly
    #   for det in detectors_on_pulse_block:
    #       trigger_info = TriggerInfo(number_of_triggers=n_triggers*n_cycles, 
    #                                   trigger=DetectorTrigger.CONSTANT_GATE, 
    #                                  deadtime=max_deadtime,
    #                                  multiplier=1,
    #                                 frame_timeout=None)

    #set up trigger info etc
    trigger_info = TriggerInfo(number_of_events = n_triggers*n_cycles, 
                            trigger=DetectorTrigger.CONSTANT_GATE, #EDGE_TRIGGER
                            deadtime=max_deadtime,
                            livetime=np.amax(profile.duration_per_cycle),
                            exposures_per_event=1,
                            frame_timeout=duration)
    

    ############################################################

    trigger_logic = StaticSeqTableTriggerLogic(panda.seq[DEFAULT_SEQ]) #flyer and prepare fly, sets the sequencers table
    flyer = StandardFlyer(trigger_logic) #flyer and prepare fly, sets the sequencers table
    # flyer = StandardFlyer(StaticSeqTableTriggerLogic(panda.seq[n_seq])) #flyer and prepare fly, sets the sequencers table


    # ####stage the detectors, the flyer, the panda
    
    yield from bps.prepare(flyer, table_info, wait=False) #setup triggering on panda - changes the sequence table
    yield from stage_and_prepare_detectors(active_detectors, flyer, trigger_info) ###change the sequence table

    # yield from prepare_pulses(panda))


    # ###### ^ this is the last thing setting up the panda
    
    
    ##########################
    #arm the panda pulses
    yield from arm_panda_pulses(panda=panda, pulses=active_pulses)



    if TRIGGER_METHOD == 'MANUAL':
        stream_name = 'primary'
        yield from bps.declare_stream(*active_detectors, name=stream_name, collect=True)
        yield from start_sequencer(panda=panda, n_seq=DEFAULT_SEQ)
        yield from wait_until_complete(panda.seq[DEFAULT_SEQ].active, False)
        # yield from wait_until_complete(panda.seq[DEFAULT_SEQ].active, False, GENERAL_TIMEOUT) #only use this while testing and things keep freezing

    else:

        ###########################
        yield from fly_and_collect_with_wait(
            stream_name='primary',
            detectors=active_detectors,
            flyer=flyer,
        )
        ##########################


    # dev_name = 'i0'
    # yield from save_device_to_yaml(yaml_directory= os.path.join(os.path.dirname(os.path.realpath(__file__)),"ophyd_panda_yamls"), yaml_file_name=f"{dev_name}_pv", device=active_detectors[1])

    ###########################
    ####start diabling and unstaging everything
    ####
    yield from wait_until_complete(panda.seq[DEFAULT_SEQ].active, False)
    # yield from disable_sequencer(panda=panda, n_seq=DEFAULT_SEQ, wait=True) #this can be performed by unstage flyer
    yield from disarm_panda_pulses(panda=panda, pulses=active_pulses) #start set to false because currently don't actually want to collect data
    yield from bps.unstage_all(*active_detectors, flyer)  #stops the hdf capture mode

    


    ###########################
    ###########################


def panda_triggers_detectors():

    pass




if __name__ == "__main__":


    #################################

    #notes to self
    # tetramm only works with mulitple triggers, something to do with arm_status being set to none possible.
    #when tetramm has multiple triggers eg, 2 the data shape is not 2. only every 1. It's duration is twice as long, but still 1000 samples

    #tetramm.py
    # async def prepare(self, trigger_info: TriggerInfo):
    #     self.maximum_readings_per_frame = self.maximum_readings_per_frame*sum(trigger_info.number_of_events)

    #still getting the experiment number jumping by two
    #neeed to sort out pulses on panda
    #split setup and run 



    ###################################
    # # Profile(id=0, cycles=1, in_trigger='IMMEDIATE', out_trigger='TTLOUT1', groups=[Group(id=0, frames=1, wait_time=100, wait_units='ms', run_time=100, run_units='ms', wait_pause=False, run_pause=False, wait_pulses=[1, 0, 0, 0, 0, 0, 0, 0], run_pulses=[0, 0, 0, 0, 0, 0, 0, 0])], multiplier=[1, 2, 4, 8, 16])

    default_config_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),"panda_config.yaml")
    configuration = PandaTriggerConfig.read_from_yaml(default_config_path)
    profile = configuration.profiles[1]

    # modifications made dodal Tetramm.py line 133

    RE(setup_panda("i22", "cm40643-3/bluesky", profile, active_detector_names=["saxs", "i0"], force_load=False))

    # RE(panda_triggers_detectors("i22", active_detector_names=["saxs", "i0"]))
    # def quickthing():
        
    #     settings = yield from load_settings_from_yaml(yaml_directory= os.path.join(os.path.dirname(os.path.realpath(__file__)),"ophyd_panda_yamls"), yaml_file_name="i22_PandaTrigger_panda1")
    #     print(settings["seq.1.enable"])

    #     settings["seq.1.enable"] = "ONE"


    #     print(settings["seq.1.enable"])

    #     print(type(settings))

    #     for x in settings:

    #         if ("ttl" in x) or ("lvds" in x) or ("seq" in x) or ("lut" in x):

    #             print(x, settings[x])


    # RE(quickthing())




    # connected_dev = return_connected_device('i22',dev_name)
    # print(f"{connected_dev=}")
    # RE(save_device_to_yaml(yaml_directory= os.path.join(os.path.dirname(os.path.realpath(__file__)),"ophyd_panda_yamls"), yaml_file_name=f"{dev_name}_pv", device=connected_dev))



