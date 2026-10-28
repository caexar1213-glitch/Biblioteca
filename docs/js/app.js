// Interfaz web. NO es un componente: solo une Catalogo, Socios y Prestamos
// y los muestra en pantalla, usando únicamente sus funciones públicas.

import * as catalogo from './catalogo.js';
import * as socios from './socios.js';
import * as prestamos from './prestamos.js';
import { hoyISO, sumarDias, diasEntre, formatear } from './fechas.js';

const CLAVE = 'biblioteca-barrio-v1';
const estado = { hoy: hoyISO(), socio: null, consulta: '' };

class AvisoUI extends Error {}

const $ = (sel) => document.querySelector(sel);
const esc = (t) => String(t).replace(/[&<>"']/g, (c) => (
  { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

// ------------------------------------------------------------------ datos
function datosDemo() {
  catalogo.agregarLibro('Don Quijote de la Mancha', 'Miguel de Cervantes', 3);
  catalogo.agregarLibro('Cien años de soledad', 'Gabriel García Márquez', 2);
  catalogo.agregarLibro('1984', 'George Orwell', 1);
  catalogo.agregarLibro('La sombra del viento', 'Carlos Ruiz Zafón', 2);
  catalogo.agregarLibro('Dune', 'Frank Herbert', 1);
  socios.alta('Ana Pérez');
  socios.alta('Luis Gómez');
}

function vaciar() {
  catalogo.importarEstado({ siguienteId: 1, libros: [] });
  socios.importarEstado({ siguienteId: 1, socios: [] });
  prestamos.importarEstado({ siguientePrestamo: 1, siguienteReserva: 1, prestamos: [], reservas: [] });
}

function guardar() {
  try {
    localStorage.setItem(CLAVE, JSON.stringify({
      hoy: estado.hoy,
      socio: estado.socio,
      catalogo: catalogo.exportarEstado(),
      socios: socios.exportarEstado(),
      prestamos: prestamos.exportarEstado(),
    }));
  } catch { /* sin almacenamiento: la app sigue funcionando en memoria */ }
}

function cargar() {
  try {
    const bruto = localStorage.getItem(CLAVE);
    if (!bruto) return false;
    const d = JSON.parse(bruto);
    catalogo.importarEstado(d.catalogo);
    socios.importarEstado(d.socios);
    prestamos.importarEstado(d.prestamos);
    const real = hoyISO();
    estado.hoy = d.hoy && d.hoy > real ? d.hoy : real;
    estado.socio = d.socio ?? null;
    return true;
  } catch {
    return false;
  }
}

// ------------------------------------------------------------------ avisos
let temporizador;
function aviso(texto, tipo) {
  const caja = $('#aviso');
  caja.textContent = texto;
  caja.className = tipo;
  caja.hidden = false;
  clearTimeout(temporizador);
  temporizador = setTimeout(() => { caja.hidden = true; }, 8000);
}

function ejecutar(accion) {
  try {
    const mensaje = accion();
    if (mensaje) aviso(mensaje, 'ok');
  } catch (e) {
    const conocido = e instanceof AvisoUI || e instanceof catalogo.CatalogoError
      || e instanceof socios.SociosError || e instanceof prestamos.PrestamosError;
    if (!conocido) throw e;
    aviso(e.message, 'error');
  }
  guardar();
  render();
}

function requiereSocio() {
  if (estado.socio === null) throw new AvisoUI('Elige primero un socio en «Operando como socio».');
  return estado.socio;
}

// ------------------------------------------------------------------ pintar
function renderBarra() {
  $('#fecha').value = estado.hoy;
  const lista = socios.listar();
  if (estado.socio !== null && !lista.some((s) => s.id === estado.socio)) estado.socio = null;
  $('#socio-actual').innerHTML = '<option value="">— elige un socio —</option>' + lista.map((s) => {
    const sancion = s.estaSancionado(estado.hoy) ? ` (sancionado hasta ${formatear(s.sancionadoHasta)})` : '';
    const marcado = s.id === estado.socio ? ' selected' : '';
    return `<option value="${s.id}"${marcado}>${esc(s.nombre)}${esc(sancion)}</option>`;
  }).join('');
}

function renderCatalogo() {
  const libros = catalogo.buscar(estado.consulta);
  if (libros.length === 0) {
    $('#resultados').innerHTML = '<p class="vacio">No hay libros que coincidan con la búsqueda.</p>';
    return;
  }
  $('#resultados').innerHTML = libros.map((l) => {
    const enCola = prestamos.reservas(l.id).length;
    const clase = l.disponibles > 0 ? 'ok' : 'mal';
    const chips = l.ejemplares.map((e) =>
      `<li class="ej ${e.estado}" title="Ejemplar ${esc(e.id)}">${esc(e.id)} · ${e.estado}</li>`).join('');
    return `
      <article class="libro">
        <div>
          <h3>${esc(l.titulo)}</h3>
          <p class="autor">${esc(l.autor)}</p>
          <ul class="ejemplares" aria-label="Ejemplares">${chips}</ul>
        </div>
        <div class="libro-accion">
          <div class="estado-libro">
            <span class="chip ${clase}">${l.disponibles}/${l.total} disponibles</span>
            ${enCola ? `<small>${enCola} reserva${enCola > 1 ? 's' : ''}</small>` : ''}
          </div>
          <button type="button" data-accion="prestar" data-id="${l.id}" ${l.disponibles === 0 ? 'disabled title="No quedan ejemplares"' : ''}>Prestar</button>
          <button type="button" class="secundario" data-accion="reservar" data-id="${l.id}">Reservar</button>
        </div>
      </article>`;
  }).join('');
}

function renderSocios() {
  const filas = socios.listar().map((s) => {
    const sancionado = s.estaSancionado(estado.hoy);
    const activos = prestamos.prestamosActivos(s.id).length;
    return `<tr>
      <td>${s.id}</td>
      <td>${esc(s.nombre)}</td>
      <td>${sancionado
        ? `<span class="chip mal">Sancionado hasta ${formatear(s.sancionadoHasta)}</span>`
        : '<span class="chip ok">Al día</span>'}</td>
      <td>${activos} / ${prestamos.MAX_PRESTAMOS}</td>
    </tr>`;
  }).join('');
  $('#tabla-socios').innerHTML = `
    <thead><tr><th>Id</th><th>Nombre</th><th>Estado</th><th>Libros en préstamo</th></tr></thead>
    <tbody>${filas || '<tr><td colspan="4" class="vacio">Aún no hay socios.</td></tr>'}</tbody>`;
}

function renderPrestamos() {
  const activos = prestamos.prestamosActivos();
  const filas = activos.map((p) => {
    const restan = diasEntre(estado.hoy, p.fechaVencimiento);
    const chip = p.estaVencido(estado.hoy)
      ? `<span class="chip mal">Vencido hace ${-restan} día${restan === -1 ? '' : 's'}</span>`
      : `<span class="chip ${restan <= 2 ? 'aviso' : 'ok'}">Quedan ${restan} día${restan === 1 ? '' : 's'}</span>`;
    return `<tr>
      <td>${esc(socios.obtener(p.socioId).nombre)}</td>
      <td>${esc(catalogo.obtener(p.libroId).titulo)}</td>
      <td>${esc(p.ejemplarId)}</td>
      <td>${formatear(p.fechaVencimiento)}</td>
      <td>${chip}</td>
      <td><button type="button" class="chico" data-accion="devolver" data-id="${p.id}">Devolver</button></td>
    </tr>`;
  }).join('');
  $('#tabla-prestamos').innerHTML = `
    <thead><tr><th>Socio</th><th>Libro</th><th>Ejemplar</th><th>Vence</th><th>Estado</th><th></th></tr></thead>
    <tbody>${filas || '<tr><td colspan="6" class="vacio">No hay préstamos activos.</td></tr>'}</tbody>`;

  const filasRes = prestamos.reservas().map((r) => `<tr>
      <td>${esc(socios.obtener(r.socioId).nombre)}</td>
      <td>${esc(catalogo.obtener(r.libroId).titulo)}</td>
      <td>${formatear(r.fecha)}</td>
      <td><button type="button" class="chico peligro" data-accion="cancelar" data-id="${r.id}">Cancelar</button></td>
    </tr>`).join('');
  $('#tabla-reservas').innerHTML = `
    <thead><tr><th>Socio</th><th>Libro</th><th>Reservado el</th><th></th></tr></thead>
    <tbody>${filasRes || '<tr><td colspan="4" class="vacio">No hay reservas.</td></tr>'}</tbody>`;
}

function render() {
  renderBarra();
  renderCatalogo();
  renderSocios();
  renderPrestamos();
}

// ------------------------------------------------------------------ eventos
document.addEventListener('click', (ev) => {
  const boton = ev.target.closest('[data-accion]');
  if (!boton) return;
  const id = Number(boton.dataset.id);

  switch (boton.dataset.accion) {
    case 'prestar':
      ejecutar(() => {
        const p = prestamos.prestar(requiereSocio(), id, estado.hoy);
        return `Préstamo registrado: «${catalogo.obtener(id).titulo}» (ejemplar ${p.ejemplarId}). Devolver antes del ${formatear(p.fechaVencimiento)}.`;
      });
      break;
    case 'reservar':
      ejecutar(() => {
        prestamos.reservar(requiereSocio(), id, estado.hoy);
        return `Reserva registrada: «${catalogo.obtener(id).titulo}».`;
      });
      break;
    case 'devolver':
      ejecutar(() => {
        const p = prestamos.devolver(id, estado.hoy);
        const titulo = catalogo.obtener(p.libroId).titulo;
        if (p.diasRetraso > 0) {
          const hasta = socios.obtener(p.socioId).sancionadoHasta;
          throw new AvisoUI(`«${titulo}» devuelto con ${p.diasRetraso} día(s) de retraso: el socio queda sancionado hasta el ${formatear(hasta)}.`);
        }
        return `«${titulo}» devuelto a tiempo.`;
      });
      break;
    case 'cancelar':
      ejecutar(() => { prestamos.cancelarReserva(id); return 'Reserva cancelada.'; });
      break;
    default:
  }
});

$('#buscador').addEventListener('input', (ev) => {
  estado.consulta = ev.target.value;
  renderCatalogo();
});

$('#form-socio').addEventListener('submit', (ev) => {
  ev.preventDefault();
  const campo = $('#nombre-socio');
  ejecutar(() => {
    const s = socios.alta(campo.value);
    campo.value = '';
    estado.socio = s.id;
    return `Socio dado de alta: ${s.nombre} (id ${s.id}).`;
  });
});

$('#socio-actual').addEventListener('change', (ev) => {
  estado.socio = ev.target.value === '' ? null : Number(ev.target.value);
  guardar();
});

$('#fecha').addEventListener('change', (ev) => {
  if (ev.target.value) estado.hoy = ev.target.value;
  guardar();
  render();
});

document.querySelectorAll('[data-dias]').forEach((b) => b.addEventListener('click', () => {
  estado.hoy = sumarDias(estado.hoy, Number(b.dataset.dias));
  guardar();
  render();
}));

$('#hoy-real').addEventListener('click', () => {
  estado.hoy = hoyISO();
  guardar();
  render();
});

$('#reiniciar').addEventListener('click', () => {
  if (!confirm('Se borrarán los datos actuales y se cargarán los de ejemplo. ¿Continuar?')) return;
  vaciar();
  datosDemo();
  estado.hoy = hoyISO();
  estado.socio = null;
  guardar();
  render();
  aviso('Datos de ejemplo restablecidos.', 'ok');
});

document.querySelectorAll('.pestana').forEach((tab) => tab.addEventListener('click', () => {
  document.querySelectorAll('.pestana').forEach((t) => t.setAttribute('aria-selected', String(t === tab)));
  document.querySelectorAll('.panel').forEach((p) => { p.hidden = p.id !== `panel-${tab.dataset.pestana}`; });
}));

// ------------------------------------------------------------------ arranque
if (!cargar()) {
  vaciar();
  datosDemo();
}
render();
