# 10 — Operación del bucle construido

## 1. Pruebas sin datos reales ni red

```bash
cd ~/Desktop/"bio humanidad"
python3 -m unittest discover -s tests -v
```

Las etiquetas y aprobaciones usadas en pruebas son fixtures sintéticos en directorios
temporales. No se escriben en `datos/dorado/` ni prueban calidad científica.

## 2. Entrada humana: conjunto dorado

Existe una muestra pendiente en `salidas/preparacion/`; la preparación inicial produjo
50 señales de las 129 de HN. No es una muestra representativa de cinco fuentes ni está
etiquetada. El CSV es material de revisión, **no se carga directamente como JSONL**.

Una persona debe leer las señales, acordar los criterios de categoría y severidad,
completar la revisión y registrar al menos 50 IDs diferentes en
`datos/dorado/senales.jsonl`. Cada línea debe contener estos campos:

| Campo | Requisito |
|---|---|
| `id`, `claim_literal`, `url` | Valores de la señal original, no inventados |
| `categoria_humana` | `brote`, `vigilancia`, `sintesis`, `dual-use`, `politica`, `capacidad`, `otro` |
| `severidad_humana` | `baja`, `media`, `alta`, `no_aplica` |
| `revisor` | Identidad de quien realizó la revisión |
| `fecha_revision` | Fecha ISO `YYYY-MM-DD` |
| `origen_etiqueta` | `humano`, solo si realmente lo fue |

El código comprueba completitud e integridad, no autentica a una persona. Los nombres
no son firmas. No se puede convertir una etiqueta generada por IA en humana cambiando
un campo. Medir precisión del futuro extractor será un trabajo adicional.

## 3. Entrada humana: revisión de cada candidato

Candidato Markdown con frontmatter de una línea por valor, sin claves duplicadas:
`id`, `falsable`, `prueba`, `costo`, `alcance`, `fuentes`, `estado`.
`fuentes` debe ser una lista JSON de 1–10 URLs únicas. `estado`: `propuesta`.
Alcances declarados admitidos: `defensa`, `preparacion`, `vigilancia`, `evals`.
Ese texto no sustituye al juicio humano sobre seguridad.

Obtén el hash del contenido exacto con:

```bash
shasum -a 256 salidas/hipotesis/ARCHIVO.md
```

La revisión humana se guarda aparte en `datos/revisiones/<sha256>.json`. Es un registro
local de decisiones, **no autenticación criptográfica ni resultado automático**.
Campos requeridos para aceptar:

- `sha256`: hash exacto del candidato.
- `origen`: `humano`.
- `revisor`: identidad real de quien revisó.
- `fecha_revision`: fecha ISO.
- `decision`: `aprobar` o `rechazar`.
- Booleanos `alcance_seguro`, `falsable`, `prueba_viable`, `novedad_revisada`,
  `fuentes_respaldan`: todos `true` solo tras evaluación humana favorable.
- `citas`: una entrada por cada URL del candidato, con `url` y `texto` (al menos
  20 caracteres de cita textual). La persona verifica que respaldan las afirmaciones.

El agente y el bucle no crean estas aprobaciones. Una modificación del candidato
invalida la revisión previa porque cambia su hash. Un rechazo humano queda registrado
sin intentar consultar fuentes para rehabilitarlo.

## 4. Ejecutar y reanudar

```bash
python3 -m bio.bucle --max-vueltas 200 --max-segundos 900
```

La salida JSON incluye `corrida`, `vueltas`, `aceptadas`, `no_aceptadas`, los estados,
el gasto de API (0) y `motivo_parada`. Si falta el dorado, esto **se detiene con código
2 y cero vueltas**. No queda una ejecución desatendida viva.

```bash
python3 -m bio.bucle --reanudar salidas/bucle/ID_DE_CORRIDA
```

Se utiliza la configuración original. Las opciones de presupuesto/red nuevas no
alteran una reanudación. Se conserva el origen monotónico de la corrida, no solo el
último checkpoint: un fallo de escritura no devuelve tiempo al reanudar. Se verifica
el identificador de arranque (Linux `/proc/sys/kernel/random/boot_id`; macOS
`kern.bootsessionuuid`). Otro arranque, un origen inválido o una corrida antigua sin
esa información bloquean reanudación y requieren inspección, sin reiniciar el presupuesto.
Se conserva además la última observación durable del reloj civil. Si este retrocede respecto al último checkpoint, se detiene con
`RELOJ_RETROCEDIO` sin aceptar el intento pendiente. Si cambias código, etiquetas o revisiones, comienza una
corrida nueva, sin `--reanudar`. No edites `config.json` para eludir las guardias.

**Guardia conservadora adicional:** si el último registro del historial es `ACEPTADA`,
la reanudación se bloquea para inspección, incluso cuando el marcador ya no existe.
Ausencia de marcador no acredita que terminó la confirmación bajo fallos combinados.
No se borran ni degradan los registros previos: una ejecución finalizada conserva su
informe, pero no se reconstruye automáticamente una aceptación final al recuperar.
Para continuar tras inspección, iniciar explícitamente otra corrida; no quitar esta
guardia ni editar el estado para forzar recuperación. Historiales cuyo último intento
no está aceptado siguen sujetos al resto de controles y al presupuesto original.

Modo sin consultas HTTP:

```bash
python3 -m bio.bucle --sin-red --max-vueltas 10 --max-segundos 120
```

No acepta fuentes como revalidadas. Si los otros controles pasan, se detiene con
`PENDIENTE_RED`. No es un atajo para saltarse verificación.

Validación de un archivo o carpeta, fuera del ejecutor:

```bash
python3 -m bio.validador.validar salidas/hipotesis/ --rubrica --sin-red
python3 -m bio.validador.validar salidas/hipotesis/ --rubrica --json
```

La validación aislada no ejecuta la guardia del conjunto dorado, el cerrojo ni el
presupuesto global: para una corrida operativa usa siempre `bio.bucle`.

## 5. Qué guarda

`salidas/bucle/<id>/` contiene:

- `config.json`: inicio, límites y hashes de protegidos.
- `intentos/000001-<hash>/candidato.md` y `registro.json`: intento comprometido.
- `intentos/.incompleto-*`: trabajo interrumpido; no cuenta como aceptado.
- `estado.json`: último checkpoint o motivo final de parada.
- `.lock`: cerrojo del sistema operativo. La existencia del archivo no prueba que
  haya un proceso activo. `proceso_activo: null` indica un checkpoint, no una prueba
  de vida; consulta el proceso para conocer su estado durante una ejecución.

Los intentos no se borran. Un historial inconsistente se detiene para revisión manual.
Las escrituras de registros y checkpoints (incluido el final) también consumen el
presupuesto. Si el último intento excede el tiempo o se observa retroceso del reloj
mientras se persiste, se conserva como `ERROR`, con `estado_previo` y el motivo;
no cuenta como aceptado ni al reanudar. Las vueltas cerradas previamente se conservan.
Los checkpoints son provisionales mientras la invocación sigue ejecutándose. Cada
intento nuevo lleva `.confirmacion-pendiente` hasta completar sus guardias y escrituras.
Si una escritura falla o el proceso muere antes de confirmar, la reanudación devuelve
`ERROR_ESTADO` por confirmación pendiente, en lugar de recuperar una aceptación dudosa.
El marcador no se elimina automáticamente al reanudar: conservar toda la evidencia,
inspeccionar y comenzar otra corrida tras la revisión pertinente. **No borrar el
marcador para forzar una aceptación.** Un SIGKILL/apagado o disco averiado todavía puede
impedir persistir el estado final: no interpretar el JSON de un intento aislado como
una entrega confirmada.
La eliminación del marcador también se comprueba contra el presupuesto y el reloj.
Si termina tarde, se restaura el bloqueo antes de invalidar el intento; si la
invalidación falla, no se permite recuperarlo como aceptado. Solo se limpia nuevamente
tras persistir un veredicto no aceptado. Un error de eliminación, incluso posterior a
eliminar físicamente el archivo, restaura el bloqueo o intenta dejar `ERROR` durable.
Fallos permanentes del disco pueden impedir ambas escrituras: en ese caso no hay
certificación de recuperación y se requiere inspección, no reanudación automática.
Los límites son cooperativos en los puntos de control: no prometen tiempo real duro
ni interrumpir una operación del filesystem mientras el sistema está suspendido.
Si terminó la cola pero hubo errores de ejecución, el estado es
`COLA_AGOTADA_CON_ERRORES` y el código de salida es 2, no éxito silencioso.
El dorado, revisiones y estado rechazan claves JSON repetidas y números no finitos:
una segunda clave `decision` no puede sobrescribir una decisión anterior.
Los directorios generados siguen ignorados por Git; no se publican datos ni revisiones
al hacer commit de código. No ejecutar simultáneamente construcción y bucle operativo:
los cambios de código son, deliberadamente, una causa de parada.

## Límites de red y seguridad

El validador solo consulta los hosts enumerados en `HOSTS_FUENTES` en
`bio/validador/validar.py`. Usa HTTPS, rechaza credenciales y puertos alternativos,
comprueba también redirecciones, limita cada respuesta a 1 MB y usa timeout de 5 s
por operación de red. El subproceso del bucle impone además el límite de tiempo total
por intento. HTML y texto plano únicamente; PDF requiere otro flujo de revisión.

Estos controles no son un sandbox del sistema operativo. Un usuario con acceso de
escritura al mismo proyecto puede alterar código y registros. Tampoco sustituyen a
un revisor humano competente ni permiten experimentos para optimizar evasión de
cribado o peligrosidad biológica.

## Componentes aún pendientes

Generación de candidatos desde anomalías, extractor con modelo local, evaluación real
del extractor contra dorado, refutador independiente, integración de modelos de pago
y validación científica. Este ejecutor no finge que existan.
