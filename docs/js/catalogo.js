// Componente CATALOGO.
// Guarda los libros (títulos) y sus ejemplares; cada ejemplar tiene su propio estado.
//
// Interfaz pública (lo único que exporta el módulo):
//   agregarLibro(titulo, autor, numEjemplares) · buscar(titulo) · obtener(id)
//   marcarPrestado(id) · marcarDevuelto(ejemplarId)
// El estado vive en variables del módulo que NO se exportan, y las funciones
// devuelven copias, así nadie de fuera puede modificarlo directamente.

export const DISPONIBLE = 'disponible';
export const PRESTADO = 'prestado';

export class CatalogoError extends Error {
  constructor(mensaje) { super(mensaje); this.name = this.constructor.name; }
}
export class LibroNoEncontrado extends CatalogoError {}
export class EjemplarNoEncontrado extends CatalogoError {}
export class SinEjemplares extends CatalogoError {}

export class Ejemplar {
  constructor(id, libroId, estado = DISPONIBLE) {
    this.id = id;
    this.libroId = libroId;
    this.estado = estado;
  }
}

export class Libro {
  constructor(id, titulo, autor, ejemplares = []) {
    this.id = id;
    this.titulo = titulo;
    this.autor = autor;
    this.ejemplares = ejemplares;
  }
  get total() { return this.ejemplares.length; }
  get disponibles() { return this.ejemplares.filter((e) => e.estado === DISPONIBLE).length; }
}

// ---- Estado INTERNO (no se exporta) ----
const libros = new Map();      // id de libro -> Libro
const ejemplares = new Map();  // id de ejemplar -> Ejemplar (mismos objetos que dentro de Libro)
let siguienteId = 1;

const normalizar = (t) =>
  t.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim();

const copia = (l) =>
  new Libro(l.id, l.titulo, l.autor, l.ejemplares.map((e) => new Ejemplar(e.id, e.libroId, e.estado)));

function libroInterno(id) {
  const libro = libros.get(id);
  if (!libro) throw new LibroNoEncontrado(`No existe ningún libro con id ${id}`);
  return libro;
}

// ---- Interfaz pública ----
export function agregarLibro(titulo, autor, numEjemplares = 1) {
  if (!titulo || !titulo.trim()) throw new CatalogoError('El título no puede estar vacío');
  if (numEjemplares < 1) throw new CatalogoError('Un título necesita al menos un ejemplar');
  const id = siguienteId++;
  const lista = Array.from({ length: numEjemplares }, (_, n) => new Ejemplar(`${id}-${n + 1}`, id));
  libros.set(id, new Libro(id, titulo.trim(), autor.trim(), lista));
  lista.forEach((e) => ejemplares.set(e.id, e));
  return id;
}

export function buscar(titulo) {
  const consulta = normalizar(titulo);
  return [...libros.values()]
    .filter((l) => normalizar(l.titulo).includes(consulta))
    .sort((a, b) => normalizar(a.titulo).localeCompare(normalizar(b.titulo)))
    .map(copia);
}

export function obtener(id) {
  return copia(libroInterno(id));
}

export function marcarPrestado(id) {
  const libro = libroInterno(id);
  const libre = libro.ejemplares.find((e) => e.estado === DISPONIBLE);
  if (!libre) throw new SinEjemplares(`No quedan ejemplares disponibles de «${libro.titulo}»`);
  libre.estado = PRESTADO;
  return libre.id;
}

export function marcarDevuelto(ejemplarId) {
  const ejemplar = ejemplares.get(ejemplarId);
  if (!ejemplar) throw new EjemplarNoEncontrado(`No existe el ejemplar ${ejemplarId}`);
  if (ejemplar.estado !== PRESTADO) throw new CatalogoError(`El ejemplar ${ejemplarId} no estaba prestado`);
  ejemplar.estado = DISPONIBLE;
}

// ---- Persistencia (para guardar en el navegador) ----
export function exportarEstado() {
  return { siguienteId, libros: [...libros.values()].map(copia) };
}

export function importarEstado(datos) {
  libros.clear();
  ejemplares.clear();
  siguienteId = datos.siguienteId;
  for (const l of datos.libros) {
    const lista = l.ejemplares.map((e) => new Ejemplar(e.id, e.libroId, e.estado));
    libros.set(l.id, new Libro(l.id, l.titulo, l.autor, lista));
    lista.forEach((e) => ejemplares.set(e.id, e));
  }
}
