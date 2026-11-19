"""Data models for registry tweak plans, backups and results."""

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class RegistryTarget:
    """A single registry value that a tweak writes."""

    hive: str
    path: str
    value_name: str
    expected_type: int
    desired_value: Any

    @property
    def key(self) -> str:
        return f"{self.hive}\\{self.path}\\{self.value_name}"


@dataclass(frozen=True)
class BackupEntry:
    """Original value of a registry entry before a tweak was applied."""

    hive: str
    path: str
    value_name: str
    value: Any
    type: int

    @property
    def key(self) -> str:
        return f"{self.hive}\\{self.path}\\{self.value_name}"

    @classmethod
    def from_mapping(cls, key: str, raw: Mapping[str, Any]) -> "BackupEntry":
        return cls(
            hive=str(raw.get("hive") or key.split("\\", 1)[0]),
            path=str(raw.get("path") or ""),
            value_name=str(raw.get("value_name") or ""),
            value=raw.get("value"),
            type=int(raw.get("type", 0)),
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "hive": self.hive,
            "path": self.path,
            "value_name": self.value_name,
            "value": self.value,
            "type": self.type,
        }


@dataclass(frozen=True)
class TweakResult:
    """Outcome of applying or reverting a registry tweak."""

    tweak_id: str
    enabled: bool
    changed: int
    failed: tuple[str, ...] = ()
    dry_run: bool = False

    @property
    def ok(self) -> bool:
        return not self.failed

    @property
    def message(self) -> str:
        action = "включения" if self.enabled else "отката"
        prefix = "[ПРОВЕРКА] " if self.dry_run else ""
        if self.failed:
            return (
                f"{prefix}Твик '{self.tweak_id}': {action} — изменено {self.changed}, "
                f"сбоев {len(self.failed)}: {', '.join(self.failed)}"
            )
        if self.changed == 0:
            return f"{prefix}Твик '{self.tweak_id}': изменений не требуется"
        return f"{prefix}Твик '{self.tweak_id}': {action} — изменено значений: {self.changed}"
