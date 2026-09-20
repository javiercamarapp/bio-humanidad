# 16 — Pipeline local de metadatos, opt-in

## Contrato

`bio.pipeline_local` conecta señales ya recolectadas con tres roles locales:

1. **Extractor:** propone categoría o abstención y una cita literal del titular.
2. **Analista documental:** explica qué información falta o qué ambigüedad existe.
3. **Refutador documental:** cuestiona la categoría/interpretación con otra familia
   y otro digest. Una objeción, abstención o falta de objeción nunca aprueba ciencia.

Es un flujo técnico completo de **metadatos**, no el sistema científico hipotético de
los documentos históricos. No implementa análisis de anomalías por modelos frontera,
no consulta el contenido de los enlaces, no genera candidatos para `bio.bucle`,
no crea etiquetas humanas y siempre conserva `publicable:false`/`verificado:false`.
Las observaciones de los modelos son propuestas no verificadas y pueden estar equivocadas.

## Perfil operativo contrastado

En Apple M3/24 GiB se ensayó inicialmente Qwen3.6-27B: un registro completó los tres
roles, pero el analista del segundo agotó180s. El lote quedó ERROR, sin manifiesto final.
No se borró esa evidencia ni se incrementó el timeout para obtener un verde.

Se conservó ese modelo en disco para uso opcional y se probó un perfil menor:

| Rol | Modelo | Familia |
|---|---|---|
| Extractor | `gemma4:12b` | gemma4 |
| Analista | `qwen3.5:9b` | qwen35 |
| Refutador | `gemma4:12b` | gemma4 |

Dos titulares reales, fuera de los dos paquetes ciegos anteriores, completaron **6
solicitudes en92.85s**, con hashes íntegros y estado `PENDIENTE_DORADO`. Durante el
muestreo de `/api/ps`, como máximo un modelo cargado; tamaño máximo reportado7.83GB,
frente a17.94GB del ensayo anterior27B. Esto no mide calidad semántica ni garantiza
memoria/latencia iguales en todas las entradas; el tamaño reportado no es toda la RAM
del sistema. Los dos modelos nuevos ocupan aproximadamente14.2GB en disco según sus
fichas. No se presentan como los mejores modelos universales ni como modelos sin límites.

Fuentes: [Gemma4-12B](https://ollama.com/library/gemma4:12b),
[Qwen3.5-9B](https://ollama.com/library/qwen3.5:9b).

## Servidor y modelos: explícitos, no instalación automática

Ollama debe estar instalado y ambos modelos descargados de forma autorizada. El
cliente NO ejecuta `pull`, no instala servicios y no acepta modelos cloud. No se
habilitan proveedores pagados. Para preparar otra máquina, tras comprobar recursos:

```bash
# Terminal1: solo loopback, cloud deshabilitado y sin modelos simultáneos.
OLLAMA_HOST=127.0.0.1:11434 OLLAMA_NO_CLOUD=1 \
OLLAMA_CONTEXT_LENGTH=4096 OLLAMA_NUM_PARALLEL=1 OLLAMA_MAX_LOADED_MODELS=1 \
OLLAMA_FLASH_ATTENTION=1 OLLAMA_KV_CACHE_TYPE=q8_0 OLLAMA_KEEP_ALIVE=0 \
ollama serve

# Terminal2: descargas explícitas; aproximadamente14.2GB en total.
OLLAMA_HOST=127.0.0.1:11434 ollama pull gemma4:12b
OLLAMA_HOST=127.0.0.1:11434 ollama pull qwen3.5:9b
```

No reutilizar un puerto ocupado por un servidor desconocido. La CLI instalada en el
Mac no equivale a servicio permanente: los servidores de prueba fueron temporales.
Las variables anteriores solo configuran ese proceso. Detenerlo con Ctrl+C al terminar.

## Ejecutar

El recolector y la preparación offline siguen siendo los existentes. El flujo local
consume un JSONL de señales; no se activa implícitamente en `bio.vigilar` ni `bio.bucle`.

```bash
python3 -m bio.pipeline_local \
  --entrada salidas/historial/acumulado-001/senales.jsonl \
  --salida salidas/modelos/lote-001 \
  --extractor gemma4:12b --analista qwen3.5:9b --refutador gemma4:12b \
  --cantidad 3 --max-segundos 600
```

Sustituir la entrada por una existente. Dentro del repositorio, la salida debe ser
`salidas/modelos/NOMBRE`, siempre nueva y sin enlaces simbólicos. Selección determinista
por ID: `--cantidad` indica cuántas señales se procesan, NO el tamaño total del corpus.
Admite1–50 señales por lote,1–3600s de presupuesto global y180s por inferencia como
máximo, incluidas comprobaciones de identidad. No hay reintentos ni reanudación.

Para detener una corrida propia, crear `STOP` dentro de su carpeta. SIGTERM/Ctrl+C
interrumpen la CLI. Se termina/recoge el hijo HTTP propio; su watchdog también sale
al perder al padre. Cerrar la conexión solicita cancelación al servidor; la cancelación
real del trabajo del modelo depende del servidor local, no permite matar procesos ajenos.

## Artefactos y estados

- `entrada.jsonl`, `seleccion.jsonl`, `config.json`: procedencia, límites y modelos.
- `NNN-extractor.json`, `NNN-analista.json`, `NNN-refutador.json`: resultado, cita,
  identidad, hash de prompt, hash de señal y duración de cada paso.
- `predicciones.jsonl`: formato compatible con evaluación, origen `ollama_v1`.
- `revision-documental.jsonl`: interpretaciones automáticas `PENDIENTE_HUMANO`.
- `revision/`: muestra ciega NUEVA, sin copiar predicciones; no sustituye las revisiones
  anteriores. Con menos de50 señales no puede cumplir por sí sola el mínimo del dorado.
- `metricas.json`, `deteccion.json`, `informe.md`: evaluación y límites explícitos.
- `manifest.json`: cierre técnico `PIPELINE_LOCAL_COMPLETO`, hashes y solicitudes.
  Exit0 certifica ese cierre, no ciencia. `estado.json` es diagnóstico de la invocación.

Timeout, STOP, esquema/cita inválidos o cambio de identidad/código detienen el lote.
Exit2, `estado.json` ERROR si pudo escribirse y **sin manifiesto final**. Un manifiesto
retirado queda como `manifest-no-finalizado.json`. No consumir archivos mientras corre
ni ignorar el exit code. SIGKILL/corte de energía pueden dejar parciales; un fallo de
disco permanente puede impedir registrar el error o retirar un archivo. No se promete
persistencia perfecta ni seguridad frente al propietario local que modifica código/disco.

## Evaluación sin fabricar humanos

Después de revisión/importación real, añadir `--dorado datos/dorado/senales.jsonl`.
El dorado debe cumplir el contrato existente de50 IDs revisados; se conserva snapshot
y hash. Las referencias no procesadas cuentan como ausencias: no se infla cobertura
por evaluar solo las respuestas convenientes. Sin `--dorado`: `PENDIENTE_DORADO`,
exactitud desconocida, nunca etiquetas inventadas.

La API `bio.evaluacion.evaluar(..., origen_esperado='ollama_v1')` habilita ese origen
explícitamente. El valor por defecto permanece `reglas_v1`; no se modifica el flujo
offline ni las guardias humanas anteriores. Los dictámenes documentales no se puntúan
como verdad científica. Modelos de distintas familias pueden compartir sesgos.

## Límites de transporte y esquema

Solo HTTP a `127.0.0.1` (puerto11434 por defecto, configurable). Sin proxies, DNS de
un host remoto, redirecciones ni herramientas. Respuestas≤256KiB, petición≤32KiB,
mensajes≤3000bytes UTF8 como margen conservador para contexto4096. Entrada excesiva
se rechaza, no se trunca para producir una respuesta. Salida≤256tokens; truncada falla.

Se comprueba tag explícito, digest, familia y ausencia de propiedades cloud antes y
después de cada generación. Un alias no simula independencia. Esquemas cerrados,
citas exactas contra el titular y observaciones≤400 caracteres sin URLs añadidas.
Estos controles NO prueban que la interpretación sea correcta ni autentican un servidor
local malicioso. Los campos de aprobación no se toman del modelo.

## Evidencia

Pruebas nuevas con HTTP local sintético, CLI/subprocesos reales, timeout, pérdida del
padre, STOP, redirecciones, tamaño, JSON ambiguo, cambios de identidad, aliases,
fallo de cierre temporal, evaluación con fixtures y ausencia de contaminación humana.
La suite antigua no se modifica. La demo offline sigue sin requerir Ollama.

Evidencia de operación real y lote fallido conservada localmente en
`salidas/verificacion/pipeline-local-20260920/` y `salidas/modelos/`. No se suben datos,
logs, pesos ni nombres de revisores a Git. Continúan pendientes las50 revisiones reales,
la calibración de cobertura/historia y cualquier autorización de publicación.
