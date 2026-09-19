# Estado verificable — entrega técnica, 2026-09-19

## Qué entrega el software

Radar de **metadatos públicos HN/Algolia y feeds CDC/ECDC/OMS**: recolectores, normalización,
procedencia, deduplicación, extractor por reglas con abstención, preparación offline,
revisión/importación humana, evaluación por hashes y ejecución acotada.

- `bio.vigilar` coordina ingesta/preparación con límites y STOP. No es un daemon ni
  soporta reanudación; conserva corridas y requiere una carpeta nueva.
- `bio.bucle` consume candidatos existentes, no los genera. Sus guardias humanas,
  presupuestos, historial y reanudación son independientes del vigilante.
- Demo y pruebas funcionan con biblioteca estándar, Python 3.9+/macOS/Linux o WSL.
- No usa modelos, no valida ciencia ni publica alertas. Código/documentación propia MIT;
  los contenidos de terceros conservan sus derechos.

Guías: [README](README.md), [bucle](10-OPERACION-BUCLE.md),
[preparación](11-PREPARACION-OFFLINE.md), [revisión](12-REVISION-HUMANA.md),
[vigilancia](13-VIGILANCIA-ACOTADA.md).

## Ampliación multifuente

`bio.recolector.multifuente` y `bio.historial` añaden snapshots RSS/Atom y unión offline
con procedencia; `bio.vigilar --fuentes` los coordina sin reemplazar el modo HN. Guía:
[14-OPERACION-MULTIFUENTE.md](14-OPERACION-MULTIFUENTE.md). El preflight real descartó
endpoints antiguos; el feed OMS retenido expone su antigüedad, no oculta206 días sin
publicación reciente. Descargas limitadas y sin hijos indefinidos tras morir el padre.

Operación real:535 URLs RSS,0 errores. Con129 HN:664 URLs/4 fuentes/1 día observado;
preparación no publicable,50 casos ciegos pendientes. Hashes comprobados y fuentes
originales intactas. El vigilante real se detuvo en MAX_VUELTAS; esta corrida precedió
al chequeo adicional de hash del snapshot, probado después con fixtures y hashes reales.

Se añadieron22 pruebas sin alterar las183 anteriores. No existe todavía integración
real con Ollama (no instalado/no disponible), ni clientes de analista/refutador. Esos
componentes requieren definir/autorizarlos; tener prompts históricos no los completa.
El detector actual no satisface automáticamente feeds semanales tras esperar90 días:
hay una decisión de cobertura/calibración de dominio pendiente, no solo tiempo faltante.

## Verificación de punta a punta

```bash
python3 -m unittest discover -s tests -v
python3.12 -m unittest discover -s tests -v
python3 -m unittest discover -s tests -p test_flujo_completo.py -v
```

Última verificación local: **205 pruebas, OK en Python 3.9.6 y 3.12.14**. No se borró, debilitó ni
saltó ninguna prueba anterior. El E2E usa comandos CLI reales en un temporal:

1. Demo sintética sin red → preparación y hashes íntegros.
2. Revisión pendiente → importación denegada incluso con confirmación.
3. Revisión **simulada y rotulada como fixture**, solo en el temporal → importación
   explícita; una segunda importación no sobrescribe el dorado.
4. Evaluación contra ese fixture → métricas técnicas y `publicable:false`.
5. Cambiar el dorado impide reanudar una configuración anterior; importar etiquetas
   no aprueba el candidato, que sigue en `PENDIENTE_HUMANO`.

Los fixtures NO completan el dorado real ni miden precisión científica.

### Revisión independiente

La primera revisión del cierre ejecutó las 165 pruebas de entonces en ambos Python
y detectó dos huecos adicionales: checkpoint final del vigilante y persistencia tardía
de aceptación en `bio.bucle`, incluida reanudación. Se reprodujeron **8 fallos** con
regresiones nuevas antes de corregirlos. Ambos arreglos mantienen las vueltas previas
válidas e invalidan solo la entrega tardía del intento en cierre.

La suite de 169 añade esas regresiones y la conservación de intentos previos. También
se reejecutaron los scripts independientes: registros/checkpoints tardíos quedan sin
informes o como `ERROR`, **0 aceptadas al reanudar**; retroceso civil y excepción del
padre quedan con causa explícita. La fuente sintética permanece intacta.

La segunda revisión ejecutó 169 pruebas OK por versión, pero emitió **NO INTEGRAR**:
un error recuperable de escritura podía saltarse el control temporal y conservar una
aceptación/informe provisional. Se reprodujeron sus casos y se aplicó la tercera
corrección: el vigilante retira la entrega afectada; el bucle crea un marcador durable
antes de comprometer el registro y bloquea reanudación si la confirmación no terminó.
La evidencia no se borra. Dos regresiones nuevas cubren checkpoint intermedio/final,
salto civil hacia adelante/atrás y fallo sin salto: la suite final da **171 OK** por versión.

La tanda de correcciones terminó sin dictamen favorable, al agotar sus 2 revisiones.
Evidencia local: `salidas/verificacion/cierre-20260919/`.

### Confirmación posterior del diseño congelado

Ante una nueva solicitud de continuación se verificó `ccc9db0`, sin permitir más
parches ni repetir revisores hasta obtener aprobación. **Dictamen: NO INTEGRAR**.
Se reprodujo un bloqueante adicional: eliminar `.confirmacion-pendiente` consume tiempo
después de la última guardia. Con presupuesto de 2 s y avance civil simulado de 60 s
antes de `unlink`, devuelve `COLA_AGOTADA`, 1 aceptación sintética y cero marcadores;
al reanudar mantiene esa aceptación. No hubo red ni revisión humana real en la prueba.

[Issue #2: confirmación fuera de presupuesto](https://github.com/javiercamarapp/bio-humanidad/issues/2)
contiene reproducción mínima y comportamiento esperado. Las 171 pruebas existentes
pasan en ambos Python, pero **no cubren ese intercalado**. Es un fallo abierto, no solo
una revisión pendiente. Se detuvo para revisar el protocolo de confirmación completo.

Se verificó por SHA-256 que los 54 archivos de la copia del revisor coincidían con el
árbol original congelado; no hubo mutaciones de código/tests. Evidencia local:
`salidas/verificacion/confirmacion-final-20260919-2039/`.

### Corrección del protocolo y recuperación conservadora

La continuación posterior añadió 9 pruebas nuevas sin tocar las 171 anteriores.
La eliminación tardía del marcador devuelve ahora `PRESUPUESTO`, **0 aceptadas y
0 al reanudar**; también se cubren retroceso, error antes/después de eliminar,
invalidación fallida y cancelación. Primero se observaron las regresiones en rojo.

La primera revisión del parche detectó fallos transitorios combinados y devolución de
presupuesto monotónico tras un checkpoint fallido. Se reprodujeron antes de ampliar el
diseño: una cola `ACEPTADA` requiere inspección al recuperar, aun sin marcador; se
conservan los registros, no se infiere aprobación. El origen monotónico persiste junto
al identificador de arranque: un reinicio del equipo o un origen no verificable bloquea
reanudación. Estas restricciones, incluida su incidencia en cierres aparentemente limpios,
están documentadas en la guía 10.

La segunda revisión no reprodujo aceptación indebida y verificó la lógica con un
arranque simulado (40 pruebas), además del presupuesto entre procesos. Su dictamen es
**NO INTEGRAR por verificación incompleta**: el sandbox denegó
`sysctl kern.bootsessionuuid`; las dos suites allí terminaron con 1 fallo y 48 errores.
No se rebajan permisos para obtener verde ni se presenta esa simulación como E2E real.
En el entorno local soportado, sin simular la consulta de arranque, las **180 pruebas
pasaron en esas corridas de ambos Python**. La continuación siguiente detectó una
intermitencia entre procesos que esas corridas verdes no habían descartado.

Se cotejaron los 55 archivos de ambas copias aisladas: sin modificaciones del revisor;
la segunda coincidía con el árbol antes de esta actualización documental. Evidencia:
`salidas/verificacion/correccion-confirmacion-20260919-2053/`. No se solicita una tercera
revisión dentro de esta tanda ni se transforma el dictamen en aprobación propia.

### Portabilidad del reloj y cierre de trazabilidad

Una nueva suite real falló en el E2E de Python3.9/macOS: `time.monotonic()` tenía
referencia por proceso. Se reprodujo el error con dos procesos de distinta edad antes
de corregirlo. `bio.reloj` usa ahora `clock_gettime(CLOCK_MONOTONIC)` con origen común;
la configuración identifica ese formato y rechaza corridas antiguas sin reinterpretarlas.
Se añadieron tres regresiones, sin cambiar métodos de prueba anteriores: **183 OK** en
3.9.6 y3.12.14. La CLI real se inició con3.9 y reanudó con3.12 conservando tiempo y
`DORADO_PENDIENTE`, cero vueltas/aceptaciones; no se simularon datos humanos.

Código revisado: `e00f0e76676b6a0d9f167938992d5b35e22d4a5f`. CI real:
[35471805979](https://github.com/javiercamarapp/bio-humanidad/actions/runs/35471805979),
**183 OK en ambos jobs**, incluidos E2E y procesos reales. El revisor contrastó esos
logs sin exigir permisos adicionales a su sandbox. No encontró otro bloqueo de código;
su único pendiente fue demostrar identidad entre el merge probado por CI y el head.

Se descargó el commit CI `ffbe720375a8d27df807bb7550e326e3753d5ba5` y se comprobó con
`git rev-parse SHA^{tree}` que ambos árboles son exactamente
`38aced91ce1bf514ec06fd8d57bd3b8a8fbf6b58`. También se cotejaron los56 archivos de la
copia revisada, sin mutaciones. Queda satisfecha la condición concreta del dictamen;
el revisor indicó que no hacía falta repetir pruebas al acreditar esa igualdad.
No es una aprobación científica ni un permiso derivado solo de CI verde.

Evidencia local: `salidas/verificacion/cierre-ci-20260919-2149/`, incluidos dictamen,
regresiones rojas, logs reales, manifiesto y `trazabilidad-ci.json`.

## Operación real y entrega humana

```bash
python3 -m bio.vigilar --salida salidas/vigilancia/cierre-red-20260919 \
  --max-vueltas 1 --max-segundos 90
```

Resultado real: **129 señales únicas, 0 errores, 0 consultas fallidas**, una vuelta,
`PREPARACION_COMPLETA`, `PENDIENTE_DORADO`, detector `DATOS_INSUFICIENTES`,
`MAX_VUELTAS`, `publicable:false` y proceso detenido. Esta ingesta precedió a los
parches de persistencia; sobre sus mismos datos se verificaron los controles temporales
intermedios/finales mediante esta corrida offline (anterior al último parche de error de escritura):

```bash
python3 -m bio.vigilar --sin-red \
  --entrada salidas/vigilancia/cierre-red-20260919/titulares.jsonl \
  --salida salidas/vigilancia/cierre-offline-final-20260919 \
  --max-vueltas 2 --intervalo-segundos 1 --max-segundos 10
```

Resultado: **2 vueltas, 0 errores, un informe**, `PREPARACION_COMPLETA → SIN_CAMBIOS`;
entrada intacta y todos los hashes del manifiesto comprobados. No se reescribieron
corridas previas ni se dejó un vigilante en segundo plano.

Paquete **local y ciego**, sin predicciones, listo para una persona:
`salidas/entrega-humana/cierre-20260919/LEEME.md`. Incluye CSV, snapshot, manifiesto y
procedencia; las copias se cotejaron por bytes y hashes. Los cinco campos humanos de
los **50 casos permanecen vacíos**. No se sube ese paquete al repositorio público.

```bash
python3 -m bio.dorado comprobar salidas/entrega-humana/cierre-20260919
```

Resultado observado: exit **2**, `PENDIENTE_REVISION_HUMANA`, **50 pendientes, 0 válidas**.
La guardia del dorado real sigue informando que faltan al menos 50 etiquetas humanas.
Las instrucciones locales dejan preparados los comandos de importación y evaluación
para ejecutarlos únicamente después de una revisión humana realmente completada.

## Integración y CI remoto

Entrega mediante [PR #1 hacia main](https://github.com/javiercamarapp/bio-humanidad/pull/1).
Su estado y checks son la referencia de integración; no se eluden protecciones ni
se modifica facturación, visibilidad, permisos o identidad. La rama remota se comprueba
antes del push no forzado y se valida el SHA exacto antes de integrar.

CI histórico de `5b67f62`: [35464112714](https://github.com/javiercamarapp/bio-humanidad/actions/runs/35464112714),
**164 pruebas OK en Python 3.9 y 3.12**. CI histórico del código `2145079`:
[35466883303](https://github.com/javiercamarapp/bio-humanidad/actions/runs/35466883303),
**success**. `gh run view 35466883303 --log` muestra `Ran 171 tests` / `OK` en ambos jobs
(3.9: 11.977 s; 3.12: 12.129 s). No es una inferencia del verde local.

La condición pendiente del contraste independiente quedó resuelta por igualdad exacta
de árboles, como se detalla arriba. La PR y sus comentarios registran la integración y
el SHA final; sus checks y el workflow de `main` son la referencia vigente, no los
verdes históricos. No se eliminan ramas ni se eluden protecciones. Consultar
[Actions](https://github.com/javiercamarapp/bio-humanidad/actions/workflows/tests.yml).

## Privacidad y presupuesto

Solo código, pruebas y documentación propia se versionan. `git ls-files datos salidas`
incluye únicamente `.gitkeep` y `datos/ESQUEMA.md`. Crudos, CSV humanos, logs, salidas,
revisiones y credenciales permanecen locales/ignorados. Gitleaks: **22 commits previos
sin hallazgos**; diff de los parches de cierre también sin hallazgos. Eso reduce riesgo,
no demuestra ausencia absoluta de secretos. La identidad Git existente no se cambió.

Presupuesto fijado en `PROGRAMA.md`: 40 minutos, hasta 3 correcciones, 2 revisiones
independientes de 5 minutos, USD 0 en APIs; sesión ChatGPT existente para revisión de
código. Ejecutadas **3/3 correcciones funcionales**, una prueba E2E nueva, **2/2 revisiones**,
1/1 corrida de red y 2/2 corridas operativas offline. Parada por agotamiento de ese
presupuesto, con la integración bloqueada por revisión final y los gates humanos aún
pendientes. No es un loop infinito ni investigación desatendida.

Tanda adicional autorizada: 30 minutos, dos revisiones como máximo (la segunda se
declaró antes de ejecutarla tras ampliar el diseño por evidencia). Sin red de ingesta,
APIs de pago ni modificaciones a etiquetas. Terminó con 180 pruebas locales OK y
revisión final limitada por el entorno; no se integró. El presupuesto y la enmienda
se conservaron en el directorio local de evidencia indicado arriba.

## Qué NO está demostrado ni se puede completar automáticamente

- **50 etiquetas humanas reales**: el paquete está preparado, la revisión no realizada.
- Verdad científica, descubrimientos, curas, amenazas o alertas sanitarias.
- Historia multifuente suficiente, calibración retrospectiva o calidad del extractor.
- Extractor por modelo, analista y refutador: no forman parte de esta entrega construida.
- Suspensión física del Mac: los saltos de reloj se simulan; STOP, SIGTERM, SIGKILL y
  timeout sí tienen pruebas con procesos reales.
- Persistencia perfecta ante apagado/disco averiado: un checkpoint puede quedar
  incompleto; no es prueba de vida ni aprobación. Inspeccionar antes de recuperar.

Las decisiones científicas y revisiones humanas no se sustituyen por un test verde.
No se desarrollan variantes biológicas ni evasión de cribados.
