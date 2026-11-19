"""Typed models for disks, network, security, licensing and benchmarks."""

from dataclasses import dataclass, field
from typing import Any, Mapping

from .hardware import _first, _int, _text


def _as_list(value: Any) -> list[Mapping[str, Any]]:
    """Normalize a WMI section to a list of mappings."""
    if isinstance(value, Mapping):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, Mapping)]
    return []


@dataclass(frozen=True)
class DiskInfo:
    """Combined physical disk and partition information."""

    model: str
    media_type: str
    interface: str
    size_bytes: int
    status: str
    health: str
    mountpoint: str
    used_bytes: int
    free_bytes: int
    used_percent: float
    temperature: float | None = None
    wear_percent: float | None = None

    @property
    def warnings(self) -> tuple[str, ...]:
        result: list[str] = []
        if self.health.lower() in {"predict failure", "failed", "degraded"}:
            result.append(f"S.M.A.R.T.: {self.health}")
        if self.temperature is not None and self.temperature >= 50:
            result.append(f"Температура {self.temperature:.0f}°C")
        if self.wear_percent is not None and self.wear_percent >= 80:
            result.append(f"Износ {self.wear_percent:.0f}%")
        if self.used_percent >= 90:
            result.append(f"Занято {self.used_percent:.0f}%")
        return tuple(result)


@dataclass(frozen=True)
class NetworkInfo:
    """Host, user and local network interface summary."""

    hostname: str
    username: str
    ip_addresses: tuple[str, ...]
    interfaces: tuple[str, ...]
    is_connected: bool


@dataclass(frozen=True)
class SecurityProductInfo:
    """Antivirus product reported by Windows Security Center."""

    name: str
    product_state: int
    enabled: bool
    up_to_date: bool

    @classmethod
    def from_wmi(cls, raw: Mapping[str, Any]) -> "SecurityProductInfo":
        state = _int(raw.get("productState"))
        # SecurityCenter2 packs the state into three bytes: provider,
        # definitions and on/off. 0x1000 marks an active product and 0x100 an
        # outdated signature database.
        return cls(
            name=_text(raw.get("displayName"), "Неизвестно"),
            product_state=state,
            enabled=bool(state & 0x1000),
            up_to_date=(state & 0x1100) != 0x0100,
        )


@dataclass(frozen=True)
class LicenseInfo:
    """Read-only Windows activation status."""

    name: str
    status: str
    activated: bool
    expiration: str
    partial: bool

    @classmethod
    def from_wmi_payload(cls, payload: Mapping[str, Any]) -> "LicenseInfo":
        records = _as_list(payload.get("license"))
        active = next(
            (item for item in records if _int(item.get("LicenseStatus")) == 1),
            None,
        )
        if active is None:
            return cls(
                name=_text(_first(payload, "os").get("Caption"), "Windows"),
                status="unlicensed",
                activated=False,
                expiration="Н/Д",
                partial=False,
            )

        remaining = _int(active.get("GracePeriodRemaining"))
        expiration = "бессрочно" if remaining == 0 else f"{remaining // 1440} дн."
        return cls(
            name=_text(active.get("Name"), "Windows"),
            status="activated",
            activated=True,
            expiration=expiration,
            partial=bool(active.get("PartialProductKey")),
        )


@dataclass(frozen=True)
class DiskBenchmarkResult:
    """Result of a cancellable, bounded disk speed test."""

    size_mb: int
    read_mbps: float
    write_mbps: float
    duration_seconds: float
    cancelled: bool = False

    @property
    def summary(self) -> str:
        return (
            f"Запись: {self.write_mbps:.1f} МБ/с, чтение: {self.read_mbps:.1f} МБ/с "
            f"({self.size_mb} МБ, {self.duration_seconds:.1f} с)"
        )


@dataclass(frozen=True)
class SystemHealthSnapshot:
    """Dynamic health data collected alongside the static hardware profile."""

    uptime_seconds: float
    disks: tuple[DiskInfo, ...] = ()
    network: NetworkInfo | None = None
    security: tuple[SecurityProductInfo, ...] = ()
    license: LicenseInfo | None = None
    benchmark: DiskBenchmarkResult | None = None
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation."""
        from dataclasses import asdict

        return asdict(self)
