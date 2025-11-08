from typing import Final
from typing import NamedTuple
from typing import final


@final
class Position(NamedTuple):
    line: int
    column: int


@final
class Range(NamedTuple):
    start: Position
    end: Position


@final
class SourceLocation(NamedTuple):
    source: str
    offset: int
    length: int

    @property
    def lexeme(self) -> str:
        if self.offset >= len(self.source):
            return ""
        return self.source[self.offset : self.offset + self.length]

    @property
    def range(self) -> Range:
        lines: Final = self.source.splitlines(keepends=True)
        current_offset = 0
        start_line = 0
        start_column = 0
        end_line = 0
        end_column = 0

        for i, line in enumerate(lines):
            line_length = len(line)
            if current_offset + line_length > self.offset and start_line == 0:
                start_line = i + 1
                start_column = self.offset - current_offset + 1
            if current_offset + line_length >= self.offset + self.length:
                end_line = i + 1
                end_column = self.offset + self.length - current_offset + 1
                break
            current_offset += line_length

        return Range(
            start=Position(line=start_line, column=start_column),
            end=Position(line=end_line, column=end_column),
        )
