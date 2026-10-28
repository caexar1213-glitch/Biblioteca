# Diario de desarrollo — Biblioteca de barrio

## Decisión sobre la petición del cliente

> «Para ir más rápido, que Prestamos lea directamente la lista de libros de Catalogo.»

**Decisión: no lo hago.** Si Prestamos leyera la lista interna de Catalogo, dependería de cómo guarda los libros ese componente, y cualquier cambio en él (por ejemplo, añadir ejemplares o pasar a una base de datos) rompería Prestamos sin avisar. En su lugar Prestamos usa solo `obtener(id)`, `marcar_prestado(id)` y `marcar_devuelto(id)`, que son igual de rápidos de usar; si algún día hace falta algo más, se añade una función pública a Catalogo.

## Registro de trabajo

- **Paso 1 — Reparto de responsabilidades.** Tres componentes: Catalogo (libros y ejemplares), Socios (fichas y sanciones) y Prestamos (préstamos y reservas). `main.py` solo los junta y habla con el usuario.
- **Paso 2 — Interfaces públicas.** Cada componente declara qué ofrece (`__all__`); lo que empieza por `_` es interior. Las funciones devuelven copias para que nadie modifique el estado desde fuera.
- **Paso 3 — Dependencias.** Solo Prestamos depende de otros (Catalogo y Socios). Catalogo y Socios no dependen de nadie. Una prueba automática comprueba que `prestamos.py` no toca nada privado de los otros.
- **Paso 4 — Reglas extra.** Máximo 2 libros por socio, préstamo de 7 días, ejemplares con estado propio, socios sancionados (por devolver tarde) que no pueden pedir ni reservar, y reservas con cola por orden de llegada.
- **Paso 5 — Versión web.** Misma arquitectura (tres módulos y una interfaz) publicada en GitHub Pages.
