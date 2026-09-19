# 11 — Pipeline de preparación offline

Este paso ya ejecuta código: lee señales locales, las normaliza, propone categorías
por reglas, prepara una muestra ciega para revisión y escribe un informe auditable.
No es un descubridor autónomo, no usa un LLM y no sustituye al pipeline científico
previsto en `04-ARQUITECTURA-ORQUESTACION.md`.

## Ejecutar

```bash
cd ~/Desktop/"bio humanidad"
python3 -m bio.preparacion \
  --entrada datos/senales/senales.jsonl \
  --salida salidas/preparacion/mi-corrida \
  --corte 2026-09-20
```

`--corte` es una fecha UTC **exclusiva**: 2026-09-20 incluye las observaciones hasta
2026-09-19. Usa el corte apropiado para tu análisis; los datos del día en curso pueden
estar incompletos. El radar no interpreta fechas antiguas de publicación como meses
de historia recolectada.

La salida debe ser una carpeta nueva: no se sobrescribe una corrida anterior.
Se requieren al menos 50 señales para la muestra predeterminada; `--cantidad N`
permite una muestra menor para pruebas, **sin reducir el mínimo de 50 del dorado**.
Límites de entrada: 10 MB y 5000 señales únicas.

## Qué produce

| Archivo | Contenido |
|---|---|
| `entrada.jsonl` | Snapshot de los bytes de entrada |
| `normalizadas.jsonl` | Campos fuente normalizados, sin aprobaciones importadas |
| `predicciones.jsonl` | Sugerencias automáticas y abstenciones; nunca etiquetas humanas |
| `deteccion.json` | Comparación léxica o abstención por historia insuficiente |
| `metricas.json` | Evaluación contra dorado existente, o métricas `null` si falta |
| `revision/revision.csv` | Muestra con campos humanos vacíos |
| `revision/muestra.jsonl` | Snapshot de campos fuente para cotejar el CSV |
| `informe.md` | Resumen y límites explícitos |
| `manifest.json` | Estado, hashes de artefactos/entrada/código y duración |

El manifiesto se escribe al final. Si cambia el código durante la preparación, no se
emite manifiesto final. Una carpeta sin él puede ser una corrida interrumpida: no se
interpreta como éxito ni se sobrescribe automáticamente.

## Dos éxitos distintos

`PREPARACION_COMPLETA` / código de salida 0 significa **archivos de preparación
producidos**, no calidad científica ni autorización de publicar. Se reporta por
separado `estado_validacion`:

- `PENDIENTE_DORADO`: no existe el conjunto de etiquetas humanas. Exactitud y cobertura
  de evaluación son `null`, no 0 ni 100%.
- `EVALUADO_TECNICAMENTE`: se calculó concordancia con al menos 50 casos humanos
  registrados. Eso no autentica a los revisores ni verifica verdad de titulares.

`publicable` siempre es `false`: faltan verificación de fuentes, refutación y decisión
humana. Un JSONL corrupto, dorado inválido o salida preexistente produce error, no una
entrega aprobada. El pipeline no llama al bucle de hipótesis ni lo desbloquea.

## Extractor de referencia, no IA

`bio/extractor.py` usa coincidencias léxicas explícitas y versionadas (`reglas_v1`).
Una sola categoría coincidente produce una sugerencia; varias categorías o ninguna
producen abstención. Guarda los fragmentos literales y posiciones que coincidieron.

- Una coincidencia temática no afirma que ocurrió un brote ni evalúa peligrosidad.
- No inventa entidad, severidad, probabilidad ni confianza.
- No consulta URLs ni ejecuta instrucciones incluidas en titulares.
- Descarta campos humanos y supuestas aprobaciones aportadas por fuentes.
- El extractor basado en modelo local sigue pendiente; no hay Ollama instalado en
  el PATH comprobado durante esta tanda. No se instaló ni descargó un modelo.

## Evaluación honesta

`bio/evaluacion.py` compara IDs y SHA-256 de `(id, url, claim_literal)` exactos.
Una predicción de otra versión del titular no puede puntuar por compartir ID.
Duplicados de ID se rechazan en lugar de elegir la predicción favorable.

- `cobertura`: respuestas válidas sin abstención / total de referencia.
- `exactitud_global`: aciertos / total de referencia, incluyendo ausencias y
  abstenciones en el denominador.
- `exactitud_selectiva`: aciertos / respondidas; `null` cuando no respondió ninguna.
- `tasa_esquema_invalido`: errores de forma / predicciones recibidas. Se separa de
  `huellas_incompatibles` (predicciones de otro contenido), aunque ambas cuentan en
  `invalidas` y `tasa_predicciones_invalidas`.
- También reporta desconocidas, abstenciones, ausentes, matriz de confusión
  y precisión/recall por categoría. No se presenta precisión sin cobertura.

Sin dorado no hay métricas de calidad real. Las pruebas sintéticas comprueban fórmulas
e integridad, no calibración. No se ajustarán reglas mirando respuestas del dorado ni
se declarará mejora A/B hasta tener un conjunto humano previo e independiente.
El pipeline mide duración global de preparación; no estima costo ni latencia de un
modelo que no se ha ejecutado. Sus llamadas de red/modelo y gasto API son cero.

## Intervención humana

Revisa el CSV contra `muestra.jsonl` **antes de consultar las sugerencias automáticas**,
para evitar etiquetar mirando las respuestas. Campos nuevos compatibles con el bucle:
`categoria_humana`, `severidad_humana`, `origen_etiqueta`, `fecha_revision`, `revisor`.
Permanecen vacíos; también se conservan los campos de notas del radar.

El CSV no es un dorado aprobado ni se carga directamente como JSONL. Sigue el esquema
humano de `10-OPERACION-BUCLE.md`; los casos ambiguos requieren resolución humana o
exclusión explícita, nunca una aprobación inventada. No hay importación automática
que convierta estas sugerencias en etiquetas humanas.

## Pruebas

```bash
python3 -m unittest discover -s tests -v
```

Se usan fixtures temporales; no se modifica el conjunto dorado real ni se hace red.
