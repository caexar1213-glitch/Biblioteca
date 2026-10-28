// Pruebas de los tres módulos de la versión web.   Ejecutar:  cd docs && node --test test/

import { test, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

import * as catalogo from '../js/catalogo.js';
import * as socios from '../js/socios.js';
import * as prestamos from '../js/prestamos.js';
import { sumarDias } from '../js/fechas.js';

const D0 = '2026-01-10';
let quijote, dune, orwell, sombra, ana, luis, eva;

beforeEach(() => {
  catalogo.importarEstado({ siguienteId: 1, libros: [] });
  socios.importarEstado({ siguienteId: 1, socios: [] });
  prestamos.importarEstado({ siguientePrestamo: 1, siguienteReserva: 1, prestamos: [], reservas: [] });
  quijote = catalogo.agregarLibro('Don Quijote de la Mancha', 'Cervantes', 2);
  dune = catalogo.agregarLibro('Dune', 'Herbert', 1);
  orwell = catalogo.agregarLibro('1984', 'Orwell', 1);
  sombra = catalogo.agregarLibro('La sombra del viento', 'Ruiz Zafón', 1);
  ana = socios.alta('Ana').id;
  luis = socios.alta('Luis').id;
  eva = socios.alta('Eva').id;
});

test('buscar ignora tildes y mayúsculas', () => {
  assert.deepEqual(catalogo.buscar('SOMBRA').map((l) => l.id), [sombra]);
  assert.equal(catalogo.buscar('').length, 4);
  assert.equal(catalogo.buscar('no existe').length, 0);
});

test('cada ejemplar tiene su propio estado', () => {
  const e1 = catalogo.marcarPrestado(quijote);
  const libro = catalogo.obtener(quijote);
  assert.equal(libro.total, 2);
  assert.equal(libro.disponibles, 1);
  assert.equal(libro.ejemplares.find((e) => e.id === e1).estado, catalogo.PRESTADO);
});

test('obtener devuelve una copia', () => {
  const libro = catalogo.obtener(dune);
  libro.ejemplares[0].estado = catalogo.PRESTADO;
  assert.equal(catalogo.obtener(dune).disponibles, 1);
});

test('el préstamo caduca a los 7 días', () => {
  const p = prestamos.prestar(ana, dune, D0);
  assert.equal(p.fechaVencimiento, sumarDias(D0, 7));
  assert.equal(p.estaVencido(sumarDias(D0, 7)), false);
  assert.equal(p.estaVencido(sumarDias(D0, 8)), true);
});

test('máximo dos libros a la vez', () => {
  prestamos.prestar(ana, dune, D0);
  prestamos.prestar(ana, orwell, D0);
  assert.throws(() => prestamos.prestar(ana, sombra, D0), prestamos.LimitePrestamos);
});

test('ejemplares independientes del mismo título', () => {
  const p1 = prestamos.prestar(ana, quijote, D0);
  const p2 = prestamos.prestar(luis, quijote, D0);
  assert.notEqual(p1.ejemplarId, p2.ejemplarId);
  assert.throws(() => prestamos.prestar(eva, quijote, D0), prestamos.LibroNoDisponible);
  prestamos.devolver(p1.id, sumarDias(D0, 1));
  assert.equal(catalogo.obtener(quijote).disponibles, 1);
});

test('devolver tarde sanciona y bloquea pedir y reservar', () => {
  const p = prestamos.prestar(ana, dune, D0);
  const dev = sumarDias(D0, 10); // vencía el día 7 -> 3 días de retraso
  assert.equal(prestamos.devolver(p.id, dev).diasRetraso, 3);
  assert.equal(socios.estaSancionado(ana, dev), true);
  assert.throws(() => prestamos.prestar(ana, orwell, dev), prestamos.SocioSancionado);
  assert.throws(() => prestamos.reservar(ana, dune, dev), prestamos.SocioSancionado);
  prestamos.prestar(ana, orwell, sumarDias(dev, 3)); // pasada la sanción, vuelve a poder
});

test('devolver a tiempo no sanciona', () => {
  const p = prestamos.prestar(ana, dune, D0);
  prestamos.devolver(p.id, sumarDias(D0, 7));
  assert.equal(socios.estaSancionado(ana, sumarDias(D0, 7)), false);
});

test('solo se reserva un libro ya prestado', () => {
  assert.throws(() => prestamos.reservar(luis, dune, D0), prestamos.ReservaInvalida);
  prestamos.prestar(ana, dune, D0);
  prestamos.reservar(luis, dune, D0);
  assert.equal(prestamos.reservas(dune).length, 1);
  assert.throws(() => prestamos.reservar(luis, dune, D0), prestamos.ReservaInvalida);
});

test('el ejemplar devuelto se guarda para quien reservó, por orden', () => {
  const p = prestamos.prestar(ana, dune, D0);
  prestamos.reservar(luis, dune, D0);
  prestamos.reservar(eva, dune, D0);
  const dia = sumarDias(D0, 1);
  prestamos.devolver(p.id, dia);
  assert.throws(() => prestamos.prestar(eva, dune, dia), prestamos.EjemplarReservado); // Eva es la segunda
  prestamos.prestar(luis, dune, dia);
  assert.equal(prestamos.reservas(dune).length, 1);
});

test('la reserva de un sancionado no bloquea el libro', () => {
  const p = prestamos.prestar(ana, dune, D0);
  prestamos.reservar(luis, dune, D0);
  socios.sancionar(luis, sumarDias(D0, 30));
  const dia = sumarDias(D0, 1);
  prestamos.devolver(p.id, dia);
  prestamos.prestar(eva, dune, dia);
});

test('arquitectura: Prestamos solo usa la interfaz pública de los otros componentes', () => {
  const fuente = readFileSync(new URL('../js/prestamos.js', import.meta.url), 'utf8');
  const importaciones = [...fuente.matchAll(/import\s+(.+?)\s+from\s+'(.+?)'/g)].map((m) => m[2]);
  assert.deepEqual(importaciones.sort(), ['./catalogo.js', './fechas.js', './socios.js']);
  assert.equal(/catalogo\.(libros|ejemplares)\b|socios\.socios\b/.test(fuente), false);
});

test('arquitectura: Catalogo y Socios no dependen de nadie', () => {
  for (const f of ['catalogo.js', 'socios.js']) {
    const fuente = readFileSync(new URL(`../js/${f}`, import.meta.url), 'utf8');
    assert.equal(/^import /m.test(fuente), false, `${f} no debe importar nada`);
  }
});
