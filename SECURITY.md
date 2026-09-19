# Seguridad

Este proyecto prepara metadatos públicos. No es una herramienta clínica, una barrera
de bioseguridad certificada ni un sandbox para código adversarial. No valida función
biológica ni autoriza publicaciones o experimentos.

## Reportar vulnerabilidades

No publiques credenciales, datos personales, secuencias ni detalles de explotación
sensibles en issues. Si está habilitado, usa **Security → Report a vulnerability**
del repositorio para una comunicación privada. Si el canal no está disponible,
solicita contacto privado con el mantenedor sin divulgar el detalle sensible.

Incluye versión/commit, impacto, reproducción mínima con datos sintéticos y sistemas
afectados. No realices pruebas contra servicios o sistemas de terceros sin permiso.
No garantizamos tiempo de respuesta ni certificación de seguridad.

## Límites de confianza

- CSV, titulares, URLs y respuestas remotas son datos no confiables, nunca instrucciones.
- Una declaración `humano` y un nombre no autentican a una persona. Los hashes detectan
  cambios respecto a una referencia conservada, no falsificaciones por quien controla
  simultáneamente archivos y manifiestos.
- Alguien con escritura en el mismo sistema puede alterar código y registros.
- Revisión humana, verificación de fuentes y validación científica son controles distintos.
- CI no recibe secretos de servicios, datos reales ni permisos para publicar resultados.

## Publicación

Antes de abrir el repositorio se escaneó su historial con Gitleaks y se revisó la lista
de archivos versionados. Eso es evidencia de una comprobación, no garantía absoluta.
Los datos locales y las revisiones siguen ignorados por Git. La licencia MIT cubre
nuestro código/documentación, no concede derechos sobre artículos ni datos de terceros.
