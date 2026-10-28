"""Biblioteca de barrio - aplicación de consola.

main.py NO es un componente: solo junta Catalogo, Socios y Prestamos y habla
con el usuario. Usa únicamente sus funciones públicas.

    python3 main.py
"""

from datetime import date, timedelta

import catalogo
import prestamos
import socios

ERRORES = (
    catalogo.CatalogoError,
    socios.SociosError,
    prestamos.PrestamosError,
    ValueError,
)

# Fecha «de hoy» de la aplicación. Se puede adelantar para probar la caducidad
# de los préstamos y las sanciones sin esperar días de verdad.
estado = {"hoy": date.today()}


def fmt(fecha):
    return fecha.strftime("%d/%m/%Y")


def datos_demo():
    """Algunos libros y socios para poder probar nada más arrancar."""
    catalogo.agregar_libro("Don Quijote de la Mancha", "Miguel de Cervantes", 3)
    catalogo.agregar_libro("Cien años de soledad", "Gabriel García Márquez", 2)
    catalogo.agregar_libro("1984", "George Orwell", 1)
    catalogo.agregar_libro("La sombra del viento", "Carlos Ruiz Zafón", 2)
    catalogo.agregar_libro("Dune", "Frank Herbert", 1)
    socios.alta("Ana Pérez")
    socios.alta("Luis Gómez")


# --------------------------------------------------------------------------
# Pantallas
# --------------------------------------------------------------------------
def mostrar_libros(libros):
    if not libros:
        print("  (no hay libros que coincidan)")
    for libro in libros:
        estados = ", ".join(f"{e.id}:{e.estado}" for e in libro.ejemplares)
        n_res = len(prestamos.reservas(libro.id))
        extra = f" · {n_res} reserva(s)" if n_res else ""
        print(f"  [{libro.id}] {libro.titulo} — {libro.autor}")
        print(f"       {libro.disponibles}/{libro.total} disponibles ({estados}){extra}")


def elegir_libro():
    texto = input("Título (o parte; vacío = todos): ")
    libros = catalogo.buscar(texto)
    mostrar_libros(libros)
    if not libros:
        return None
    return int(input("Id del libro: "))


def elegir_socio():
    for s in socios.listar():
        sancion = ""
        if socios.esta_sancionado(s.id, estado["hoy"]):
            sancion = f"  (sancionado hasta {fmt(s.sancionado_hasta)})"
        print(f"  [{s.id}] {s.nombre}{sancion}")
    return int(input("Id del socio: "))


def buscar_libro():
    texto = input("Título (o parte; vacío = todos): ")
    mostrar_libros(catalogo.buscar(texto))


def alta_socio():
    socio = socios.alta(input("Nombre del nuevo socio: "))
    print(f"  ✔ Socio dado de alta: [{socio.id}] {socio.nombre}")


def hacer_prestamo():
    libro_id = elegir_libro()
    if libro_id is None:
        return
    socio_id = elegir_socio()
    p = prestamos.prestar(socio_id, libro_id, estado["hoy"])
    print(f"  ✔ Préstamo {p.id} (ejemplar {p.ejemplar_id}). "
          f"Devolver antes del {fmt(p.fecha_vencimiento)}.")


def devolver_libro():
    ver_prestamos()
    if not prestamos.prestamos_activos():
        return
    p = prestamos.devolver(int(input("Id del préstamo a devolver: ")), estado["hoy"])
    print("  ✔ Devuelto.")
    if p.dias_retraso:
        hasta = socios.obtener(p.socio_id).sancionado_hasta
        print(f"  ⚠ {p.dias_retraso} día(s) de retraso: socio sancionado hasta {fmt(hasta)}.")


def reservar_libro():
    libro_id = elegir_libro()
    if libro_id is None:
        return
    socio_id = elegir_socio()
    r = prestamos.reservar(socio_id, libro_id, estado["hoy"])
    print(f"  ✔ Reserva {r.id} registrada.")


def ver_prestamos():
    activos = prestamos.prestamos_activos()
    if not activos:
        print("  (no hay préstamos activos)")
    for p in activos:
        titulo = catalogo.obtener(p.libro_id).titulo
        nombre = socios.obtener(p.socio_id).nombre
        aviso = "  ⚠ VENCIDO" if p.esta_vencido(estado["hoy"]) else ""
        print(f"  [{p.id}] {nombre} — «{titulo}» (ej. {p.ejemplar_id}) "
              f"vence {fmt(p.fecha_vencimiento)}{aviso}")
    for r in prestamos.reservas():
        titulo = catalogo.obtener(r.libro_id).titulo
        nombre = socios.obtener(r.socio_id).nombre
        print(f"  reserva [{r.id}] {nombre} espera «{titulo}»")


def avanzar_dias():
    dias = int(input("¿Cuántos días adelantar la fecha? "))
    estado["hoy"] += timedelta(days=dias)
    print(f"  Fecha de la aplicación: {fmt(estado['hoy'])}")


MENU = """
=== Biblioteca de barrio · hoy es {hoy} ===
 1. Buscar un libro
 2. Dar de alta un socio
 3. Hacer un préstamo
 4. Devolver un libro
 5. Reservar un libro
 6. Ver préstamos y reservas
 7. Adelantar la fecha (simulación)
 0. Salir"""

ACCIONES = {
    "1": buscar_libro,
    "2": alta_socio,
    "3": hacer_prestamo,
    "4": devolver_libro,
    "5": reservar_libro,
    "6": ver_prestamos,
    "7": avanzar_dias,
}


def main():
    datos_demo()
    while True:
        print(MENU.format(hoy=fmt(estado["hoy"])))
        try:
            opcion = input("Opción: ").strip()
        except EOFError:
            break
        if opcion == "0":
            break
        accion = ACCIONES.get(opcion)
        if accion is None:
            print("  Opción no válida")
            continue
        try:
            accion()
        except ERRORES as error:
            print(f"  ✖ {error}")
        except EOFError:
            break
    print("¡Hasta pronto!")


if __name__ == "__main__":
    main()
