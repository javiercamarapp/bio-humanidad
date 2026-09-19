# 02 — Programa del bucle

Aplica `bucle-trinquete`. Un bucle sin métrica, reversión barata y techo no itera:
deambula.

---

## Las cuatro condiciones — verificación previa

| Condición | ¿Se cumple? | Cómo |
|---|---|---|
| Salida verificable | **Parcial** | La métrica es un puntaje de rúbrica, no un pass/fail natural. Requiere un script validador. Ver abajo. |
| Acción reversible | **Sí** | Cada vuelta es un commit; `git revert` devuelve el estado. Repo y worktree. |
| Horizonte corto | **Sí** | Cada vuelta cierra en minutos: una hipótesis, un archivo, una validación. |
| Entorno acotado | **Sí** | El bucle solo escribe en `salidas/hipotesis/`. Nada más. |

**Advertencia honesta:** la primera condición no se cumple de forma natural. La
"calidad de una hipótesis científica" no la lee un comando. Por eso el bucle mide un
**proxy**: cuántas hipótesis pasan una rúbrica automatizable. Un proxy se puede
optimizar en falso — el bucle aprenderá a escribir hipótesis que pasan la rúbrica
aunque sean malas. **Los guardias existen por eso** y no son negociables.

---

## Métrica

**Cobertura validada** = hipótesis que pasan las cinco comprobaciones / hipótesis propuestas.
Dirección: **sube**.

Comando: `python3 -m bio.validar salidas/hipotesis/ --rubrica`

Las cinco comprobaciones, cada una automática:

1. **Falsable** — declara un resultado que la mataría, en forma observable.
2. **Fuente real** — cada afirmación `[V]` cita una URL que el script vuelve a consultar
   y confirma que existe y contiene la afirmación. Si no, falla.
3. **Novedad** — no duplica una hipótesis ya presente en el historial (similitud < umbral).
4. **Prueba y costo** — define el experimento mínimo y estima costo y tiempo.
5. **Dentro de alcance** — no toca mejora de patógenos ni clasificación de función dual-use.

Cómo se lee: el script imprime `cobertura = N/M` y la línea `FALLA: <hipotesis> <comprobacion>`.

## Archivos

- **Mutables:** `salidas/hipotesis/**` (único lugar que el bucle escribe).
- **Protegidos:** `bio/validar.py`, `datos/dorado/**`, `01-ALCANCE-Y-LIMITES.md`,
  `02-PROGRAMA-BUCLE.md`. El bucle **no los toca ni para arreglarlos**. Si puede
  editar la rúbrica, la editará.

## Cada vuelta

1. Lee el estado actual, el historial de vueltas y la lista de callejones sin salida.
2. Propone **UNA** hipótesis, motivada por una brecha detectada en la evidencia.
3. La escribe en `salidas/hipotesis/YYYY-MM-DD-slug.md`.
4. Commit del candidato.
5. Corre `python3 -m bio.validar` con tope de **5 minutos**.
6. Si la cobertura sube o la hipótesis pasa → conserva. Si no → `git revert` al mejor
   conocido. Si crashea → revierte, anota la excepción, sigue.
7. Registra: hipótesis, veredicto, comprobación que falló, motivo.

## Presupuesto

- Vueltas máximas: **200**
- Tiempo máximo: **14 días**
- Costo máximo: **$150** (modelos locales + llamadas frontera contadas para el refutador)

## Cuándo detenerse y preguntar

- Cambiar de dirección de investigación.
- Contactar una organización externa o publicar.
- Cualquier gasto fuera del presupuesto.
- Tocar un archivo protegido.
- Una hipótesis que entra en zona dual-use dudosa: **para y escala a humano**, no la descarte en silencio.

## Agotamiento

Si **25 vueltas seguidas** no mejoran la cobertura, el bucle para y reporta. Un bucle
agotado no es un fracaso: es información de que la rúbrica o el espacio de búsqueda
están mal, o de que la dirección ya está cubierta.

## Guardias (se revierten aunque la métrica mejore)

- La **suite del conjunto dorado** sigue en verde (50 señales etiquetadas).
- **Ninguna fuente inventada**: toda cita `[V]` se re-verifica en vivo.
- **Nada sale de `salidas/hipotesis/`**.
- Ninguna hipótesis viola la comprobación 5 de alcance.
- El número de callejones sin salida **crece** (un bucle que no descarta nada no está aprendiendo).

---

## El trinquete solo mejora lo que ve

Este bucle optimiza **cobertura de hipótesis falsables**, no verdad científica. Puede
llenar la carpeta de hipótesis elegantes que nadie probará nunca. Eso no es un
descubrimiento: es una lista de deseos con buena redacción.

**El correctivo es humano:** un investigador de verdad tiene que leer las 10 mejores y
decir cuáles vale la pena probar en un banco. El bucle prepara el terreno; no cava el pozo.