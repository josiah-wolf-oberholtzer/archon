import asyncio
import logging
from pathlib import Path
from typing import Dict, List
from uuid import UUID, uuid4

from supriya.clocks import AsyncClock, ClockContext
from supriya.osc import OscMessage
from supriya.patterns import Event, NoteEvent, PatternPlayer, Priority, StopEvent
from supriya.providers import OscCallbackProxy, Provider
from supriya.realtime import AsyncServer

from .analysis import AnalysisEngine
from .buffers import BufferManager
from .ephemera import AnalysisTarget
from .patterns import PatternFactory
from .query import Database
from .synthdefs import analysis

logger = logging.getLogger(__name__)


class Engine:
    """
    Synthesis engine.

    Yokes together scsynth (and buffer) management, OSC and pattern event
    handlers, sample database, analysis / behavioral engine, and pattern
    emission.
    """

    def __init__(self, analysis_path: Path):
        self.is_running = False
        self.server = AsyncServer()
        self.provider = Provider.from_context(self.server)
        self.osc_callbacks: List[OscCallbackProxy] = []
        self.analysis_engine = AnalysisEngine()
        self.buffer_manager = BufferManager(self.provider, analysis_path.parent)
        self.clock = AsyncClock()
        self.database = Database.new(analysis_path)
        self.pattern_factory = PatternFactory()
        self.pattern_futures: Dict[UUID, asyncio.Future] = {}
        self.pattern_players: Dict[UUID, PatternPlayer] = {}
        self.periodic_tasks: List[asyncio.Task] = []

    async def boot_server(self) -> None:
        """
        Boot scsynth, setup OSC handlers, groups and synths.
        """
        if self.server.is_running:
            return
        logger.info("Booting scsynth ...")
        await self.server.boot()
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
                in_=self.server.options.output_bus_channel_count, synthdef=analysis
            )

    async def quit_server(self, graceful: bool = True) -> None:
        """
        Quit scsynth, teardown osc handlers.
        """
        if not self.server.is_running:
            return
        await self.stop(graceful=graceful)
        logger.info("Quitting scsynth ...")
        for callback in self.osc_callbacks:
            self.provider.unregister_osc_callback(callback)
        await self.server.quit()

    async def start(self, graceful: bool = True) -> None:
        """
        Start the engine.
        """
        if self.is_running:
            return
        self.is_running = True
        await self.clock.start()
        self.periodic_tasks.append(
            asyncio.get_running_loop().create_task(self.poll_analysis_engine())
        )

    async def stop(self, graceful: bool = True) -> None:
        """
        Stop the engine.
        """
        if not self.is_running:
            return
        self.is_running = False
        self.periodic_tasks.clear()  # Lose references to periodic task
        if not graceful:
            for pattern_player in self.pattern_players.values():
                pattern_player.stop()
        await asyncio.wait(list(self.pattern_futures.values()))
        await self.clock.stop()
        self.pattern_futures.clear()
        self.pattern_players.clear()

    async def on_analysis_target(self, analysis_target: AnalysisTarget) -> None:
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
        self.pattern_players[uuid] = pattern.play(
            callback=self.on_pattern_player_callback,
            clock=self.clock,
            provider=self.provider,
            uuid=uuid,
        )
        self.pattern_futures[uuid] = asyncio.get_running_loop().create_future()

    async def on_analysis_osc_message(self, osc_message, OscMessage):
        self.analysis_engine.intake(
            peak=osc_message.contents[2],
            rms=osc_message.contents[3],
            f0=osc_message.contents[4],
            is_voiced=bool(osc_message.contents[5]),
            is_onset=bool(osc_message.contents[6]),
            centroid=osc_message.contents[7],
            flatness=osc_message.contents[8],
            rolloff=osc_message.contents[9],
        )

    async def on_n_end_osc_message(self, osc_message: OscMessage):
        node_id = osc_message.contents[0]
        self.buffer_manager.decrement(node_id)

    async def on_pattern_player_callback(
        self,
        player: PatternPlayer,
        context: ClockContext,
        event: Event,
        priority: Priority,
    ):
        if isinstance(event, NoteEvent) and priority == Priority.START:
            buffer_id = event.kwargs.get("buffer_id")
            if buffer_id is not None:
                self.buffer_manager.increment(
                    buffer_id, player._proxies_by_uuid[event.id_]
                )
        elif isinstance(event, StopEvent):
            self.buffer_manager.decrement(player.uuid)
            self.pattern_players.pop(player.uuid)
            self.pattern_futures.pop(player.uuid).set_result(True)

    async def poll_analysis_engine(self) -> None:
        while self.is_running:
            # check if polyphony has capacity
            # check if analysis engine will emit
            await asyncio.sleep(1)
