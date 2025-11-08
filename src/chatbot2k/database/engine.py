from collections.abc import Generator
from collections.abc import Iterable
from contextlib import contextmanager
from pathlib import Path
from typing import Final
from typing import Optional
from typing import final

from sqlalchemy import event
from sqlalchemy import func
from sqlalchemy.engine.interfaces import DBAPIConnection
from sqlalchemy.pool.base import ConnectionPoolEntry
from sqlmodel import Session
from sqlmodel import create_engine
from sqlmodel import select

from chatbot2k.database.tables import Broadcast
from chatbot2k.database.tables import Constant
from chatbot2k.database.tables import DictionaryEntry
from chatbot2k.database.tables import Parameter
from chatbot2k.database.tables import ParameterizedCommand
from chatbot2k.database.tables import SoundboardCommand
from chatbot2k.database.tables import StaticCommand
from chatbot2k.database.tables import Translation
from chatbot2k.models.parameterized_command import ParameterizedCommand as ParameterizedCommandModel
from chatbot2k.translation_key import TranslationKey


def create_database_url(sqlite_db_path: Path) -> str:
    return f"sqlite:///{sqlite_db_path}"


@final
class Database:
    def __init__(self, sqlite_db_path: Path, *, echo: bool = False) -> None:
        url: Final = create_database_url(sqlite_db_path)
        self._engine = create_engine(url, echo=echo)

        # Ensure SQLite enforces ON DELETE CASCADE at the DB level
        if url.startswith("sqlite"):

            @event.listens_for(self._engine, "connect")
            def _set_sqlite_pragma(dbapi_connection: DBAPIConnection, _: ConnectionPoolEntry) -> None:  # type: ignore[reportUnusedFunction]
                cursor: Final = dbapi_connection.cursor()
                try:
                    cursor.execute("PRAGMA foreign_keys=ON")
                finally:
                    cursor.close()

        # Uncomment the following line to create tables automatically if they don't exist. We use migrations instead.
        # SQLModel.metadata.create_all(self._engine)

    @contextmanager
    def _session(self) -> Generator[Session]:
        with Session(self._engine) as session:
            yield session

    def add_static_command(self, *, name: str, response: str) -> StaticCommand:
        with self._session() as s:
            existing = s.get(StaticCommand, name)
            if existing:
                raise ValueError(f"StaticCommand '{name}' already exists")
            obj = StaticCommand(name=name, response=response)
            s.add(obj)
            s.commit()
            s.refresh(obj)
            return obj

    def remove_static_command(self, *, name: str) -> None:
        with self._session() as s:
            obj = s.get(StaticCommand, name)
            if not obj:
                raise KeyError(f"StaticCommand '{name}' not found")
            s.delete(obj)
            s.commit()

    def get_static_commands(self) -> list[StaticCommand]:
        with self._session() as s:
            return list(s.exec(select(StaticCommand)).all())

    def add_parameterized_command(
        self,
        *,
        name: str,
        response: str,
        parameters: Iterable[str],
    ) -> ParameterizedCommand:
        with self._session() as s:
            if s.get(ParameterizedCommand, name):
                raise ValueError(f"ParameterizedCommand '{name}' already exists")

            cmd = ParameterizedCommand(name=name, response=response)
            seen: set[str] = set()
            for p in parameters:
                p = p.strip()
                if not p or p in seen:
                    continue
                seen.add(p)
                cmd.parameters.append(Parameter(command_name=name, name=p))

            s.add(cmd)
            s.commit()
            s.refresh(cmd)
            return cmd

    def remove_parameterized_command(self, *, name: str) -> None:
        with self._session() as s:
            cmd = s.get(ParameterizedCommand, name)
            if not cmd:
                raise KeyError(f"ParameterizedCommand '{name}' not found")
            s.delete(cmd)  # ORM delete -> cascades delete-orphan
            s.commit()

    def get_parameterized_commands(self) -> list[ParameterizedCommandModel]:
        with self._session() as s:
            return [
                ParameterizedCommandModel(
                    name=command.name,
                    response=command.response,
                    parameters=[parameter.name for parameter in command.parameters],
                )
                for command in s.exec(select(ParameterizedCommand)).all()
            ]

    def add_soundboard_command(self, *, name: str, clip_url: str) -> SoundboardCommand:
        with self._session() as s:
            if s.get(SoundboardCommand, name):
                raise ValueError(f"SoundboardCommand '{name}' already exists")
            obj = SoundboardCommand(name=name, clip_url=clip_url)
            s.add(obj)
            s.commit()
            s.refresh(obj)
            return obj

    def remove_command_case_insensitive(self, *, name: str) -> bool:
        with self._session() as s:
            for command_type in (StaticCommand, ParameterizedCommand, SoundboardCommand):
                obj = s.exec(select(command_type).where(func.lower(command_type.name) == name.lower())).one_or_none()
                if obj is not None:
                    s.delete(obj)
                    s.commit()
                    return True
            return False

    def remove_soundboard_command(self, *, name: str) -> None:
        with self._session() as s:
            obj = s.get(SoundboardCommand, name)
            if obj is None:
                raise KeyError(f"SoundboardCommand '{name}' not found")
            s.delete(obj)
            s.commit()

    def get_soundboard_commands(self) -> list[SoundboardCommand]:
        with self._session() as s:
            return list(s.exec(select(SoundboardCommand)).all())

    def add_broadcast(
        self,
        *,
        interval_seconds: int,
        message: str,
        alias_command: Optional[str] = None,
    ) -> Broadcast:
        with self._session() as s:
            obj = Broadcast(
                interval_seconds=interval_seconds,
                message=message,
                alias_command=alias_command,
            )
            s.add(obj)
            s.commit()
            s.refresh(obj)
            return obj

    def remove_broadcast(self, *, id_: int) -> None:
        with self._session() as s:
            obj = s.get(Broadcast, id_)
            if not obj:
                raise KeyError(f"Broadcast id {id_} not found")
            s.delete(obj)
            s.commit()

    def get_broadcasts(self) -> list[Broadcast]:
        with self._session() as s:
            return list(s.exec(select(Broadcast)).all())

    def add_constant(self, *, name: str, text: str) -> Constant:
        with self._session() as s:
            if s.get(Constant, name):
                raise ValueError(f"Constant '{name}' already exists")
            obj = Constant(name=name, text=text)
            s.add(obj)
            s.commit()
            s.refresh(obj)
            return obj

    def remove_constant(self, *, name: str) -> None:
        with self._session() as s:
            obj = s.get(Constant, name)
            if not obj:
                raise KeyError(f"Constant '{name}' not found")
            s.delete(obj)
            s.commit()

    def get_constants(self) -> list[Constant]:
        with self._session() as s:
            return list(s.exec(select(Constant)).all())

    def add_dictionary_entry(self, *, word: str, explanation: str) -> DictionaryEntry:
        with self._session() as s:
            if s.get(DictionaryEntry, word):
                raise ValueError(f"DictionaryEntry '{word}' already exists")
            obj = DictionaryEntry(word=word, explanation=explanation)
            s.add(obj)
            s.commit()
            s.refresh(obj)
            return obj

    def remove_dictionary_entry_case_insensitive(self, *, word: str) -> None:
        with self._session() as s:
            obj: Final = s.exec(
                select(DictionaryEntry).where(func.lower(DictionaryEntry.word) == word.lower())
            ).one_or_none()
            if obj is None:
                raise KeyError(f"DictionaryEntry '{word}' not found")
            s.delete(obj)
            s.commit()

    def get_dictionary_entry_case_insensitive(self, *, word: str) -> Optional[DictionaryEntry]:
        with self._session() as s:
            stmt = select(DictionaryEntry).where(func.lower(DictionaryEntry.word) == word.lower())
            return s.exec(stmt).one_or_none()

    def get_dictionary_entries(self) -> list[DictionaryEntry]:
        with self._session() as s:
            return list(s.exec(select(DictionaryEntry)).all())

    def add_translation(self, *, key: TranslationKey, value: str) -> Translation:
        with self._session() as s:
            if s.get(Translation, key):
                raise ValueError(f"Translation '{key}' already exists")
            obj = Translation(key=key, value=value)
            s.add(obj)
            s.commit()
            s.refresh(obj)
            return obj

    def remove_translation(self, *, key: str) -> None:
        with self._session() as s:
            obj = s.get(Translation, key)
            if not obj:
                raise KeyError(f"Translation '{key}' not found")
            s.delete(obj)
            s.commit()

    def get_translations(self) -> list[Translation]:
        with self._session() as s:
            return list(s.exec(select(Translation)).all())
