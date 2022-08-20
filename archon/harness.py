import asyncio
import logging
import signal
from pathlib import Path
from typing import List
from uuid import uuid4

import supriya

from .analysis import AnalysisEngine
from .buffers import BufferManager
from .ephemera import AnalysisTarget
from .patterns import PatternFactory
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
        await harness.stop()
        await harness.quit()


class StartCommand(Command):
    async def do(self, harness: "Harness"):
        await harness.start()


class StopCommand(Command):
    async def do(self, harness: "Harness"):
        await harness.stop()


class RestartCommand(Command):
    async def do(self, harness: "Harness"):
        await harness.stop()
        await harness.start()


class Harness:
    def __init__(self, analysis_path: Path, loop):
        self.loop = loop
        self.command_queue: asyncio.Queue[Command] = asyncio.Queue()
        self.is_running = True
        self.exit_future = loop.create_future()

        self.server = supriya.AsyncServer()
        self.provider = supriya.Provider.from_context(self.server)
        self.osc_callbacks: List[supriya.osc.OscCallback] = []

        self.analysis_engine = AnalysisEngine()
        self.buffer_manager = BufferManager(self.provider, analysis_path.parent)
        self.clock = supriya.AsyncClock()
        self.database = Database.new(analysis_path)
        self.pattern_factory = PatternFactory()

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

    async def boot(self):
        logger.info("Booting ...")
        await self.server.boot()
        await self.setup_scsynth_topology()
        for address, handler in {
            "/analysis": self.analysis_engine.handle_analysis_message,
            "/n_end": self.buffer_manager.handle_n_end_message,
        }.items():
            self.osc_callbacks.append(
                self.provider.register_osc_callback(
                    pattern=(address,), procedure=handler
                )
            )
        await self.clock.start()

    async def start(self):
        if self.is_running:
            return
        self.is_running = True
        self.loop.create_task(self.poll_analysis_engine())

    async def stop(self):
        if not self.is_running:
            return
        self.is_running = False

    async def quit(self):
        logger.info("Quitting ...")
        await self.clock.stop()
        for callback in self.osc_callbacks:
            self.provider.unregister_osc_callback(callback)
        await self.server.quit()
        self.exit_future.set_result(True)

    async def setup_scsynth_topology(self):
        async with self.provider.at():
            self.provider.add_synth(
                in_=self.server.options.output_bus_channel_count, synthdef=analysis
            )

    async def handle_analysis_message(self, analysis_target: AnalysisTarget):
        # Query the database
        entries = self.database.query_analysis_target(analysis_target)
        # Generate a UUID
        uuid = uuid4()
        # Allocate buffers
        async with self.provider.at():
            buffers = self.buffer_manager.increment_multiple(entries, uuid)
        # Generate the pattern
        pattern = self.pattern_factory.emit(analysis_target, buffers)
        # Play it
        pattern.play(
            callback=self.buffer_manager.handle_pattern_event,
            clock=self.clock,
            provider=self.provider,
            uuid=uuid,
        )

    async def poll_analysis_engine(self):
        while self.is_running:
            # check if polyphony has capacity
            # check if analysis engine will emit
            await asyncio.sleep(1)


def run(analysis_path: Path):
    loop = asyncio.get_event_loop()
    harness = Harness(analysis_path, loop)
    loop.run_until_complete(harness.run())
