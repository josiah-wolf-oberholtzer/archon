import logging
from pathlib import Path
from typing import Dict, List, Set, Union
from uuid import UUID

from supriya.providers import BufferProxy, Provider

from .query import Entry

logger = logging.getLogger(__name__)


class BufferManager:
    def __init__(self, provider: Provider, root_path: Path):
        self.provider = provider
        self.root_path = root_path
        self.buffers_to_entities: Dict[BufferProxy, Set[Union[UUID, int]]] = {}
        self.buffers_to_entries: Dict[BufferProxy, Entry] = {}
        self.entities_to_buffers: Dict[Union[UUID, int], Set[BufferProxy]] = {}
        self.entries_to_buffers: Dict[Entry, BufferProxy] = {}

    def increment(
        self, entry_or_buffer_id: Union[Entry, BufferProxy], reference: Union[UUID, int]
    ) -> BufferProxy:
        logger.debug(f"Incrementing {reference}")
        if isinstance(entry_or_buffer_id, Entry):
            entry = entry_or_buffer_id
            if entry not in self.entries_to_buffers:
                buffer_ = self.provider.add_buffer(
                    channel_count=1,
                    file_path=self.root_path / entry.path,
                    starting_frame=entry.starting_frame,
                    frame_count=entry.frame_count,
                )
                self.buffers_to_entries[buffer_] = entry
                self.entries_to_buffers[entry] = buffer_
                buffer_id = self.entries_to_buffers[entry]
                logger.debug(f"Allocating {int(buffer_id)}")
            else:
                buffer_id = self.entries_to_buffers[entry]
                logger.debug(f"Already allocated: {int(buffer_id)}")
        else:
            buffer_id = entry_or_buffer_id
            logger.debug(f"Already allocated: {int(buffer_id)}")
        self.buffers_to_entities.setdefault(buffer_id, set()).add(reference)
        self.entities_to_buffers.setdefault(reference, set()).add(buffer_id)
        return buffer_id

    def increment_multiple(
        self, entries: List[Entry], reference: UUID
    ) -> List[BufferProxy]:
        return [self.increment(entry, reference) for entry in entries]

    def decrement(self, reference: Union[UUID, int], free=True):
        logger.debug(f"Decrementing {reference}")
        for buffer_id in self.entities_to_buffers.pop(reference):
            references = self.buffers_to_entities[buffer_id]
            references.remove(reference)
            if not references and free:
                logger.debug(f"Freeing {int(buffer_id)}")
                self.buffers_to_entities.pop(buffer_id)
                entry = self.buffers_to_entries.pop(buffer_id)
                self.entries_to_buffers.pop(entry)
                self.provider.free_buffer(buffer_id)
