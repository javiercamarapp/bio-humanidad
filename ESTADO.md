# Estado verificable — entrega técnica en revisión, 2026-09-19

## Qué entrega el software

Radar de **metadatos públicos HN/Algolia**, una sola fuente: recolector, normalización,
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

## Verificación de punta a punta

```bash
python3 -m unittest discover -s tests -v
python3.12 -m unittest discover -s tests -v
python3 -m unittest discover -s tests -p test_flujo_completo.py -v
```

Última verificación local: **171 pruebas, OK en Python 3.9.6 y 3.12.14**. No se borró, debilitó ni
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

**Esta última corrección aún no tiene dictamen independiente favorable.** Se agotaron
las 2 revisiones previstas: no se interpreta el verde local como aprobación del revisor
ni se integra la PR por inferencia. Ambas revisiones usaron copias aisladas de fuentes
públicas con temporales escribibles; se cotejaron hashes, sin acceso a datos reales.
Evidencia local: `salidas/verificacion/cierre-20260919/`.

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
**164 pruebas OK en Python 3.9 y 3.12**. CI de las nuevas 171 pruebas: pendiente de push y
comprobación remota. El verde local no sustituye al CI. Tras integrar se exige también
el workflow de `main`; consultar [Actions](https://github.com/javiercamarapp/bio-humanidad/actions/workflows/tests.yml).

## Privacidad y presupuesto

Solo código, pruebas y documentación propia se versionan. `git ls-files datos salidas`
incluye únicamente `.gitkeep` y `datos/ESQUEMA.md`. Crudos, CSV humanos, logs, salidas,
revisiones y credenciales permanecen locales/ignorados. Gitleaks: **20 commits previos
sin hallazgos**; diff de los parches de cierre también sin hallazgos. Eso reduce riesgo,
no demuestra ausencia absoluta de secretos. La identidad Git existente no se cambió.

Presupuesto fijado en `PROGRAMA.md`: 40 minutos, hasta 3 correcciones, 2 revisiones
independientes de 5 minutos, USD 0 en APIs; sesión ChatGPT existente para revisión de
código. Ejecutadas **3/3 correcciones funcionales**, una prueba E2E nueva, **2/2 revisiones**,
1/1 corrida de red y 2/2 corridas operativas offline. Parada por agotamiento de ese
presupuesto, con la integración bloqueada por revisión final y los gates humanos aún
pendientes. No es un loop infinito ni investigación desatendida.

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
