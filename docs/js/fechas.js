// Utilidades de fechas (no es un componente). Las fechas son cadenas ISO «AAAA-MM-DD».

const aUTC = (iso) => {
  const [y, m, d] = iso.split('-').map(Number);
  return Date.UTC(y, m - 1, d);
};

export function hoyISO() {
  const d = new Date();
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  return `${d.getFullYear()}-${mm}-${dd}`;
}

export function sumarDias(iso, n) {
  return new Date(aUTC(iso) + n * 86400000).toISOString().slice(0, 10);
}

export function diasEntre(desde, hasta) {
  return Math.round((aUTC(hasta) - aUTC(desde)) / 86400000);
}

export function formatear(iso) {
  const [y, m, d] = iso.split('-');
  return `${d}/${m}/${y}`;
}
