from dataclasses import dataclass
from typing import List

@dataclass(frozen=True)
class HandbookSection:
    section_title: str
    chunk_ids: List[str]

@dataclass(frozen=True)
class HandbookResult:
    sections: List[HandbookSection]

    @staticmethod
    def from_handbook_structure(handbook_structure: list[dict]) -> "HandbookResult":
        sections = [
            HandbookSection(
                section_title=sec["section"],
                chunk_ids=sec["chunks"]
            )
            for sec in handbook_structure
        ]
        return HandbookResult(sections=sections)
