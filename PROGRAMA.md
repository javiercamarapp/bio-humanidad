# Programa de ejecución — fase operativa

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
