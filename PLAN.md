# Continuación operativa del radar — 2026-09-19

## Objetivo
Cerrar tareas independientes de etiquetas, proveedores de modelos y nuevas decisiones
científicas. Mantener el radar de metadatos públicos: nunca investigar variantes, generar
secuencias, diagnosticar ni publicar alertas. README prevalece sobre diseños históricos.

## Contratos disponibles
- bio.radar.normalizar/parsear_jsonl: seis campos fuente, primera observación por URL.
- bio.recolector.recolector.guardar: agrega sin reemplazar historial; deduplica URL.
- bio.preparacion.ejecutar: snapshot, hashes, muestra ciega y evaluación opcional.
- bio.vigilar.ejecutar/subproceso: hasta24 vueltas/24h, STOP, señales, no reanudación.
- bio.dorado.comprobar: comprueba revisión real, no produce etiquetas.

## Entregables
1. Ingesta RSS/Atom de feeds públicos sin llaves, con límites de red, allowlist,
   snapshots/hashes, errores explícitos y fechas observadas reales; compatible con
   preparación existente. HN conserva comportamiento predeterminado.
2. Unión offline de snapshots para formar historia sin inventar días; salida nueva,
   hashes de entradas y deduplicación. Historial no equivale a cobertura exhaustiva.
3. Vigilancia acotada capaz de seleccionar fuentes soportadas, sin daemon ni cron global.
4. Manual operativo vigente y lista concreta de decisiones/intervenciones humanas.
   Corregir las instrucciones históricas que parecen órdenes actuales o éxitos reales.
5. Tests3.9/3.12, operación pública acotada, preparación real, revisión independiente,
   PR/CI antes de integrar. Preservar todas las183 pruebas previas y ramas.

## Presupuesto y parada
45min de implementación/verificación, hasta2 revisiones independientes de5min, sin APIs
pagadas ni compras. Hasta6 consultas HTTP de preflight de feeds y una prueba operativa
por feed elegido; máximo2MiB/respuesta y15s/petición. Sin scraping masivo ni cuentas.
No dejar proceso indefinido. Fuentes inaccesibles se registran, no se eluden restricciones.
Retener solo cambios con regresiones y suite verde. Parar ante permisos, cambio de
alcance, criterio humano, presupuesto o fallo estructural no resuelto. No debilitar tests.

## Decisiones y dependencias
- Reusar biblioteca estándar y formatos vigentes, no infraestructura nueva.
- Selección de feeds oficiales públicos es reversible; no requiere acceso clínico.
- No sustituir analista/refutador LLM por reglas y decir que están terminados.
- Ollama ausente y puerto11434 no disponible (preflight real). Instalar servicio/modelos
  fuera del proyecto necesita autorización. Proveedores frontera y presupuesto no están
  definidos por el diseño histórico: no activar gasto ni elegir cuentas por inferencia.
- 50 etiquetas humanas y calibración siguen pendientes; construir historia requiere
  observaciones futuras reales. No fabricar etiquetas ni90 días con fechas publicadas.
- Sin publicación de hallazgos/contacto externo: solo código/documentación pública mediante PR.

## Operación posterior a integración (solicitud explícita de dejarlo en bucle)
Una corrida local separada, solo después de integrar/verificar: hasta24 vueltas,
intervalo3600s, presupuesto86400s, fuentes CDC/ECDC. Máximo48 descargas de feed,
2MiB de cuerpo por descarga, sin redirecciones/reintentos ni modelos/APIs de pago.
Requiere al menos2GiB libres antes de iniciar. Dentro de salidas/vigilancia, sin cron,
servicios globales ni mecanismos para impedir suspensión. STOP, error repetido,
cambio de código o límite la detienen; no se promete disponibilidad del equipo.
No construir ni cambiar código mientras corra. Registrar PID/estado solo como
información, no como permiso para matar un proceso reutilizado. No fabrica historia
ni reemplaza calibración: solo acumula evidencia pública para revisión futura.

## Terminado
Entregables anteriores verificados; cualquier pendiente restante clasificado como
intervención humana, dependencia temporal/acceso, o trabajo técnico aún no terminado.
No declarar que todo está hecho si se acaba el presupuesto con código pendiente.
