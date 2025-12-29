from collections.abc import Generator
from collections.abc import Iterable
from contextlib import contextmanager
from pathlib import Path
from typing import Final
from typing import NamedTuple
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
from chatbot2k.database.tables import Script
from chatbot2k.database.tables import ScriptStore
from chatbot2k.database.tables import SoundboardCommand
from chatbot2k.database.tables import StaticCommand
from chatbot2k.database.tables import Translation
from chatbot2k.database.tables import TwitchTokenSet
from chatbot2k.models.parameterized_command import ParameterizedCommand as ParameterizedCommandModel
from chatbot2k.translation_key import TranslationKey


@final
class ScriptStoreData(NamedTuple):
    """Data for a script store to be added to the database."""

    store_name: str
    store_json: str
    value_json: str


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
            # Handle regular commands (`StaticCommand`, `ParameterizedCommand`, `SoundboardCommand`).
            for command_type in (StaticCommand, ParameterizedCommand, SoundboardCommand):
                obj = s.exec(select(command_type).where(func.lower(command_type.name) == name.lower())).one_or_none()
                if obj is not None:
                    s.delete(obj)
                    s.commit()
                    return True

            # Handle Script commands (use `command` field instead of `name`).
            script_object: Final = s.exec(
                select(Script).where(func.lower(Script.command) == name.lower())
            ).one_or_none()
            if script_object is not None:
                s.delete(script_object)
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

    def add_script(
        self,
        *,
        command: str,
        source_code: str,
        script_json: str,
        stores: list[ScriptStoreData],
    ) -> Script:
        """Add a script command with its stores to the database.

        Args:
            command: Command name (e.g., "!hello-world")
            source_code: Original source code
            script_json: JSON representation of the `Script` Pydantic model
            stores: List of `ScriptStoreData` containing store information

        Returns:
            The created `Script` object
        """
        with self._session() as s:
            existing: Final = s.get(Script, command)
            if existing is not None:
                raise ValueError(f"Script command '{command}' already exists")

            script_object: Final = Script(
                command=command,
                source_code=source_code,
                script_json=script_json,
            )
            s.add(script_object)

            # Add all stores.
            for store_data in stores:
                store_obj = ScriptStore(
                    script_command=command,
                    store_name=store_data.store_name,
                    store_json=store_data.store_json,
                    value_json=store_data.value_json,
                )
                s.add(store_obj)

            s.commit()
            s.refresh(script_object)
            return script_object

    def get_scripts(self) -> list[Script]:
        """Get all script commands from the database."""
        with self._session() as s:
            return list(s.exec(select(Script)).all())

    def get_script(self, command: str) -> Optional[Script]:
        """Get a specific script command by name."""
        with self._session() as s:
            return s.get(Script, command)

    def remove_script(self, command: str) -> bool:
        """Remove a script command and its stores from the database.

        Returns:
            `True` if the script was removed, `False` if it didn't exist
        """
        with self._session() as s:
            script_object: Final = s.get(Script, command)
            if script_object is None:
                return False
            s.delete(script_object)  # CASCADE will delete associated stores
            s.commit()
            return True

    def get_script_store(self, *, script_command: str, store_name: str) -> Optional[ScriptStore]:
        """Get a specific script store by script command and store name."""
        with self._session() as s:
            return s.exec(
                select(ScriptStore).where(
                    ScriptStore.script_command == script_command,
                    ScriptStore.store_name == store_name,
                )
            ).one_or_none()

    def update_script_store_value(self, *, script_command: str, store_name: str, value_json: str) -> None:
        """Update the value of a script store."""
        with self._session() as s:
            store: Final = s.exec(
                select(ScriptStore).where(
                    ScriptStore.script_command == script_command,
                    ScriptStore.store_name == store_name,
                )
            ).one_or_none()

            if store is None:
                raise KeyError(f"ScriptStore '{store_name}' for script '{script_command}' not found")

            store.value_json = value_json
            s.add(store)
            s.commit()

    def add_or_update_twitch_token_set(
        self,
        *,
        user_id: str,
        access_token: str,
        refresh_token: str,
        expires_at: int,
    ) -> None:
        """Add or update a Twitch token set for a user."""
        with self._session() as s:
            token_set = s.get(TwitchTokenSet, user_id)
            if token_set is None:
                token_set = TwitchTokenSet(
                    id=None,
                    user_id=user_id,
                    access_token=access_token,
                    refresh_token=refresh_token,
                    expires_at=expires_at,
                )
            else:
                token_set.access_token = access_token
                token_set.refresh_token = refresh_token
                token_set.expires_at = expires_at

            s.add(token_set)
            s.commit()

    def get_twitch_token_set(self, *, user_id: str) -> Optional[TwitchTokenSet]:
        """Get a Twitch token set for a user."""
        with self._session() as s:
            return s.exec(select(TwitchTokenSet).where(TwitchTokenSet.user_id == user_id)).one_or_none()

    def delete_twitch_token_set(self, *, user_id: str) -> None:
        """Delete a Twitch token set for a user."""
        with self._session() as s:
            token_set: Final = s.exec(select(TwitchTokenSet).where(TwitchTokenSet.user_id == user_id)).one_or_none()
            if token_set is None:
                return
            s.delete(token_set)
            s.commit()
