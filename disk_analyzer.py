#!/usr/bin/env python3
"""Аналіз використання диска в Arch Linux. Лише читання, без залежностей."""

import argparse
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
from dataclasses import dataclass, field


@dataclass
class Usage:
    size: int = 0
    missing: bool = False
    errors: list[str] = field(default_factory=list)


def scan(root: Path) -> Usage:
    """Порахувати st_blocks, не обходячи symlink і не дублюючи hardlink."""
    result = Usage()
    pending = [root]
    seen = set()
    while pending:
        path = pending.pop()
        try:
            info = path.lstat()
            key = (info.st_dev, info.st_ino)
            if key in seen:
                continue
            seen.add(key)
            result.size += info.st_blocks * 512
            if stat.S_ISDIR(info.st_mode):
                with os.scandir(path) as entries:
                    for entry in entries:
                        pending.append(Path(entry.path))
        except FileNotFoundError as exc:
            if path == root:
                result.missing = True
            else:
                result.errors.append(f"{path}: {exc.strerror}")
        except OSError as exc:
            result.errors.append(f"{path}: {exc.strerror}")
    return result


def human_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB", "PiB"):
        if value < 1024 or unit == "PiB":
            return f"{value:.1f} {unit}"
        value /= 1024


def xdg_path(name: str, fallback: Path, use_environment: bool) -> Path:
    value = os.environ.get(name) if use_environment else None
    return Path(value) if value and Path(value).is_absolute() else fallback


def pacman_paths(warnings: list[str]) -> list[Path]:
    try:
        output = subprocess.run(
            ["pacman-conf", "CacheDir"], capture_output=True, text=True,
            check=True, timeout=5,
        ).stdout
        paths = list(dict.fromkeys(Path(line.strip()) for line in output.splitlines()
                                   if line.strip()))
        if paths and all(path.is_absolute() for path in paths):
            return paths
    except (OSError, subprocess.SubprocessError):
        pass
    warnings.append("Не вдалося прочитати CacheDir через pacman-conf; "
                    "використано /var/cache/pacman/pkg.")
    return [Path("/var/cache/pacman/pkg")]


def yay_path(config: Path, cache: Path, warnings: list[str]) -> Path:
    try:
        data = json.loads((config / "yay/config.json").read_text())
        if not isinstance(data, dict):
            raise ValueError("очікується JSON-об’єкт")
        # yay зберігає каталог збірки в полі buildDir.
        value = data.get("buildDir")
        if value is not None:
            if not isinstance(value, str) or not Path(value).is_absolute():
                raise ValueError("buildDir має бути абсолютним шляхом")
            return Path(value)
    except FileNotFoundError:
        pass
    except (OSError, ValueError) as exc:
        warnings.append(f"Не вдалося прочитати конфігурацію yay: {exc}; "
                        "використано стандартний каталог.")
    return cache / "yay"


def display(label: str, path: Path, usage: Usage) -> None:
    status = " — відсутній" if usage.missing else ""
    if usage.errors:
        status += f" — НЕПОВНО, помилок: {len(usage.errors)}"
    # repr не дозволяє керівним символам в іменах змінювати термінал.
    print(f"{human_size(usage.size):>12}  {label}: {str(path)!r}{status}")


def positive_int(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("значення має бути більше нуля")
    return number


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--top", type=positive_int, default=10,
                        help="кількість найбільших папок (типово: 10)")
    parser.add_argument("--home", type=Path,
                        help="домашня директорія для аналізу (типово: поточний користувач)")
    parser.add_argument("--pacman-cache", type=Path, action="append",
                        help="шлях кешу pacman; можна вказати кілька разів")
    parser.add_argument("--yay-cache", type=Path, help="шлях кешу/збірок yay")
    args = parser.parse_args(argv)
    home = (args.home or Path.home()).expanduser().absolute()
    if not home.is_dir():
        parser.error(f"домашня директорія не існує або недоступна: {home}")

    warnings: list[str] = []
    use_environment = args.home is None
    cache = xdg_path("XDG_CACHE_HOME", home / ".cache", use_environment)
    config = xdg_path("XDG_CONFIG_HOME", home / ".config", use_environment)
    data = xdg_path("XDG_DATA_HOME", home / ".local/share", use_environment)
    pacman = args.pacman_cache or pacman_paths(warnings)
    yay = args.yay_cache or yay_path(config, cache, warnings)
    targets = [("Кеш pacman", path.expanduser()) for path in pacman]
    targets += [
        ("Кеш/збірки yay", yay.expanduser()),
        ("Кошик користувача", data / "Trash"),
        ("Журнали (включно з постійним journal)", Path("/var/log")),
        ("Тимчасовий journal", Path("/run/log/journal")),
    ]
    print("Зайняте місце на диску (блоки; 1 KiB = 1024 B)\n")
    incomplete = False
    for label, path in targets:
        usage = scan(path)
        display(label, path, usage)
        incomplete |= bool(usage.errors)
        warnings.extend(usage.errors[:3])

    print(f"\nНайбільші папки в {str(home)!r} (включно з прихованими):")
    directories = []
    try:
        with os.scandir(home) as entries:
            for entry in entries:
                try:
                    if entry.is_dir(follow_symlinks=False):
                        path = Path(entry.path)
                        usage = scan(path)
                        directories.append((path, usage))
                        incomplete |= bool(usage.errors) or usage.missing
                        warnings.extend(usage.errors[:3])
                except OSError as exc:
                    incomplete = True
                    warnings.append(f"{entry.path}: {exc.strerror}")
    except OSError as exc:
        incomplete = True
        warnings.append(f"{home}: {exc.strerror}")

    directories.sort(key=lambda item: (-item[1].size, str(item[0])))
    for path, usage in directories[:args.top]:
        display("Папка", path, usage)
    if not directories:
        print("Папок не знайдено або немає доступу.")
    print("\nКатегорії та домашні папки можуть перетинатися; їх не слід додавати.")
    print("Кошики інших дисків не враховано. Символічні посилання не обходяться.")
    if warnings:
        print("\nПопередження:", file=sys.stderr)
        for warning in warnings:
            print(f"  {warning!r}", file=sys.stderr)
    return 1 if incomplete else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nАналіз перервано.", file=sys.stderr)
        sys.exit(130)
