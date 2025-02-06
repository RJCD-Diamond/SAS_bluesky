from dodal.beamlines.i22 import panda1
from ophyd_async.fastcs.panda import HDFPanda
from bluesky.utils import MsgGenerator
import bluesky.plan_stubs as bps
from bluesky.run_engine import RunEngine
from dodal import cli


cli.connect(beamline="i22")
# print(panda.pulse)


def arm_panda_trigger(panda: HDFPanda, group="arm_panda_gridscan"):
    yield from bps.abs_set(panda.seq[1].enable, Enabled.ENABLED.value, group=group)  # type: ignore
    yield from bps.abs_set(panda.pulse[1].enable, Enabled.ENABLED.value, group=group)  # type: ignore
    yield from bps.abs_set(panda.counter[1].enable, Enabled.ENABLED.value, group=group)  # type: ignore
    yield from bps.abs_set(panda.pcap.arm, PcapArm.ARMED.value, group=group)  # type: ignore
    yield from bps.wait(group=group, timeout=GENERAL_TIMEOUT)
    LOGGER.info("PandA has been armed")


def disarm_panda_trigger(panda, group="disarm_panda_gridscan") -> MsgGenerator:
    yield from bps.abs_set(panda.pcap.arm, PcapArm.DISARMED.value, group=group)  # type: ignore
    yield from bps.abs_set(panda.counter[1].enable, Enabled.DISABLED.value, group=group)  # type: ignore
    yield from bps.abs_set(panda.seq[1].enable, Enabled.DISABLED.value, group=group)
    yield from bps.abs_set(panda.pulse[1].enable, Enabled.DISABLED.value, group=group)
    yield from bps.abs_set(panda.pcap.enable, Enabled.DISABLED.value, group=group)  # type: ignore
    yield from bps.wait(group=group, timeout=GENERAL_TIMEOUT)


def justreadstuff():

    i22panda = panda1()
    readback = yield from bps.rd(i22panda.seq[1])

    print(readback)



RE = RunEngine(call_returns_result=True)

RE(justreadstuff())