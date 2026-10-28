"""Componente PRESTAMOS.

Gestiona préstamos y reservas. Para saber algo de un libro o de un socio
pregunta a los componentes Catalogo y Socios, y SOLO a través de sus
funciones públicas (nunca toca sus variables internas).

Dependencias:  prestamos -> catalogo,  prestamos -> socios

Reglas:
  * un socio no puede tener más de 2 libros a la vez
  * cada préstamo caduca a los 7 días
  * un socio sancionado no puede pedir ni reservar libros
  * se puede reservar un libro cuando todos sus ejemplares están prestados
  * si se devuelve tarde, el socio queda sancionado tantos días como de retraso

Interfaz pública:
    prestar(socio_id, libro_id, hoy=None)    -> Prestamo
    devolver(prestamo_id, hoy=None)          -> Prestamo
    reservar(socio_id, libro_id, hoy=None)   -> Reserva
    cancelar_reserva(reserva_id)
    prestamos_activos(socio_id=None)         -> list[Prestamo]
    reservas(libro_id=None)                  -> list[Reserva]
"""

import copy
from datetime import date, timedelta

import catalogo
import socios

__all__ = [
    "MAX_PRESTAMOS", "DIAS_PRESTAMO",
    "Prestamo", "Reserva",
    "PrestamosError", "SocioSancionado", "LimitePrestamos", "LibroNoDisponible",
    "EjemplarReservado", "ReservaInvalida", "PrestamoNoEncontrado",
    "prestar", "devolver", "reservar", "cancelar_reserva",
    "prestamos_activos", "reservas",
]

MAX_PRESTAMOS = 2
DIAS_PRESTAMO = 7


# --------------------------------------------------------------------------
# Errores
# --------------------------------------------------------------------------
class PrestamosError(Exception):
    """Error base del componente Prestamos."""


class SocioSancionado(PrestamosError):
    pass


class LimitePrestamos(PrestamosError):
    pass


class LibroNoDisponible(PrestamosError):
    pass


class EjemplarReservado(PrestamosError):
    pass


class ReservaInvalida(PrestamosError):
    pass


class PrestamoNoEncontrado(PrestamosError):
    pass


# --------------------------------------------------------------------------
# Clases con identidad (id) y estado
# --------------------------------------------------------------------------
class Prestamo:
    """Un préstamo. Identidad: id. Estado: activo hasta que se devuelve."""

    def __init__(self, id, socio_id, libro_id, ejemplar_id, fecha_inicio):
        self.id = id
        self.socio_id = socio_id
        self.libro_id = libro_id
        self.ejemplar_id = ejemplar_id
        self.fecha_inicio = fecha_inicio
        self.fecha_vencimiento = fecha_inicio + timedelta(days=DIAS_PRESTAMO)
        self.fecha_devolucion = None

    @property
    def activo(self):
        return self.fecha_devolucion is None

    def esta_vencido(self, hoy):
        return self.activo and hoy > self.fecha_vencimiento

    @property
    def dias_retraso(self):
        """Días de retraso con que se devolvió (0 si fue a tiempo o sigue activo)."""
        if self.fecha_devolucion is None:
            return 0
        return max(0, (self.fecha_devolucion - self.fecha_vencimiento).days)

    def __eq__(self, otro):
        return isinstance(otro, Prestamo) and self.id == otro.id

    def __hash__(self):
        return hash(self.id)

    def __repr__(self):
        return f"Prestamo({self.id}, socio={self.socio_id}, libro={self.libro_id})"


class Reserva:
    """Una reserva de un libro ya prestado. Identidad: id."""

    def __init__(self, id, socio_id, libro_id, fecha):
        self.id = id
        self.socio_id = socio_id
        self.libro_id = libro_id
        self.fecha = fecha

    def __eq__(self, otro):
        return isinstance(otro, Reserva) and self.id == otro.id

    def __hash__(self):
        return hash(self.id)

    def __repr__(self):
        return f"Reserva({self.id}, socio={self.socio_id}, libro={self.libro_id})"


# --------------------------------------------------------------------------
# Estado INTERNO (no se expone)
# --------------------------------------------------------------------------
_prestamos = []
_reservas = []
_siguiente_prestamo = 1
_siguiente_reserva = 1


def _activos_de(socio_id):
    return [p for p in _prestamos if p.socio_id == socio_id and p.activo]


def _cola(libro_id, hoy):
    """Reservas del libro por orden de llegada, ignorando a quien ahora no podría
    cogerlo (sancionado), para que una reserva no bloquee el libro para siempre."""
    return [r for r in _reservas
            if r.libro_id == libro_id and not socios.esta_sancionado(r.socio_id, hoy)]


def _comprobar_puede_pedir(socio_id, hoy):
    socio = socios.obtener(socio_id)          # lanza SocioNoEncontrado si no existe
    if socios.esta_sancionado(socio_id, hoy):
        raise SocioSancionado(
            f"{socio.nombre} está sancionado hasta el {socio.sancionado_hasta:%d/%m/%Y}"
        )
    return socio


# --------------------------------------------------------------------------
# Interfaz pública
# --------------------------------------------------------------------------
def prestar(socio_id, libro_id, hoy=None):
    """Presta un ejemplar del libro al socio, si las reglas lo permiten."""
    global _siguiente_prestamo
    hoy = hoy or date.today()

    socio = _comprobar_puede_pedir(socio_id, hoy)
    if len(_activos_de(socio_id)) >= MAX_PRESTAMOS:
        raise LimitePrestamos(
            f"{socio.nombre} ya tiene {MAX_PRESTAMOS} libros prestados (máximo permitido)"
        )

    libro = catalogo.obtener(libro_id)        # solo la función pública
    if libro.disponibles == 0:
        raise LibroNoDisponible(
            f"No quedan ejemplares de «{libro.titulo}». Puede reservarlo."
        )

    # Los ejemplares libres se retienen para quien reservó antes (por orden).
    cola = _cola(libro_id, hoy)
    posicion = next((i for i, r in enumerate(cola) if r.socio_id == socio_id), None)
    if posicion is not None:
        if posicion >= libro.disponibles:
            raise EjemplarReservado(
                f"Aún no le toca a {socio.nombre}: hay {posicion} reserva(s) por delante"
            )
    elif len(cola) >= libro.disponibles:
        raise EjemplarReservado(
            f"Los ejemplares libres de «{libro.titulo}» están retenidos para reservas"
        )

    ejemplar_id = catalogo.marcar_prestado(libro_id)
    if posicion is not None:
        _reservas.remove(cola[posicion])      # la reserva se cumple

    prestamo = Prestamo(_siguiente_prestamo, socio_id, libro_id, ejemplar_id, hoy)
    _siguiente_prestamo += 1
    _prestamos.append(prestamo)
    return copy.copy(prestamo)


def devolver(prestamo_id, hoy=None):
    """Registra la devolución. Si es tarde, sanciona al socio."""
    hoy = hoy or date.today()
    prestamo = next((p for p in _prestamos if p.id == prestamo_id and p.activo), None)
    if prestamo is None:
        raise PrestamoNoEncontrado(f"No hay ningún préstamo activo con id {prestamo_id}")

    catalogo.marcar_devuelto(prestamo.ejemplar_id)
    prestamo.fecha_devolucion = hoy

    if prestamo.dias_retraso > 0:
        socios.sancionar(prestamo.socio_id, hoy + timedelta(days=prestamo.dias_retraso))
    return copy.copy(prestamo)


def reservar(socio_id, libro_id, hoy=None):
    """Reserva un libro cuyos ejemplares libres ya están todos comprometidos."""
    global _siguiente_reserva
    hoy = hoy or date.today()

    socio = _comprobar_puede_pedir(socio_id, hoy)
    libro = catalogo.obtener(libro_id)
    cola = _cola(libro_id, hoy)

    if libro.disponibles > len(cola):
        raise ReservaInvalida(
            f"«{libro.titulo}» tiene ejemplares libres: pídalo directamente"
        )
    if any(r.socio_id == socio_id for r in cola):
        raise ReservaInvalida(f"{socio.nombre} ya tiene reservado «{libro.titulo}»")

    reserva = Reserva(_siguiente_reserva, socio_id, libro_id, hoy)
    _siguiente_reserva += 1
    _reservas.append(reserva)
    return copy.copy(reserva)


def cancelar_reserva(reserva_id):
    reserva = next((r for r in _reservas if r.id == reserva_id), None)
    if reserva is None:
        raise ReservaInvalida(f"No existe la reserva {reserva_id}")
    _reservas.remove(reserva)


def prestamos_activos(socio_id=None):
    return [copy.copy(p) for p in _prestamos
            if p.activo and (socio_id is None or p.socio_id == socio_id)]


def reservas(libro_id=None):
    return [copy.copy(r) for r in _reservas
            if libro_id is None or r.libro_id == libro_id]
