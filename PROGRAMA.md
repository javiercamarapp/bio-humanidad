# Programa de ejecución — fase operativa

## Tanda de continuación — 2026-09-19, 18:54 UTC

Alcance: terminar `bio.vigilar` (ingesta pública y preparación, no investigación).
Presupuesto de construcción: máximo 3 cambios funcionales, 35 minutos, USD 0 en APIs;
parada tras 2 intentos consecutivos sin mejora, conflicto concurrente o permisos.
Métrica fija: fallos de `python3 -m unittest discover -s tests -v`, dirección descendente;
reproducción inicial del vigilante: 16 pruebas, 1 fallo de suspensión. No se borran,
debilitan ni saltan pruebas existentes. Se añaden regresiones antes de nuevos arreglos.
Guardias: datos/revisiones humanos intactos, `publicable:false`, sin modelos ni alertas.
Mutables: `bio/vigilar.py`, regresiones nuevas y documentación de uso/evidencia.
Reversión: retirar únicamente el parche propio fallido; preservar los dos archivos
previos no versionados y todos los resultados, nunca reset destructivo.
Operación posterior a suite verde y revisión de límites: máximo una corrida de red,
1 vuelta / 90 segundos; hasta 2 corridas offline de 2 vueltas / 10 segundos.
No ejecutar el vigilante mientras se edita código. Cada corrida usa carpeta nueva;
no inventar reanudación: el vigilante no la soporta, `bio.bucle` sí.
Commits sustantivos, push no forzado y PR están autorizados por el traspaso. Remoto
comprobado PUBLIC, main y feat/radar-reproducible en `18b7088`; no cambiar identidad,
permisos, facturación ni visibilidad. Los límites de no publicación automática de
candidatos del programa original siguen vigentes. Registrar resultado y parada en
`ESTADO.md`. Revisión de código: un evaluador con contexto limpio mediante Codex
(sesión existente ChatGPT, sin API key), máximo una invocación, concurrencia 1,
4 minutos, sin reintentos ni cambios de código. No es un componente del radar.
La cuenta puede consumir su cuota existente; no se cambia facturación ni se contrata
capacidad adicional. Sin revisor disponible, declarar la revisión pendiente.

## Objetivo de esta sesión
Implementar y probar un consumidor acotado de candidatos, no un descubridor autónomo.
Orden: pruebas de regresión → validador conservador → bucle persistente → pruebas
integrales → ejecución sobre la carpeta real → informe del bloqueo o resultado.
Sin publicar, contactar terceros, instalar modelos ni usar APIs de pago.

## Contrato del bucle
- Entrada: candidatos Markdown en `salidas/hipotesis/`.
- El bucle NO genera nuevas hipótesis ni altera las existentes. Analista, extractor,
  refutador y detector siguen siendo componentes pendientes, no simulados.
- Métrica: número de candidatos con revisión humana vigente y controles técnicos
  superados. Dirección ascendente. NO mide verdad científica, descubrimientos ni
  precisión de un extractor.
- Comando: `python3 -m bio.bucle --max-vueltas 200 --max-segundos 900`.
- Reanudación: `python3 -m bio.bucle --reanudar salidas/bucle/<id>`.
- Sin red: añadir `--sin-red`; no permite aceptar evidencia como revalidada.

## Guardias
1. Al menos 50 señales con etiquetas humanas completas en
   `datos/dorado/senales.jsonl`. Su integridad no equivale a medir un extractor.
2. Revisión humana de cada candidato en `datos/revisiones/<sha256>.json`, ligada
   al hash exacto de su contenido. El agente no escribe estas aprobaciones.
3. Verificar citas textuales en fuentes HTTPS permitidas, con límites de lectura y
   tiempo. Una coincidencia literal NO prueba que la fuente respalde una conclusión;
   eso sigue siendo una responsabilidad de la revisión humana.
4. Duplicación léxica contra candidatos aceptados; no se promete novedad científica.
5. Cambiar código, pruebas, alcance, programa, conjunto dorado o revisiones durante
   una corrida detiene el bucle. El código de validación nunca es modificado por él.
6. Ningún candidato se publica automáticamente ni se ejecuta como código.

## Mutables y reversión
Solo `salidas/bucle/<id>/**`: snapshots, registros por intento y estado. Un intento
se conserva con su veredicto; los rechazados NO se borran. No se hacen resets de Git.
Los candidatos originales y todos los demás archivos son de solo lectura.
La persistencia por intento es atómica; un intento incompleto no cuenta como aceptado.

## Presupuesto
Máximo 200 intentos, 900 segundos por defecto (techo absoluto 14 días),
30 segundos por intento y parada tras 25 intentos sin mejora.
Costo de APIs: USD 0; no se llama ningún modelo ni servicio de pago.
El tiempo total incluye pausas entre reanudaciones. No hay reinicio de presupuesto.

## Paradas
Conjunto dorado ausente/inválido; revisión humana pendiente; alcance no aprobado;
archivos protegidos alterados; cola agotada; presupuesto; estancamiento; error de
estado. Dos procesos no pueden escribir la misma corrida simultáneamente.
No se finge una corrida activa si el proceso terminó o encontró una guardia.

## Verificación y límites
`python3 -m unittest discover -s tests -v` prueba controles con fixtures sintéticos.
La ejecución real informa intentos, retenidos, descartados y motivo de parada.
No se fabricarán etiquetas humanas para lograr un resultado verde.
Una revisión independiente de código sigue pendiente si no hay revisor disponible.
