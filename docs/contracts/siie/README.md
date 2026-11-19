# Entregas documentales SIIE

Los archivos del proveedor son contratos y evidencia de lo que declara; no autorizan escrituras ni acreditan publicación remota o aceptación de RinovaPlus.

| Entrega | Contenido | Estado |
|---|---|---|
| `20261119/` | Primer contrato de estudiantes/contactos y período ofrecido, todavía con dos credenciales. | Versión previa conservada. |
| `20261119-single-key/` | Inventario de 21 operaciones, guía y colección con una sola `apiKey`. | Entrega vigente para adaptar y probar; disponibilidad pública pendiente de validación propia. |

SHA-256 de la entrega de clave única:

- `API_INVENTORY.md`: `5ee628e2cfe45cf26ecb0da38d06fbb4c280756e445e0c9a4f806d3b0c3bfed8`.
- `GUIA_API_CRM_SIIE.md`: `0c374e5a51f4423416d3cc291f83d4f8a6bf4c30ee1eb1c750d63532e8133878`.
- `SIIE_CRM.postman_collection.json`: `5d29f6fd2ffb38f997bb8e62d85bfc9e1b638a4b1b5ac283374f6397f75e4bce`.

Se verificaron 21 solicitudes y variables de credencial vacías en la colección nueva. El consumidor CRM ofrece 12 GET, no las 21 operaciones: no habilita POST/PUT de seguimiento o preinscripción ni convierte las consultas Moodle en una ficha CRM. La clave del proveedor sí tiene capacidad de escritura; la restricción de este adaptador es de método/ruta, no una afirmación de que el token sea de sólo lectura.
