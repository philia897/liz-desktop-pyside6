from dataclasses import dataclass, field

@dataclass
class Shortcut:
    id: str
    hit_number: int
    shortcut: str
    application: str
    description: str
    comment: str

    searchable_text: str = field(init=False)

    def __post_init__(self):
        # Precompute and cache the lowercased searchable text
        self.searchable_text = f"{self.shortcut} {self.application} {self.description}".lower()


@dataclass
class RhythmItem:
    name: str
    value: str
    hint: str