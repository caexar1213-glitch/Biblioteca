"""Componente SOCIOS.

Guarda a los socios de la biblioteca y sus sanciones.

Interfaz pública:
    alta(nombre)                 -> Socio
    obtener(id)                  -> Socio
    listar()                     -> list[Socio]
    esta_sancionado(id, hoy=None) -> bool
    sancionar(id, hasta)         -> Socio   (sancionado hasta esa fecha, sin incluirla)

Todo lo que empieza por «_» es interior del componente.
"""

from datetime import date

__all__ = [
    "Socio", "SociosError", "SocioNoEncontrado",
    "alta", "obtener", "listar", "esta_sancionado", "sancionar",
]


class SociosError(Exception):
    """Error base del componente Socios."""


class SocioNoEncontrado(SociosError):
    pass


class Socio:
    """Un socio. Identidad: id. Estado: hasta cuándo está sancionado (si lo está)."""

    def __init__(self, id, nombre, sancionado_hasta=None):
        self.id = id
        self.nombre = nombre
        self.sancionado_hasta = sancionado_hasta

    def esta_sancionado(self, hoy):
        return self.sancionado_hasta is not None and hoy < self.sancionado_hasta

    def __eq__(self, otro):
        return isinstance(otro, Socio) and self.id == otro.id

    def __hash__(self):
        return hash(self.id)

    def __repr__(self):
        return f"Socio({self.id}, {self.nombre!r})"


# Estado INTERNO (no se expone)
_socios = {}
_siguiente_id = 1


def _copia(socio):
    return Socio(socio.id, socio.nombre, socio.sancionado_hasta)


def _socio_interno(id):
    try:
        return _socios[id]
    except KeyError:
        raise SocioNoEncontrado(f"No existe ningún socio con id {id}") from None


def alta(nombre):
    """Da de alta a un socio nuevo y devuelve una copia de su ficha."""
    global _siguiente_id
    if not nombre or not nombre.strip():
        raise SociosError("El nombre no puede estar vacío")
    socio = Socio(_siguiente_id, nombre.strip())
    _socios[socio.id] = socio
    _siguiente_id += 1
    return _copia(socio)


def obtener(id):
    return _copia(_socio_interno(id))


def listar():
    return [_copia(s) for s in _socios.values()]


def esta_sancionado(id, hoy=None):
    hoy = hoy or date.today()
    return _socio_interno(id).esta_sancionado(hoy)


def sancionar(id, hasta):
    """Sanciona al socio hasta `hasta`. Si ya tenía una sanción más larga, se mantiene."""
    socio = _socio_interno(id)
    if socio.sancionado_hasta is None or hasta > socio.sancionado_hasta:
        socio.sancionado_hasta = hasta
    return _copia(socio)
