from pathlib import Path
from typing import Dict, List, Set, Union
from uuid import UUID

from supriya import Provider
from supriya.clocks import ClockContext
from supriya.osc import OscMessage
from supriya.patterns import Event, NoteEvent, PatternPlayer, Priority, StopEvent

from .query import Entry


class BufferManager:
    def __init__(self, provider: Provider, root_path: Path):
        self.provider = provider
        self.root_path = root_path
        self.buffers_to_entities: Dict[int, Set[Union[UUID, int]]] = {}
        self.buffers_to_entries: Dict[int, Entry] = {}
        self.entities_to_buffers: Dict[Union[UUID, int], Set[int]] = {}
        self.entries_to_buffers: Dict[Entry, int] = {}

    def increment(self, entry_or_buffer_id: Union[Entry, int], reference: UUID) -> int:
        if isinstance(entry_or_buffer_id, Entry):
            entry = entry_or_buffer_id
            if entry not in self.entries_to_buffers:
                buffer_ = self.provider.add_buffer(
                    channel_count=1,
                    file_path=self.root_path / entry.path,
                    starting_frame=entry.starting_frame,
                    frame_count=entry.frame_count,
                )
                self.buffers_to_entries[buffer_.identifier] = entry
                self.entries_to_buffers[entry] = buffer_.identifier
            buffer_id = self.entries_to_buffers[entry]
        else:
            buffer_id = entry_or_buffer_id
        self.buffers_to_entities.setdefault(buffer_id, set()).add(reference)
        self.entities_to_buffers.setdefault(reference, set()).add(buffer_id)
        return buffer_id

    def increment_multiple(self, entries: List[Entry], reference: UUID) -> List[int]:
        return [self.increment(entry, reference) for entry in entries]

    def decrement(self, reference: UUID, free=True):
        for buffer_id in self.entities_to_buffers.pop(reference):
            references = self.buffers_to_entities[buffer_id]
            references.remove(reference)
            if not references and free:
                self.buffers_to_entities.pop(buffer_id)
                entry = self.buffers_to_entries.pop(buffer_id)
                self.entries_to_buffers.pop(entry)
                self.provider.free_buffer(buffer_id)

    def handle_pattern_event(
        self,
        player: PatternPlayer,
        context: ClockContext,
        event: Event,
        priority: Priority,
    ) -> None:
        """
        Decrement pattern stops and increment note starts.
        """
        if isinstance(event, StopEvent):
            self.decrement(player.uuid)
        elif isinstance(event, NoteEvent) and priority == Priority.START:
            buffer_id = event.kwargs.get("buffer_id")
            if buffer_id is not None:
                self.increment(buffer_id, player._proxies_by_uuid[event.id_].identifier)

    def handle_node_end(self, message: OscMessage) -> None:
        """
        Decrement node ends.
        """
        self.decrement(message.contents[0])
