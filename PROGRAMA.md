# Programa de ejecución — fase operativa

## Cierre de portabilidad y CI — 2026-09-19, 21:49 UTC

Nueva solicitud de continuar. Techo declarado:20min, una revisión de hasta5min, sin
ingesta ni APIs de pago. Antes de revisar, la suite real detectó E2E intermitente en
macOS3.9: origen monotónico privado del proceso. Se declaró un único parche acotado,
se reprodujo en rojo y se sustituyó por CLOCK_MONOTONIC compartido; tres pruebas nuevas,
ninguna anterior debilitada. La enmienda previa y evidencia permanecen en
`salidas/verificacion/cierre-ci-20260919-2149/PROGRAMA.md`.

183 pruebas reales OK por Python, local y CI del código e00f0e7. El revisor no encontró
otro bloqueo de código; exigió probar identidad del árbol del merge CI. Se descargó
ese objeto y se verificó igualdad exacta del árbol38aced91ce1bf514ec06fd8d57bd3b8a8fbf6b58.
Condición satisfecha sin repetir revisores, simular CI ni cambiar permisos. Bajo la
autorización existente: integrar PR1 hacia main con SHA esperado, sin admin ni force;
comprobar CI de la documentación final y del main resultante, conservar ramas/datos.
No más parches en esta tanda. Detener ante checks fallidos, cambios concurrentes,
falta de permisos o gate humano. Las50 etiquetas reales continúan pendientes.

## Tanda de protocolo de confirmación — 2026-09-19, 20:53 UTC

Nueva solicitud de continuar hasta cerrar. Presupuesto local declarado antes de ejecutar:
30 minutos, corrección del protocolo del issue #2, sin ingesta ni APIs de pago. Tras
la primera revisión y reproducciones nuevas, se declaró una segunda y última revisión
del diseño ampliado, hasta5 minutos, dentro del mismo techo de30 minutos. No se repitió
el mismo código buscando aprobación. Evidencia y enmienda originales:
`salidas/verificacion/correccion-confirmacion-20260919-2053/PROGRAMA.md`.

Guardias: mantener las171 pruebas previas, agregar regresiones en rojo, suites3.9/3.12,
ninguna etiqueta humana inventada. Diseño: confirmar dentro del presupuesto incluyendo
limpieza, restaurar bloqueo ante error/cancelación, no recuperar automáticamente una
cola ACEPTADA, conservar origen monotónico e identificador de arranque entre procesos.
Arranque cambiado/no verificable bloquea, nunca renueva presupuesto.

Resultado:180 pruebas locales OK por versión. Revisión final: NO INTEGRAR por consulta
de arranque denegada en su sandbox; lógica comprobada con arranque simulado, no sustituto
del E2E real. No cambiar permisos ni agotar revisores para obtener verde. Publicar el
parche mediante push no forzado a la PR borrador; no integrar mientras falte completar
esa revisión y verificar CI del SHA exacto. Mantener datos e históricos intactos.

## Tanda de cierre integral — 2026-09-19, 19:49 UTC

Nueva solicitud: cerrar de punta a punta la entrega técnica y la integración pendiente.
Alcance ya construido: radar público HN, preparación, revisión/importación, evaluación,
consumidor de candidatos y vigilante finito. No ampliar a investigación científica,
modelos, fuentes adicionales ni producción sanitaria por inferencia.

- Presupuesto: 40 minutos, hasta 3 correcciones funcionales y 2 revisiones independientes
  de 5 minutos cada una, concurrencia de revisores 1; sin APIs de pago ni compras.
  Revisores por sesión ChatGPT existente de Codex; puede consumir su cuota, no se cambia
  facturación. Máximo 1 ingesta de red de 1 vuelta/90 s y 2 pruebas operativas offline.
- Métrica: defectos bloqueantes reproducidos pendientes, dirección descendente; guardia
  fija `python3 -m unittest discover -s tests -v` en 3.9 y 3.12 sin eliminar, debilitar
  ni saltar pruebas existentes. Añadir regresiones o integración donde falte evidencia.
- Revisor: copia aislada solo de archivos versionados dentro de `salidas/verificacion/`,
  con temporales escribibles. Sin datos reales, acceso a otros proyectos ni mutaciones
  de fuentes. Contrastar hashes para detectar cualquier modificación del revisor.
- Mutables: correcciones de defectos demostrados en `bio/`, nuevas pruebas y documentación;
  protegidos: datos, etiquetas/aprobaciones humanas, reglas de alcance, pruebas anteriores.
- Retener solo cambios con regresión verde y suite completa; retirar únicamente el
  parche propio fallido, sin resets destructivos ni eliminar evidencia de fallos.
- Parar por 2 intentos consecutivos sin mejora, presupuesto, conflicto concurrente,
  permisos o gate humano. No activar un daemon ni dejar el loop sin límite.
- Integración: revalidar PR #1 hacia `main`; solo integrar tras revisión independiente
  sin bloqueantes, pruebas locales y checks remotos verdes del SHA exacto. Sin forzar,
  usar privilegios de administrador ni modificar protecciones. Comprobar CI en `main`
  tras integrar; conservar las ramas y datos locales.
- Terminado técnico: flujo sintético E2E verificable, corrida operativa no publicable,
  documentación utilizable, entrega humana local preparada, PR integrada y CI remoto.
  No equivale a precisión científica ni a 50 etiquetas humanas completadas. Esos gates
  solo los resuelve una persona; comprobar que permanecen cerrados.


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
