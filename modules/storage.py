"""Persistencia JSON con manejo de errores y creacion automatica de carpetas."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"


class StorageError(Exception):
    """Error de lectura o escritura sobre archivos JSON."""


def _build_path(filename: str) -> Path:
    return DATA_DIR / filename


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def read_json_file(filename: str, default_data: Any | None = None) -> Any:
    """Lee un archivo JSON y lo inicializa si no existe."""

    path = _build_path(filename)
    ensure_directory(path.parent)

    if not path.exists():
        data_to_store = deepcopy(default_data if default_data is not None else [])
        write_json_file(filename, data_to_store)
        return data_to_store

    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError as error:
        raise StorageError(
            f"El archivo '{path.name}' no contiene un JSON valido."
        ) from error
    except OSError as error:
        raise StorageError(f"No fue posible leer '{path.name}'.") from error


def write_json_file(filename: str, data: Any) -> Path:
    """Escribe datos JSON con UTF-8 y formato legible."""

    path = _build_path(filename)
    ensure_directory(path.parent)

    try:
        with path.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=2, ensure_ascii=False)
    except OSError as error:
        raise StorageError(f"No fue posible escribir '{path.name}'.") from error

    return path


def next_record_id(records: list[dict[str, Any]]) -> int:
    """Obtiene el siguiente identificador numerico disponible."""

    return max((int(record.get("id", 0) or 0) for record in records), default=0) + 1
