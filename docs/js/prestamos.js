// Componente PRESTAMOS.
// Gestiona préstamos y reservas. Para saber algo de un libro o de un socio pregunta
// a Catalogo y a Socios, y SOLO a través de sus funciones públicas.
//
// Dependencias:  prestamos -> catalogo,  prestamos -> socios
//
// Reglas: máximo 2 libros a la vez · préstamo de 7 días · el socio sancionado no puede
// pedir ni reservar · se reservan libros ya prestados · devolver tarde sanciona tantos
// días como de retraso.

import * as catalogo from './catalogo.js';
import * as socios from './socios.js';
import { sumarDias, diasEntre, formatear } from './fechas.js';

export const MAX_PRESTAMOS = 2;
export const DIAS_PRESTAMO = 7;

export class PrestamosError extends Error {
  constructor(mensaje) { super(mensaje); this.name = this.constructor.name; }
}
export class SocioSancionado extends PrestamosError {}
export class LimitePrestamos extends PrestamosError {}
export class LibroNoDisponible extends PrestamosError {}
export class EjemplarReservado extends PrestamosError {}
export class ReservaInvalida extends PrestamosError {}
export class PrestamoNoEncontrado extends PrestamosError {}

export class Prestamo {
  constructor(id, socioId, libroId, ejemplarId, fechaInicio) {
    this.id = id;
    this.socioId = socioId;
    this.libroId = libroId;
    this.ejemplarId = ejemplarId;
    this.fechaInicio = fechaInicio;
    this.fechaVencimiento = sumarDias(fechaInicio, DIAS_PRESTAMO);
    this.fechaDevolucion = null;
  }
  get activo() { return this.fechaDevolucion === null; }
  estaVencido(hoy) { return this.activo && hoy > this.fechaVencimiento; }
  get diasRetraso() {
    return this.fechaDevolucion === null ? 0 : Math.max(0, diasEntre(this.fechaVencimiento, this.fechaDevolucion));
  }
}

export class Reserva {
  constructor(id, socioId, libroId, fecha) {
    this.id = id;
    this.socioId = socioId;
    this.libroId = libroId;
    this.fecha = fecha;
  }
}

// ---- Estado INTERNO (no se exporta) ----
let prestamosLista = [];
let reservasLista = [];
let siguientePrestamo = 1;
let siguienteReserva = 1;

const copiaP = (p) => Object.assign(new Prestamo(p.id, p.socioId, p.libroId, p.ejemplarId, p.fechaInicio), {
  fechaDevolucion: p.fechaDevolucion,
});
const copiaR = (r) => new Reserva(r.id, r.socioId, r.libroId, r.fecha);

const activosDe = (socioId) => prestamosLista.filter((p) => p.socioId === socioId && p.activo);

// Reservas del libro por orden de llegada, sin las de quien ahora está sancionado
// (así una reserva no bloquea el libro para siempre).
const cola = (libroId, hoy) =>
  reservasLista.filter((r) => r.libroId === libroId && !socios.estaSancionado(r.socioId, hoy));

function comprobarPuedePedir(socioId, hoy) {
  const socio = socios.obtener(socioId); // lanza SocioNoEncontrado si no existe
  if (socios.estaSancionado(socioId, hoy)) {
    throw new SocioSancionado(`${socio.nombre} está sancionado hasta el ${formatear(socio.sancionadoHasta)}`);
  }
  return socio;
}

// ---- Interfaz pública ----
export function prestar(socioId, libroId, hoy) {
  const socio = comprobarPuedePedir(socioId, hoy);
  if (activosDe(socioId).length >= MAX_PRESTAMOS) {
    throw new LimitePrestamos(`${socio.nombre} ya tiene ${MAX_PRESTAMOS} libros prestados (máximo permitido)`);
  }

  const libro = catalogo.obtener(libroId);
  if (libro.disponibles === 0) {
    throw new LibroNoDisponible(`No quedan ejemplares de «${libro.titulo}». Puede reservarlo.`);
  }

  // Los ejemplares libres se retienen para quien reservó antes (por orden).
  const fila = cola(libroId, hoy);
  const posicion = fila.findIndex((r) => r.socioId === socioId);
  if (posicion !== -1) {
    if (posicion >= libro.disponibles) {
      throw new EjemplarReservado(`Aún no le toca a ${socio.nombre}: hay ${posicion} reserva(s) por delante`);
    }
  } else if (fila.length >= libro.disponibles) {
    throw new EjemplarReservado(`Los ejemplares libres de «${libro.titulo}» están retenidos para reservas`);
  }

  const ejemplarId = catalogo.marcarPrestado(libroId);
  if (posicion !== -1) reservasLista = reservasLista.filter((r) => r !== fila[posicion]); // se cumple

  const prestamo = new Prestamo(siguientePrestamo++, socioId, libroId, ejemplarId, hoy);
  prestamosLista.push(prestamo);
  return copiaP(prestamo);
}

export function devolver(prestamoId, hoy) {
  const prestamo = prestamosLista.find((p) => p.id === prestamoId && p.activo);
  if (!prestamo) throw new PrestamoNoEncontrado(`No hay ningún préstamo activo con id ${prestamoId}`);

  catalogo.marcarDevuelto(prestamo.ejemplarId);
  prestamo.fechaDevolucion = hoy;

  if (prestamo.diasRetraso > 0) {
    socios.sancionar(prestamo.socioId, sumarDias(hoy, prestamo.diasRetraso));
  }
  return copiaP(prestamo);
}

export function reservar(socioId, libroId, hoy) {
  const socio = comprobarPuedePedir(socioId, hoy);
  const libro = catalogo.obtener(libroId);
  const fila = cola(libroId, hoy);

  if (libro.disponibles > fila.length) {
    throw new ReservaInvalida(`«${libro.titulo}» tiene ejemplares libres: pídalo directamente`);
  }
  if (fila.some((r) => r.socioId === socioId)) {
    throw new ReservaInvalida(`${socio.nombre} ya tiene reservado «${libro.titulo}»`);
  }

  const reserva = new Reserva(siguienteReserva++, socioId, libroId, hoy);
  reservasLista.push(reserva);
  return copiaR(reserva);
}

export function cancelarReserva(reservaId) {
  if (!reservasLista.some((r) => r.id === reservaId)) {
    throw new ReservaInvalida(`No existe la reserva ${reservaId}`);
  }
  reservasLista = reservasLista.filter((r) => r.id !== reservaId);
}

export function prestamosActivos(socioId = null) {
  return prestamosLista
    .filter((p) => p.activo && (socioId === null || p.socioId === socioId))
    .map(copiaP);
}

export function reservas(libroId = null) {
  return reservasLista.filter((r) => libroId === null || r.libroId === libroId).map(copiaR);
}

// ---- Persistencia ----
export function exportarEstado() {
  return {
    siguientePrestamo,
    siguienteReserva,
    prestamos: prestamosLista.map(copiaP),
    reservas: reservasLista.map(copiaR),
  };
}

export function importarEstado(datos) {
  siguientePrestamo = datos.siguientePrestamo;
  siguienteReserva = datos.siguienteReserva;
  prestamosLista = datos.prestamos.map(copiaP);
  reservasLista = datos.reservas.map(copiaR);
}
