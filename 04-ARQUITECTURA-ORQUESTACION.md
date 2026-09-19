# 04 — Arquitectura y orquestación

Cómo se usan varios modelos **sin** que sea "pedir once opiniones".

---

## Principio

No se pide consenso. Se reparten **roles**. Cada modelo hace una cosa distinta y
verificable. La diversidad de modelos aquí es real: el que extrae no es el que
analiza, y el que analiza no es el que refuta.

```
[1 Recolector]   scripts + APIs     →  señales crudas (JSONL)
[2 Extractor]    modelo local 8-30B →  JSON estructurado
[3 Dedup]        embeddings         →  agrupa la misma noticia
[4 Clasificador] modelo local       →  categoría + severidad
[5 Detector]     clustering         →  "raro contra la línea base"
[6 Analista]     frontier           →  explica la anomalía con citas
[7 Refutador]    OTRO frontier      →  intenta tumbarla
[8 Validador]    script             →  re-verifica fuentes en vivo
[9 HUMANO]       tú                 →  firma y decide
```

**Pasos 1-5 y 8 son código.** No gastan tokens de modelos frontera. El gasto caro
está en 6 y 7, que corren pocas veces por semana.

---

## Los tres papeles de modelo (esto sí es orquestar)

| Papel | Modelo | Frecuencia | Por qué ese |
|---|---|---|---|
| Extraer | local (Qwen/Llama vía Ollama) | miles | Barato, privado, corre sin red |
| Analizar | frontier | ~10/semana | Razonamiento largo sobre evidencia |
| Refutar | **otro** frontier distinto | ~10/semana | Sesgo distinto; no se auto-confirma |

**Regla dura:** el refutador **nunca** es el mismo que el analista. Si el mismo modelo
propone y aprueba, no hay verificación, hay eco.

---

## Los prompts por rol

### Extractor (local)
```
Devuelve SOLO JSON. Campos:
fuente, fecha, entidad, claim_literal, categoria, metodo_mencionado,
salvaguarda_mencionada, url, cita.
Si un campo no está en el texto, pon null. No infieras. No resumas.
```

### Analista (frontier)
```
Te doy N señales de esta semana y la línea base de 90 días.
1. Nombra las 3 más anómalas contra esa línea base.
2. Para cada una: qué patrón rompe, qué explicación benigna tiene,
   y qué evidencia la confirmaría o la MATARÍA.
3. Si nada es anómalo, responde solo "sin anomalía" y por qué.
No especules sobre patógenos. Solo señales observables.
```

### Refutador (otro frontier)
```
Estas son las anomalías propuestas y sus fuentes.
Tu único trabajo es TUMBARLAS. Para cada una:
- ¿es ruido o sesgo de cobertura?
- ¿la fuente es débil o secundaria?
- ¿hay una explicación trivial?
Sobrevive solo la que no puedas tumbar. Sé hostil, no cortés.
```

---

## El guardia anti-alucinación (paso 8)

Antes de que nada se publique, un **script** (no un modelo) vuelve a abrir cada URL
citada y confirma que existe y que contiene la afirmación. Una cita que no se
re-verifica **se marca como no verificada y no entra en el informe**.

Esto es lo que separa este pipeline de un generador de texto plausible.

---

## Infraestructura y costo

| Componente | Herramienta | Costo |
|---|---|---|
| Modelo local | Ollama + Qwen o Llama | $0 |
| Embeddings | local | $0 |
| Frontera (analista/refutador) | API, ~20 llamadas/semana | ~$20-40/mes |
| Recolector | cron + curl + Python | $0 |
| Almacén | SQLite o JSONL | $0 |
| **Total** | | **<$50/mes** |

Nada de entrenar. Nada de GPU. Un portátil alcanza.

---

## Estructura del repositorio

```
bio/
  recolector/      fuentes.py, normalizar.py
  extractor/       prompt + cliente local
  dedup/           embeddings
  detector/        clustering y línea base
  analista/        cliente frontera + prompt
  refutador/       cliente frontera distinto + prompt
  validador/       verifica URLs y rúbrica
  informes/        genera el informe semanal
datos/
  senales/         JSONL crudo
  dorado/          las 50 señales etiquetadas a mano (PROTEGIDO)
salidas/
  hipotesis/       único lugar que el bucle escribe
  informes/        informes semanales
prompts/           los tres prompts versionados
```

## Reglas de operación

1. Si el detector no encuentra anomalía, **el informe sale vacío**. El silencio es válido.
2. Toda cifra del informe cita fuente verificada o no aparece.
3. El refutador va siempre; ningún hallazgo se publica sin pasar por él.
4. Los prompts viven en archivos versionados, no en el chat.
5. El humano firma. El pipeline propone.