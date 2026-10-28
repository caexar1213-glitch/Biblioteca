// Componente SOCIOS.
// Guarda a los socios y sus sanciones.
//
// Interfaz pública: alta(nombre) · obtener(id) · listar() ·
//                   estaSancionado(id, hoy) · sancionar(id, hasta)

export class SociosError extends Error {
  constructor(mensaje) { super(mensaje); this.name = this.constructor.name; }
}
export class SocioNoEncontrado extends SociosError {}

export class Socio {
  constructor(id, nombre, sancionadoHasta = null) {
    this.id = id;
    this.nombre = nombre;
    this.sancionadoHasta = sancionadoHasta; // «AAAA-MM-DD» o null
  }
  estaSancionado(hoy) {
    return this.sancionadoHasta !== null && hoy < this.sancionadoHasta;
  }
}

// ---- Estado INTERNO (no se exporta) ----
const socios = new Map();
let siguienteId = 1;

const copia = (s) => new Socio(s.id, s.nombre, s.sancionadoHasta);

function socioInterno(id) {
  const socio = socios.get(id);
  if (!socio) throw new SocioNoEncontrado(`No existe ningún socio con id ${id}`);
  return socio;
}

// ---- Interfaz pública ----
export function alta(nombre) {
  if (!nombre || !nombre.trim()) throw new SociosError('El nombre no puede estar vacío');
  const socio = new Socio(siguienteId++, nombre.trim());
  socios.set(socio.id, socio);
  return copia(socio);
}

export function obtener(id) {
  return copia(socioInterno(id));
}

export function listar() {
  return [...socios.values()].map(copia);
}

export function estaSancionado(id, hoy) {
  return socioInterno(id).estaSancionado(hoy);
}

export function sancionar(id, hasta) {
  const socio = socioInterno(id);
  if (socio.sancionadoHasta === null || hasta > socio.sancionadoHasta) socio.sancionadoHasta = hasta;
  return copia(socio);
}

// ---- Persistencia ----
export function exportarEstado() {
  return { siguienteId, socios: [...socios.values()].map(copia) };
}

export function importarEstado(datos) {
  socios.clear();
  siguienteId = datos.siguienteId;
  for (const s of datos.socios) socios.set(s.id, new Socio(s.id, s.nombre, s.sancionadoHasta));
}
