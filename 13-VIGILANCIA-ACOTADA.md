# 13 — Vigilancia pública acotada

`bio.vigilar` coordina el recolector HN/Algolia y la preparación offline. No es
investigación científica autónoma: no genera hipótesis, etiquetas humanas ni alertas,
no llama modelos, no publica y no desbloquea `bio.bucle`.

## Una vuelta real

Desde la raíz del repositorio, con Python 3.9+ en macOS/Linux:

```bash
python3 -m bio.vigilar \
  --salida salidas/vigilancia/mi-primera-corrida \
  --max-vueltas 1 --max-segundos 90
```

Esto hace consultas de titulares a HN/Algolia (una sola fuente sesgada). No descarga
el contenido de los enlaces publicados. La salida debe ser nueva. Dentro del
repositorio solo se permite `salidas/vigilancia/NOMBRE`; se rechazan enlaces simbólicos
observados y componentes `..`. No es un sandbox contra otro usuario con escritura local.

Para una observación horaria finita, elige otra carpeta:

```bash
python3 -m bio.vigilar \
  --salida salidas/vigilancia/mi-jornada \
  --max-vueltas 8 --intervalo-segundos 3600 --max-segundos 28800
```

Corre en primer plano. No instala un servicio ni se relanza solo. No ejecutes
construcción o cambios de código mientras está activo.

## Presupuesto y paradas

- Entre 1 y 24 vueltas; entre 1 y 86400 segundos de presupuesto global.
- Intervalo de 1 a 86400 segundos; la CLI con red exige al menos 60 segundos.
  El intervalo comienza al terminar la vuelta, no al iniciarla.
- Cada hijo dispone de hasta 300 segundos, nunca más que el presupuesto restante.
- El mayor tiempo transcurrido de reloj monotónico/civil cuenta hacia el presupuesto:
  la suspensión simulada del equipo no lo reinicia. Un avance civil puede agotar el
  presupuesto conservadoramente; un retroceso observado causa `RELOJ_RETROCEDIO`.
- Los resultados de hijos terminados fuera de presupuesto no se incorporan a
  `informes`. Pueden quedar archivos parciales: no borrarlos ni confundirlos con una
  entrega aceptada por el vigilante.
- Tres errores consecutivos detienen la corrida. Una recolección parcial no pasa
  silenciosamente a preparación, aunque el recolector haya guardado algunos titulares.
- `MAX_VUELTAS`, `PRESUPUESTO`, STOP o señal terminan la ejecución. Un timeout de hijo
  se registra como error; agotar tiempo durante la espera es una parada normal.
- `codigo_salida` es 2 si hubo errores, 0 si no. **Exit 0 no significa calidad
  científica, muestra suficiente ni aprobación humana.** Mira también cada registro.

Parada desde otra terminal, una vez creada la carpeta:

```bash
touch salidas/vigilancia/mi-jornada/STOP
```

También puedes usar Ctrl+C o SIGTERM dirigido al proceso que tú lanzaste. STOP y las
señales se comprueban durante la espera de hijos en intervalos de hasta 1 segundo
mientras el sistema está ejecutando. Se termina y recoge únicamente el hijo creado
por el vigilante; no se buscan procesos por nombre ni se mata un PID leído del disco.
Las operaciones locales de archivo no son interrumpidas por ese sondeo.

## Offline y deduplicación

```bash
python3 -m bio.vigilar \
  --salida salidas/vigilancia/mi-prueba-offline \
  --sin-red --entrada datos/senales/senales.jsonl \
  --max-vueltas 2 --intervalo-segundos 1 --max-segundos 10
```

`--entrada` solo se admite con `--sin-red`. Se copia una vez; el original no se modifica.
El recolector conserva URLs únicas **dentro de cada corrida**, sin fabricar observaciones
históricas al consultar otra vez. Con los mismos bytes y corte UTC, el siguiente ciclo
queda en `SIN_CAMBIOS`, sin otra muestra de revisión. Un cambio de día recalcula la ventana.
El corte es el día UTC siguiente (exclusivo): el día actual aún está incompleto.

Si hay menos de 50 señales únicas se registra `MUESTRA_INSUFICIENTE`. No se reduce
el mínimo humano ni se rellena con duplicados. El vigilante prepara siempre contra
un dorado deliberadamente ausente; para evaluar un dorado humano real usa
`bio.preparacion` explícitamente, siguiendo los documentos 11 y 12.

## Artefactos y recuperación

Cada corrida guarda `titulares.jsonl`, `estado.json` y `ciclo-NNN/registro.json`.
Los ciclos preparados incluyen snapshot e informe con manifiesto, huellas y muestra
ciega. Los registros guardan salidas/códigos de cada hijo; todo queda ignorado por Git.
`publicable` siempre es `false` y `gasto_api_usd` es 0.

`estado.json` es un checkpoint, **no una prueba de vida**. Tras SIGKILL, crash del
intérprete o apagado puede seguir diciendo `EN_CURSO`/`ESPERANDO` y `proceso_activo:true`.
El PID puede haberse reutilizado: no lo uses para matar procesos. Revisa el proceso
que lanzaste y conserva los archivos para diagnóstico.

**No hay `--reanudar` en el vigilante.** Una carpeta existente nunca se reutiliza,
aunque la ejecución muriera. Para continuar offline, inicia una carpeta nueva con
`--entrada CORRIDA_ANTERIOR/titulares.jsonl`; se abre un presupuesto nuevo explícito,
no se heredan automáticamente vueltas, muestras ni deduplicación de otra corrida.
No se promete historia acumulada entre corridas. `bio.bucle --reanudar` es un contrato
distinto: conserva sus límites y revisiones, no sirve para reanudar el vigilante.

## Verificar

```bash
python3 -m unittest discover -s tests -p test_vigilar.py -v
python3 -m unittest discover -s tests -v
```

Fixtures offline prueban suspensión/retroceso simulados, timeout, STOP, SIGTERM,
SIGKILL, código cambiado, parciales, deduplicación, entradas y límites. No se suspendió
físicamente el Mac para estas pruebas. La suite completa comprueba también el contrato
de reanudación separado de `bio.bucle`. Ni los tests ni la ingesta miden precisión
científica: siguen pendientes las 50 etiquetas humanas reales.
