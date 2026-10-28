"""Pruebas de los tres componentes y de sus reglas.  Ejecutar:

    python3 -m unittest discover -s tests -v
"""

import importlib
import pathlib
import re
import sys
import unittest
from datetime import date, timedelta

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import catalogo  # noqa: E402
import prestamos  # noqa: E402
import socios  # noqa: E402

D0 = date(2026, 1, 10)


class Base(unittest.TestCase):
    def setUp(self):
        # Cada componente guarda su estado en el módulo: se recarga para empezar limpio.
        for modulo in (catalogo, socios, prestamos):
            importlib.reload(modulo)
        self.quijote = catalogo.agregar_libro("Don Quijote de la Mancha", "Cervantes", 2)
        self.dune = catalogo.agregar_libro("Dune", "Herbert", 1)
        self.orwell = catalogo.agregar_libro("1984", "Orwell", 1)
        self.sombra = catalogo.agregar_libro("La sombra del viento", "Ruiz Zafón", 1)
        self.ana = socios.alta("Ana").id
        self.luis = socios.alta("Luis").id
        self.eva = socios.alta("Eva").id


class TestCatalogo(Base):
    def test_buscar_ignora_tildes_y_mayusculas(self):
        self.assertEqual([l.id for l in catalogo.buscar("SOMBRA")], [self.sombra])
        self.assertEqual(len(catalogo.buscar("")), 4)
        self.assertEqual(catalogo.buscar("no existe"), [])

    def test_cada_ejemplar_tiene_su_propio_estado(self):
        e1 = catalogo.marcar_prestado(self.quijote)
        libro = catalogo.obtener(self.quijote)
        self.assertEqual(libro.total, 2)
        self.assertEqual(libro.disponibles, 1)
        estados = {e.id: e.estado for e in libro.ejemplares}
        self.assertEqual(estados[e1], catalogo.PRESTADO)
        self.assertEqual(sorted(estados.values()), [catalogo.DISPONIBLE, catalogo.PRESTADO])

    def test_sin_ejemplares(self):
        catalogo.marcar_prestado(self.dune)
        with self.assertRaises(catalogo.SinEjemplares):
            catalogo.marcar_prestado(self.dune)

    def test_obtener_devuelve_copia(self):
        libro = catalogo.obtener(self.dune)
        libro.ejemplares[0].estado = catalogo.PRESTADO
        libro.titulo = "Manipulado"
        self.assertEqual(catalogo.obtener(self.dune).disponibles, 1)
        self.assertEqual(catalogo.obtener(self.dune).titulo, "Dune")

    def test_libro_inexistente(self):
        with self.assertRaises(catalogo.LibroNoEncontrado):
            catalogo.obtener(999)


class TestPrestamos(Base):
    def test_prestamo_caduca_a_los_7_dias(self):
        p = prestamos.prestar(self.ana, self.dune, D0)
        self.assertEqual(p.fecha_vencimiento, D0 + timedelta(days=7))
        self.assertFalse(p.esta_vencido(D0 + timedelta(days=7)))
        self.assertTrue(p.esta_vencido(D0 + timedelta(days=8)))

    def test_maximo_dos_libros_a_la_vez(self):
        prestamos.prestar(self.ana, self.dune, D0)
        prestamos.prestar(self.ana, self.orwell, D0)
        with self.assertRaises(prestamos.LimitePrestamos):
            prestamos.prestar(self.ana, self.sombra, D0)

    def test_al_devolver_se_puede_pedir_otro(self):
        p1 = prestamos.prestar(self.ana, self.dune, D0)
        prestamos.prestar(self.ana, self.orwell, D0)
        prestamos.devolver(p1.id, D0 + timedelta(days=2))
        prestamos.prestar(self.ana, self.sombra, D0 + timedelta(days=2))
        self.assertEqual(len(prestamos.prestamos_activos(self.ana)), 2)

    def test_ejemplares_independientes(self):
        p1 = prestamos.prestar(self.ana, self.quijote, D0)
        p2 = prestamos.prestar(self.luis, self.quijote, D0)
        self.assertNotEqual(p1.ejemplar_id, p2.ejemplar_id)
        with self.assertRaises(prestamos.LibroNoDisponible):
            prestamos.prestar(self.eva, self.quijote, D0)
        prestamos.devolver(p1.id, D0 + timedelta(days=1))
        self.assertEqual(catalogo.obtener(self.quijote).disponibles, 1)
        prestamos.prestar(self.eva, self.quijote, D0 + timedelta(days=1))

    def test_devolucion_a_tiempo_no_sanciona(self):
        p = prestamos.prestar(self.ana, self.dune, D0)
        prestamos.devolver(p.id, D0 + timedelta(days=7))
        self.assertFalse(socios.esta_sancionado(self.ana, D0 + timedelta(days=7)))

    def test_devolucion_tardia_sanciona_y_bloquea(self):
        p = prestamos.prestar(self.ana, self.dune, D0)
        dev = D0 + timedelta(days=10)                 # vencía el día 7 -> 3 días de retraso
        devuelto = prestamos.devolver(p.id, dev)
        self.assertEqual(devuelto.dias_retraso, 3)
        self.assertTrue(socios.esta_sancionado(self.ana, dev))
        with self.assertRaises(prestamos.SocioSancionado):
            prestamos.prestar(self.ana, self.orwell, dev)
        with self.assertRaises(prestamos.SocioSancionado):
            prestamos.reservar(self.ana, self.dune, dev)
        # Pasada la sanción vuelve a poder pedir
        prestamos.prestar(self.ana, self.orwell, dev + timedelta(days=3))

    def test_devolver_dos_veces_falla(self):
        p = prestamos.prestar(self.ana, self.dune, D0)
        prestamos.devolver(p.id, D0)
        with self.assertRaises(prestamos.PrestamoNoEncontrado):
            prestamos.devolver(p.id, D0)

    def test_socio_o_libro_inexistente(self):
        with self.assertRaises(socios.SocioNoEncontrado):
            prestamos.prestar(999, self.dune, D0)
        with self.assertRaises(catalogo.LibroNoEncontrado):
            prestamos.prestar(self.ana, 999, D0)


class TestReservas(Base):
    def test_solo_se_reserva_si_esta_prestado(self):
        with self.assertRaises(prestamos.ReservaInvalida):
            prestamos.reservar(self.luis, self.dune, D0)       # libre: se pide directamente
        prestamos.prestar(self.ana, self.dune, D0)
        r = prestamos.reservar(self.luis, self.dune, D0)
        self.assertEqual(len(prestamos.reservas(self.dune)), 1)
        self.assertEqual(r.socio_id, self.luis)

    def test_no_se_reserva_dos_veces(self):
        prestamos.prestar(self.ana, self.dune, D0)
        prestamos.reservar(self.luis, self.dune, D0)
        with self.assertRaises(prestamos.ReservaInvalida):
            prestamos.reservar(self.luis, self.dune, D0)

    def test_el_ejemplar_devuelto_se_guarda_para_quien_reservo(self):
        p = prestamos.prestar(self.ana, self.dune, D0)
        prestamos.reservar(self.luis, self.dune, D0)
        prestamos.devolver(p.id, D0 + timedelta(days=1))
        with self.assertRaises(prestamos.EjemplarReservado):   # Eva se cuela: no puede
            prestamos.prestar(self.eva, self.dune, D0 + timedelta(days=1))
        prestamos.prestar(self.luis, self.dune, D0 + timedelta(days=1))
        self.assertEqual(prestamos.reservas(self.dune), [])    # la reserva se cumple

    def test_orden_de_la_cola(self):
        p = prestamos.prestar(self.ana, self.dune, D0)
        prestamos.reservar(self.luis, self.dune, D0)
        prestamos.reservar(self.eva, self.dune, D0)
        prestamos.devolver(p.id, D0 + timedelta(days=1))
        with self.assertRaises(prestamos.EjemplarReservado):   # Eva es la segunda
            prestamos.prestar(self.eva, self.dune, D0 + timedelta(days=1))

    def test_reserva_de_sancionado_no_bloquea_el_libro(self):
        p = prestamos.prestar(self.ana, self.dune, D0)
        prestamos.reservar(self.luis, self.dune, D0)
        socios.sancionar(self.luis, D0 + timedelta(days=30))
        prestamos.devolver(p.id, D0 + timedelta(days=1))
        prestamos.prestar(self.eva, self.dune, D0 + timedelta(days=1))

    def test_cancelar_reserva(self):
        prestamos.prestar(self.ana, self.dune, D0)
        r = prestamos.reservar(self.luis, self.dune, D0)
        prestamos.cancelar_reserva(r.id)
        self.assertEqual(prestamos.reservas(), [])


class TestArquitectura(unittest.TestCase):
    """Prestamos solo puede usar la interfaz pública de los otros componentes."""

    def test_prestamos_no_toca_el_interior_de_otros_componentes(self):
        fuente = (RAIZ / "prestamos.py").read_text(encoding="utf-8")
        accesos_privados = re.findall(r"\b(?:catalogo|socios)\._\w+", fuente)
        self.assertEqual(accesos_privados, [], "acceso a elementos privados")
        for prohibido in ("_libros", "_ejemplares", "_socios"):
            self.assertNotIn(prohibido, fuente)

    def test_catalogo_y_socios_no_dependen_de_nadie(self):
        for nombre in ("catalogo.py", "socios.py"):
            fuente = (RAIZ / nombre).read_text(encoding="utf-8")
            for otro in ("import prestamos", "import catalogo", "import socios"):
                if otro.endswith(nombre[:-3]):
                    continue
                self.assertNotIn(otro, fuente, f"{nombre} no debe depender de otros componentes")


if __name__ == "__main__":
    unittest.main()
