import asyncio
import logging
import random
from typing import Dict, List, cast
from uuid import UUID, uuid4

from supriya.clocks import AsyncClock, ClockContext
from supriya.osc import OscMessage
from supriya.patterns import Event, NoteEvent, PatternPlayer, Priority, StopEvent
from supriya.providers import BufferProxy, OscCallbackProxy, Provider
from supriya.realtime import AsyncServer

from .analysis import AnalysisEngine, AnalysisTarget
from .buffers import BufferManager
from .config import ArchonConfig
from .patterns import PatternFactory
from .query import Database
from .synthdefs import build_online_analysis_synthdef, hdverb
from .utils import scale

logger = logging.getLogger(__name__)


class Engine:
    """
    Synthesis engine.

    Yokes together scsynth (and buffer) management, OSC and pattern event
    handlers, sample database, analysis / behavioral engine, and pattern
    emission.
    """

    def __init__(self, config: ArchonConfig):
        self.config = config
        self.is_running = False
        self.server = AsyncServer()
        self.provider = Provider.from_context(self.server)
        self.osc_callbacks: List[OscCallbackProxy] = []
        self.analysis_engine = AnalysisEngine(config)
        self.buffer_manager = BufferManager(self.provider, config.root_path)
        self.clock = AsyncClock()
        self.database = Database.new(config)
        self.pattern_factory = PatternFactory()
        self.pattern_futures: Dict[UUID, asyncio.Future] = {}
        self.pattern_players: Dict[UUID, PatternPlayer] = {}
        self.periodic_tasks: List[asyncio.Task] = []

    async def boot_server(self) -> None:
        """
        Boot scsynth, setup OSC handlers, groups and synths.
        """
        logger.info("Booting server ...")
        if self.server.is_running:
            logger.warning("Server already booted!")
            return
        await self.clock.start()
        await self.server.boot(
            input_bus_channel_count=self.config.inputs,
            output_bus_channel_count=self.config.outputs,
        )
        for address, handler in {
            "/analysis": self.on_analysis_osc_message,
            "/n_end": self.on_n_end_osc_message,
        }.items():
            self.osc_callbacks.append(
                self.provider.register_osc_callback(
                    pattern=(address,), procedure=handler
                )
            )
        async with self.provider.at():
            self.provider.add_synth(
                in_=self.config.input_bus,
                synthdef=build_online_analysis_synthdef(
                    mfcc_count=self.config.mfcc_count,
                    pitch_detection_max_frequency=self.config.pitch_detection_max_frequency,
                    pitch_detection_min_frequency=self.config.pitch_detection_min_frequency,
                ),
            )
            self.provider.add_synth(
                in_=self.config.output_bus,
                mix=0.1,
                out=self.config.output_bus,
                synthdef=hdverb,
            )
        logger.info("... server booted!")

    async def quit_server(self, graceful: bool = True) -> None:
        """
        Quit scsynth, teardown osc handlers.
        """
        logger.info("Quitting server ...")
        if not self.server.is_running:
            logger.warning("Server already quit!")
            return
        await self.stop(graceful=graceful)
        for callback in self.osc_callbacks:
            self.provider.unregister_osc_callback(callback)
        await self.server.quit()
        await self.clock.stop()
        logger.info("... server quit!")

    async def start(self, graceful: bool = True) -> None:
        """
        Start the engine.
        """
        logger.info("Starting engine ...")
        if self.is_running:
            logger.warning("Engine already started!")
            return
        self.is_running = True
        self.periodic_tasks.append(
            asyncio.get_running_loop().create_task(self.poll_analysis_engine())
        )
        logger.info("... engine started!")

    async def stop(self, graceful: bool = True) -> None:
        """
        Stop the engine.
        """
        logger.info("Stopping engine ...")
        if not self.is_running:
            logger.warning("Engine already stopped!")
            return
        self.is_running = False
        # Cancel any polling tasks
        while self.periodic_tasks:
            self.periodic_tasks.pop().cancel()
        logger.info("Stopping engine gracefully ...")
        for uuid, pattern_player in self.pattern_players.items():
            logger.info(f"Stopping pattern {pattern_player.uuid}")
            pattern_player.stop()
        if self.pattern_futures:
            logger.info(f"Waiting on pattern players: {self.pattern_futures}")
            await asyncio.wait(list(self.pattern_futures.values()))
        self.pattern_futures.clear()
        self.pattern_players.clear()
        logger.info("... engine stopped!")

    async def on_analysis_target(self, analysis_target: AnalysisTarget) -> None:
        # Query the database
        entries = self.database.query_analysis_target(analysis_target)
        if not entries:
            logger.warning("No entries found")
        # Generate a UUID
        uuid = uuid4()
        # Allocate buffers
        async with self.provider.at():
            buffers = self.buffer_manager.increment_multiple(entries, uuid)
        # Generate the pattern
        pattern = self.pattern_factory.emit(
            analysis_target, buffers, out=self.config.output_bus
        )
        # Play it
        self.pattern_players[uuid] = pattern.play(
            callback=self.on_pattern_player_callback,
            clock=self.clock,
            provider=self.provider,
            uuid=uuid,
        )
        # Save a pattern future so we can track pattern completion,
        # e.g. for managing graceful shutdown
        self.pattern_futures[uuid] = asyncio.get_running_loop().create_future()
        logger.info(f"Pattern started: {uuid}")

    async def on_analysis_osc_message(self, osc_message: OscMessage):
        logger.debug(f"/analysis received: {osc_message!r}")
        (
            _,
            _,
            peak,
            rms,
            f0,
            is_voiced,
            is_onset,
            centroid,
            flatness,
            rolloff,
            *mfcc,
        ) = osc_message.contents
        self.analysis_engine.intake(
            peak=peak,
            rms=rms,
            f0=f0,
            is_voiced=bool(is_voiced),
            is_onset=bool(is_onset),
            centroid=centroid,
            flatness=flatness,
            rolloff=rolloff,
            mfcc=mfcc,
        )

    async def on_n_end_osc_message(self, osc_message: OscMessage):
        logger.debug(f"/n_end received: {osc_message!r}")
        node_id = osc_message.contents[0]
        async with self.provider.at():
            self.buffer_manager.decrement(node_id)

    async def on_pattern_player_callback(
        self,
        player: PatternPlayer,
        context: ClockContext,
        event: Event,
        priority: Priority,
    ):
        if isinstance(event, NoteEvent) and priority == Priority.START:
            node_id = int(player._proxies_by_uuid[event.id_])
            buffer_id = cast(BufferProxy, event.kwargs.get("buffer_id"))
            logger.debug(f"Playing note: {node_id} w/ {int(buffer_id)}")
            if buffer_id is not None:
                self.buffer_manager.increment(buffer_id, node_id)
        elif isinstance(event, StopEvent):
            logger.debug(f"Pattern stopped: {player.uuid}")
            async with self.provider.at():
                self.buffer_manager.decrement(player.uuid)
            self.pattern_players.pop(player.uuid)
            self.pattern_futures.pop(player.uuid).set_result(True)

    async def poll_analysis_engine(self) -> None:
        logger.info("Starting new analysis engine poller ...")
        while self.is_running:
            logger.debug(f"{self.server.status}")
            logger.info("Polling analysis engine ...")
            analysis_target, min_sleep, max_sleep = self.analysis_engine.emit()
            # check if polyphony has capacity
            if analysis_target is not None:
                await self.on_analysis_target(analysis_target)
            else:
                logger.info("Analysis engine not yet primed")
            await asyncio.sleep(scale(random.random(), 0, 1, min_sleep, max_sleep))
        logger.info("... exiting analysis engine poller.")
