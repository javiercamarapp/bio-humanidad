# 08 — Guía paso a paso

Qué hacer, en qué orden, desde hoy.

---

## Fase 0 — Radar y evals (semanas 1-12). Cuesta <$500.

### Semana 1-2 — Rigor antes de código
- [ ] Escribir el **alcance** (ya en `01`). No cambiar sin motivo nuevo.
- [ ] Elegir **una** dirección para empezar: **D3, el radar**.
- [ ] Definir qué es "señal" y qué es "anomalía", en una página.
- [ ] Instalar Ollama + un modelo local (Qwen 7-14B). Verificar que corre sin red.

### Semana 3-4 — Recolector
- [ ] Cinco fuentes: ProMED-mail, CIDRAP, bioRxiv/medRxiv, GISAID/Nextstrain, HN/RSS.
- [ ] Script que corre cada hora, normaliza a JSON y guarda con URL y fecha.
- [ ] **Sin IA todavía.** Solo recolección. Si el recolector es frágil, nada más importa.

### Semana 5-6 — Extracción y conjunto dorado
- [ ] Extractor con el prompt de `04`, en modelo local.
- [ ] Etiquetar a mano 50 señales: categoría y severidad. **Este es el conjunto dorado.**
- [ ] Medir la precisión del extractor contra él. Publicar el número, aunque sea 0.6.
- [ ] Proteger el archivo del conjunto dorado (el bucle no lo toca).

### Semana 7-8 — Detección de anomalías
- [ ] Embeddings + clustering.
- [ ] Construir la línea base de 90 días.
- [ ] La pregunta es "¿qué es raro?", no "¿qué pasó?".

### Semana 9-10 — Analista y refutador
- [ ] Cliente de modelo frontera para el analista.
- [ ] Cliente de **otro** modelo para el refutador.
- [ ] Guardia anti-alucinación: script que re-abre cada URL citada.
- [ ] Regla: sin refutación, no hay hallazgo.

### Semana 11-12 — Primer informe público
- [ ] Generar el primer informe semanal con método y umbrales visibles.
- [ ] Publicarlo como informe abierto.
- [ ] Escribir a NTI|bio, Johns Hopkins CHS e IBBIS con el informe, pidiendo *qué falta*.

**Entregable de la fase 0:** 12 semanas de alertas publicadas y 3 conversaciones abiertas.

---

## Fase 1 — Evals bio reproducibles (meses 4-9)

- [ ] Diseñar la suite: qué mide, qué cuenta como fallo, cómo se reporta.
- [ ] Correrla sobre ≥2 modelos y publicar comparación.
- [ ] Someter a revisión externa (una persona respetada, no un amigo).
- [ ] Aplicar a una beca pequeña con los resultados en mano.

**Entregable:** un eval bio reproducible que un tercero puede correr.

---

## Fase 2 — Credibilidad e ingresos (meses 10-18)

- [ ] Primer contrato/piloto con salud pública o filantropía.
- [ ] Auditoría externa del pipeline.
- [ ] Informe de preparación por plataforma (D5).
- [ ] Definir estructura legal: PBC o non-profit.

**Entregable:** financiación que no depende de tu bolsillo.

---

## Fase 3 — Priorización con banco húmedo (años 2-3)

- [ ] Alianza con un laboratorio con licencia.
- [ ] D2: priorizar qué validar en húmedo, con pocos cientos de pruebas.
- [ ] D1 (cribado por función) **solo** dentro de consorcio con supervisión estatal.

---

## Reglas para no descarrilar

1. **Una dirección a la vez.** El radar primero. No abras D1 hasta tener fase 0.
2. **Nada sin fuente.** Una cifra sin cita no entra.
3. **Publica los fracasos.** Son el activo de credibilidad.
4. **No prometas el descubrimiento.** Promete método y evidencia.
5. **Cuando dudes, haz la llamada**, no la investigación. Cinco conversaciones valen
   más que once modelos.
6. **Si el bucle se agota, para.** Un bucle agotado es información, no fracaso.

---

## Qué hacer mañana, exactamente

Tres cosas, en este orden, y ninguna necesita permiso de nadie:

1. `ollama pull qwen2.5:14b` y verificar que responde sin conexión.
2. Escribir el recolector de **una** fuente (ProMED o bioRxiv). Solo una.
3. Crear el archivo vacío del conjunto dorado y etiquetar la primera señal a mano.

Con eso ya empezó el programa. El resto es repetición y rigor.