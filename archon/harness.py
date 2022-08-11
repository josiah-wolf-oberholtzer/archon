import asyncio
import logging
import signal
from pathlib import Path
from typing import List

import supriya

from .query import Database
from .synthdefs import analysis

logger = logging.getLogger(__name__)


class Command:
    async def do(self, harness: "Harness"):
        raise NotImplementedError


class BootCommand(Command):
    async def do(self, harness: "Harness"):
        await harness.boot()


class QuitCommand(Command):
    async def do(self, harness: "Harness"):
        await harness.quit()


class Harness:
    def __init__(self, analysis_path: Path, loop):
        self.clock = supriya.AsyncClock()
        self.command_queue: asyncio.Queue[Command] = asyncio.Queue()
        self.database = Database.new(analysis_path)
        self.exit_future = loop.create_future()
        self.osc_callbacks: List[supriya.osc.OscCallback] = []
        self.server = supriya.AsyncServer()
        self.provider = supriya.Provider.from_context(self.server)

    async def boot(self):
        logger.info("Booting ...")
        await self.server.boot()
        await self.clock.start()
        for address in ["/analysis", "/n_end"]:
            self.osc_callbacks.append(
                self.server.osc_protocol.register(
                    pattern=(address,), procedure=self.handle_osc_message
                )
            )
        async with self.provider.at():
            self.provider.add_synth(
                in_=self.server.options.output_bus_channel_count, synthdef=analysis
            )

    def handle_osc_message(self, osc_message):
        if osc_message.address == "/analysis":
            (
                _,
                _,
                peak,
                rms,
                frequency,
                is_voiced,
                centroid,
                flatness,
                rolloff,
            ) = osc_message.contents
            logger.info(
                f"P{peak:.06f} R{rms:.06f} V{int(is_voiced)} F{frequency:.03f} "
                f"C{centroid:.01f} F{flatness:.03f} R{rolloff:.01f}"
            )
        else:
            logger.info(repr(osc_message))

    async def run(self):
        def signal_handler(*args):
            async def bail():
                await self.command_queue.put(QuitCommand())

            logger.warning("Caught signal!")
            loop.create_task(bail())

        logger.info("Running harness ...")
        loop = asyncio.get_running_loop()
        loop.add_signal_handler(signal.SIGINT, signal_handler)
        loop.add_signal_handler(signal.SIGTSTP, signal_handler)
        await self.command_queue.put(BootCommand())
        while not self.exit_future.done():
            command = await self.command_queue.get()
            await command.do(self)
        logger.info("... harness done.")

    async def quit(self):
        logger.info("Quitting ...")
        await self.clock.stop()
        await self.server.quit()
        for callback in self.osc_callbacks:
            self.server.osc_protocol.unregister(callback)
        self.exit_future.set_result(True)


def run(analysis_path: Path):
    loop = asyncio.get_event_loop()
    harness = Harness(analysis_path, loop)
    loop.run_until_complete(harness.run())
