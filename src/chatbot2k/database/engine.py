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
from sqlmodel import desc
from sqlmodel import select

from chatbot2k.database.tables import Broadcast
from chatbot2k.database.tables import ConfigurationSetting
from chatbot2k.database.tables import Constant
from chatbot2k.database.tables import DictionaryEntry
from chatbot2k.database.tables import EntranceSound
from chatbot2k.database.tables import LiveNotificationChannel
from chatbot2k.database.tables import Parameter
from chatbot2k.database.tables import ParameterizedCommand
from chatbot2k.database.tables import PendingSoundboardClip
from chatbot2k.database.tables import Script
from chatbot2k.database.tables import ScriptStore
from chatbot2k.database.tables import SoundboardCommand
from chatbot2k.database.tables import StaticCommand
from chatbot2k.database.tables import Translation
from chatbot2k.database.tables import TwitchTokenSet
from chatbot2k.models.parameterized_command import ParameterizedCommand as ParameterizedCommandModel
from chatbot2k.translation_key import TranslationKey
from chatbot2k.types.configuration_setting_kind import ConfigurationSettingKind


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

    def store_configuration_setting(self, kind: ConfigurationSettingKind, value: str) -> None:
        key: Final = kind.value
        with self._session() as s:
            object_ = s.get(ConfigurationSetting, key)
            if object_ is None:
                object_ = ConfigurationSetting(key=key, value=value)
            else:
                object_.value = value
            s.add(object_)
            s.commit()

    def retrieve_configuration_setting(self, kind: ConfigurationSettingKind) -> Optional[str]:
        key: Final = kind.value
        with self._session() as s:
            object_ = s.get(ConfigurationSetting, key)
            if object_ is None:
                return None
            return object_.value

    def retrieve_configuration_setting_or_default[T](self, kind: ConfigurationSettingKind, default: T) -> str | T:
        result: Final = self.retrieve_configuration_setting(kind)
        return default if result is None else result

    def retrieve_configuration_setting_or_raise(self, kind: ConfigurationSettingKind) -> str:
        result: Final = self.retrieve_configuration_setting(kind)
        if result is None:
            raise KeyError(f"Configuration setting '{kind.value}' not found")
        return result

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

    def add_soundboard_command(
        self,
        *,
        name: str,
        filename: str,
        uploader_twitch_id: Optional[str],
        uploader_twitch_login: Optional[str],
        uploader_twitch_display_name: Optional[str],
    ) -> SoundboardCommand:
        with self._session() as s:
            if s.get(SoundboardCommand, name):
                raise ValueError(f"SoundboardCommand '{name}' already exists")
            obj = SoundboardCommand(
                name=name,
                filename=filename,
                uploader_twitch_id=uploader_twitch_id,
                uploader_twitch_login=uploader_twitch_login,
                uploader_twitch_display_name=uploader_twitch_display_name,
            )
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

    def update_soundboard_command_name(self, *, old_name: str, new_name: str) -> None:
        """Update the name of a soundboard command."""
        with self._session() as s:
            # Check if new name already exists (case-insensitive).
            existing_with_new_name = s.exec(
                select(SoundboardCommand).where(func.lower(SoundboardCommand.name) == new_name.lower())
            ).one_or_none()
            if existing_with_new_name is not None and existing_with_new_name.name != old_name:
                raise ValueError(f"SoundboardCommand '{new_name}' already exists")

            # Get the command to update
            obj = s.get(SoundboardCommand, old_name)
            if obj is None:
                raise KeyError(f"SoundboardCommand '{old_name}' not found")

            # Update the name
            obj.name = new_name
            s.add(obj)
            s.commit()

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
            return s.exec(
                select(TwitchTokenSet)
                .where(TwitchTokenSet.user_id == user_id)
                .order_by(desc(TwitchTokenSet.expires_at))
            ).first()

    def delete_twitch_token_set(self, *, user_id: str) -> None:
        """Delete all token sets for a user."""
        with self._session() as s:
            token_sets: Final = s.exec(select(TwitchTokenSet).where(TwitchTokenSet.user_id == user_id)).all()
            for token_set in token_sets:
                s.delete(token_set)
            s.commit()

    def add_live_notification_channel(
        self,
        *,
        broadcaster_name: str,
        broadcaster_id: str,
        text_template: str,
        target_channel: str,
    ) -> None:
        """Add a live notification channel for a broadcaster."""
        with self._session() as s:
            existing: Final = s.exec(
                select(LiveNotificationChannel).where(
                    LiveNotificationChannel.broadcaster_id == broadcaster_id,
                )
            ).one_or_none()
            if existing is not None:
                msg: Final = (
                    f"Live notification channel for broadcaster '{broadcaster_name}' "
                    + f"(ID = {broadcaster_id}) already exists"
                )
                raise ValueError(msg)
            live_notification_channel: Final = LiveNotificationChannel(
                broadcaster_name=broadcaster_name,
                broadcaster_id=broadcaster_id,
                text_template=text_template,
                target_channel=target_channel,
            )
            s.add(live_notification_channel)
            s.commit()

    def get_live_notification_channels(self) -> list[LiveNotificationChannel]:
        """Get all live notification channels."""
        with self._session() as s:
            return list(s.exec(select(LiveNotificationChannel)).all())

    def update_live_notification_channel(
        self,
        *,
        id_: int,
        broadcaster_name: str,
        broadcaster_id: str,
        text_template: str,
        target_channel: str,
    ) -> None:
        """Update a live notification channel."""
        with self._session() as s:
            channel: Final = s.exec(
                select(LiveNotificationChannel).where(LiveNotificationChannel.id == id_)
            ).one_or_none()
            if channel is None:
                raise KeyError(f"Live notification channel with id '{id_}' not found")
            channel.broadcaster_name = broadcaster_name
            channel.broadcaster_id = broadcaster_id
            channel.text_template = text_template
            channel.target_channel = target_channel
            s.add(channel)
            s.commit()

    def remove_live_notification_channel(self, *, broadcaster_id: str) -> None:
        """Remove a live notification channel for a broadcaster."""
        with self._session() as s:
            live_notification_channel: Final = s.exec(
                select(LiveNotificationChannel).where(
                    LiveNotificationChannel.broadcaster_id == broadcaster_id,
                )
            ).one_or_none()
            if live_notification_channel is None:
                msg: Final = f"Live notification channel for broadcaster ID {broadcaster_id} not found"
                raise KeyError(msg)
            s.delete(live_notification_channel)
            s.commit()

    def add_pending_soundboard_clip(
        self,
        *,
        name: str,
        filename: str,
        uploader_twitch_id: str,
        uploader_twitch_login: str,
        uploader_twitch_display_name: str,
        may_persist_uploader_info: bool,
    ) -> None:
        """Add a pending soundboard clip."""
        with self._session() as s:
            existing: Final = s.get(PendingSoundboardClip, name)
            if existing is not None:
                raise ValueError(f"PendingSoundboardClip '{name}' already exists")
            clip: Final = PendingSoundboardClip(
                name=name,
                filename=filename,
                uploader_twitch_id=uploader_twitch_id,
                uploader_twitch_login=uploader_twitch_login,
                uploader_twitch_display_name=uploader_twitch_display_name,
                may_persist_uploader_info=may_persist_uploader_info,
            )
            s.add(clip)
            s.commit()

    def update_pending_soundboard_clip(
        self,
        *,
        id_: int,
        name: str,
        may_persist_uploader_info: bool,
    ) -> None:
        """Update a pending soundboard clip."""
        with self._session() as s:
            clip: Final = s.get(PendingSoundboardClip, id_)
            if clip is None:
                raise KeyError(f"PendingSoundboardClip with ID {id_} not found")
            clip.name = name
            clip.may_persist_uploader_info = may_persist_uploader_info
            s.add(clip)
            s.commit()

    def remove_pending_soundboard_clip(self, *, id_: int) -> None:
        """Remove a pending soundboard clip by ID."""
        with self._session() as s:
            clip: Final = s.get(PendingSoundboardClip, id_)
            if clip is None:
                raise KeyError(f"PendingSoundboardClip with ID {id_} not found")
            s.delete(clip)
            s.commit()

    def get_number_of_pending_soundboard_clips(self) -> int:
        """Get the number of pending soundboard clips."""
        with self._session() as s:
            return s.exec(select(func.count()).select_from(PendingSoundboardClip)).one()

    def get_all_pending_soundboard_clips(self) -> list[PendingSoundboardClip]:
        """Get all pending soundboard clips."""
        with self._session() as s:
            return list(s.exec(select(PendingSoundboardClip).order_by(PendingSoundboardClip.name)).all())

    def get_pending_soundboard_clips_by_twitch_user_id(self, *, twitch_user_id: str) -> list[PendingSoundboardClip]:
        """Get pending soundboard clips for a specific Twitch user ID."""
        with self._session() as s:
            return list(
                s.exec(
                    select(PendingSoundboardClip)
                    .where(PendingSoundboardClip.uploader_twitch_id == twitch_user_id)
                    .order_by(PendingSoundboardClip.name)
                ).all()
            )

    def add_entrance_sound(
        self,
        *,
        twitch_user_id: str,
        filename: str,
    ) -> None:
        """Add an entrance sound for a Twitch user."""
        with self._session() as s:
            existing: Final = s.exec(
                select(EntranceSound).where(EntranceSound.twitch_user_id == twitch_user_id)
            ).one_or_none()
            if existing is not None:
                raise ValueError(f"EntranceSound for Twitch user ID '{twitch_user_id}' already exists")
            entrance_sound: Final = EntranceSound(
                twitch_user_id=twitch_user_id,
                filename=filename,
            )
            s.add(entrance_sound)
            s.commit()

    def get_all_entry_sounds(self) -> list[EntranceSound]:
        """Get all entrance sounds."""
        with self._session() as s:
            return list(s.exec(select(EntranceSound)).all())

    def get_entrance_sound_by_twitch_user_id(self, *, twitch_user_id: str) -> Optional[EntranceSound]:
        """Get an entrance sound for a specific Twitch user ID."""
        with self._session() as s:
            return s.exec(select(EntranceSound).where(EntranceSound.twitch_user_id == twitch_user_id)).one_or_none()

    def delete_entrance_sound(self, *, twitch_user_id: str) -> None:
        """Delete an entrance sound for a Twitch user."""
        with self._session() as s:
            entrance_sound: Final = s.exec(
                select(EntranceSound).where(EntranceSound.twitch_user_id == twitch_user_id)
            ).one_or_none()
            if entrance_sound is None:
                raise KeyError(f"EntranceSound for Twitch user ID '{twitch_user_id}' not found")
            s.delete(entrance_sound)
            s.commit()
