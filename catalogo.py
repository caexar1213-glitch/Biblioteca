"""Componente CATALOGO.

Guarda los libros (títulos) y sus ejemplares físicos. Cada ejemplar tiene su
propio estado (disponible / prestado).

Interfaz pública (lo único que pueden usar los demás componentes):
    agregar_libro(titulo, autor, num_ejemplares=1) -> int
    buscar(titulo)          -> list[Libro]
    obtener(id)             -> Libro
    marcar_prestado(id)     -> str   (id del ejemplar que se ha prestado)
    marcar_devuelto(ejemplar_id)

Todo lo que empieza por «_» es interior del componente. Las funciones públicas
devuelven COPIAS, así nadie de fuera puede modificar el estado por la puerta
de atrás.
"""

import unicodedata

__all__ = [
    "DISPONIBLE", "PRESTADO",
    "Libro", "Ejemplar",
    "CatalogoError", "LibroNoEncontrado", "EjemplarNoEncontrado", "SinEjemplares",
    "agregar_libro", "buscar", "obtener", "marcar_prestado", "marcar_devuelto",
]

DISPONIBLE = "disponible"
PRESTADO = "prestado"


# --------------------------------------------------------------------------
# Errores
# --------------------------------------------------------------------------
class CatalogoError(Exception):
    """Error base del componente Catalogo."""


class LibroNoEncontrado(CatalogoError):
    pass


class EjemplarNoEncontrado(CatalogoError):
    pass


class SinEjemplares(CatalogoError):
    """No queda ningún ejemplar disponible del libro."""


# --------------------------------------------------------------------------
# Clases con identidad (id) y estado
# --------------------------------------------------------------------------
class Ejemplar:
    """Una copia física de un libro. Identidad: id. Estado: disponible/prestado."""

    def __init__(self, id, libro_id, estado=DISPONIBLE):
        self.id = id
        self.libro_id = libro_id
        self.estado = estado

    def __eq__(self, otro):
        return isinstance(otro, Ejemplar) and self.id == otro.id

    def __hash__(self):
        return hash(self.id)

    def __repr__(self):
        return f"Ejemplar({self.id}, {self.estado})"


class Libro:
    """Un título del catálogo. Identidad: id. Estado: el de sus ejemplares."""

    def __init__(self, id, titulo, autor, ejemplares=None):
        self.id = id
        self.titulo = titulo
        self.autor = autor
        self.ejemplares = list(ejemplares or [])

    @property
    def total(self):
        return len(self.ejemplares)

    @property
    def disponibles(self):
        return sum(1 for e in self.ejemplares if e.estado == DISPONIBLE)

    def __eq__(self, otro):
        return isinstance(otro, Libro) and self.id == otro.id

    def __hash__(self):
        return hash(self.id)

    def __repr__(self):
        return f"Libro({self.id}, {self.titulo!r}, {self.disponibles}/{self.total})"


# --------------------------------------------------------------------------
# Estado INTERNO del componente (no se expone)
# --------------------------------------------------------------------------
_libros = {}       # id de libro -> Libro
_ejemplares = {}   # id de ejemplar -> Ejemplar (mismos objetos que dentro de Libro)
_siguiente_id = 1


def _normalizar(texto):
    """Minúsculas y sin tildes, para buscar «quijote» y encontrar «Quijote»."""
    sin_tildes = unicodedata.normalize("NFD", texto)
    sin_tildes = "".join(c for c in sin_tildes if unicodedata.category(c) != "Mn")
    return sin_tildes.lower().strip()


def _copia(libro):
    return Libro(
        libro.id, libro.titulo, libro.autor,
        [Ejemplar(e.id, e.libro_id, e.estado) for e in libro.ejemplares],
    )


def _libro_interno(id):
    try:
        return _libros[id]
    except KeyError:
        raise LibroNoEncontrado(f"No existe ningún libro con id {id}") from None


# --------------------------------------------------------------------------
# Interfaz pública
# --------------------------------------------------------------------------
def agregar_libro(titulo, autor, num_ejemplares=1):
    """Da de alta un título con varios ejemplares. Devuelve el id del libro."""
    global _siguiente_id
    if not titulo or not titulo.strip():
        raise CatalogoError("El título no puede estar vacío")
    if num_ejemplares < 1:
        raise CatalogoError("Un título necesita al menos un ejemplar")
    libro_id = _siguiente_id
    _siguiente_id += 1
    ejemplares = [Ejemplar(f"{libro_id}-{n}", libro_id) for n in range(1, num_ejemplares + 1)]
    _libros[libro_id] = Libro(libro_id, titulo.strip(), autor.strip(), ejemplares)
    for e in ejemplares:
        _ejemplares[e.id] = e
    return libro_id


def buscar(titulo):
    """Libros cuyo título contiene el texto (sin distinguir tildes ni mayúsculas).

    Con texto vacío devuelve todo el catálogo, ordenado por título."""
    consulta = _normalizar(titulo)
    encontrados = [l for l in _libros.values() if consulta in _normalizar(l.titulo)]
    encontrados.sort(key=lambda l: _normalizar(l.titulo))
    return [_copia(l) for l in encontrados]


def obtener(id):
    """Devuelve una copia del libro con ese id."""
    return _copia(_libro_interno(id))


def marcar_prestado(id):
    """Marca como prestado el primer ejemplar libre del libro `id`.

    Devuelve el id del ejemplar concreto que ha salido de la biblioteca."""
    libro = _libro_interno(id)
    for ejemplar in libro.ejemplares:
        if ejemplar.estado == DISPONIBLE:
            ejemplar.estado = PRESTADO
            return ejemplar.id
    raise SinEjemplares(f"No quedan ejemplares disponibles de «{libro.titulo}»")


def marcar_devuelto(ejemplar_id):
    """Vuelve a poner disponible un ejemplar concreto."""
    ejemplar = _ejemplares.get(ejemplar_id)
    if ejemplar is None:
        raise EjemplarNoEncontrado(f"No existe el ejemplar {ejemplar_id}")
    if ejemplar.estado != PRESTADO:
        raise CatalogoError(f"El ejemplar {ejemplar_id} no estaba prestado")
    ejemplar.estado = DISPONIBLE
