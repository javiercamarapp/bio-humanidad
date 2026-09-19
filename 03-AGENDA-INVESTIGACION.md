# 03 — Agenda de investigación

El hallazgo que abre todo, y las direcciones que salen de él.

---

## HALLAZGO 0 — El "0-day biológico": el cribado de ADN es de forma, no de función

**Marca:** `[V]` — verificado en fuente primaria pública.

**Qué pasó.** Un equipo liderado por Microsoft descubrió y reportó una
vulnerabilidad no reconocida ("biological 0-day") en los programas que examinan
las compras de ADN. El sistema existente detecta amenazas por **similitud de
secuencia y de estructura**. La vulnerabilidad: las herramientas de diseño de
proteínas por IA ya pueden tomar una toxina conocida y diseñar una proteína con la
**misma función** pero lo bastante distinta como para que el cribado no la marque.

**Evidencia concreta.** Partiendo de 72 toxinas, generaron ~75.000 variantes con
tres paquetes de diseño de proteínas de código abierto y las pasaron por **cuatro
programas de cribado**:

- Los programas variaron **muchísimo** en capacidad de detección: dos lo hicieron
  bien, uno regular, y **uno dejó pasar la mayoría**.
- Tres de los programas se actualizaron y mejoraron notablemente.
- Tendencia en los cuatro: cuanto más parecida la variante en estructura, más
  probable la detección.
- Aun en las versiones **parcheadas**, entre un **1% y 3%** de las variantes "muy
  similares" pasaban sin ser marcadas.
- Las variantes no detectadas se concentraban en **unas pocas toxinas**, no era un
  problema general.

**La limitación que el mismo estudio declara.** No pudieron validar en húmedo
75.000 diseños. Usaron dos aproximaciones por software: similitud de la estructura
predicha y diferencias en las posiciones de los aminoácidos. **Ninguna es un
indicador claro de si las dos proteínas serían igual de funcionales.** La mayoría
de las variantes probablemente son inactivas; muchas serían inútiles como vector.

**El protocolo que usaron, y que vale copiar.** Lo trataron como un zero-day de
ciberseguridad: contacto confidencial con el IGSC y cuerpos relevantes (OSTP, NIST,
DHS, Oficina de Preparación ante Pandemias), **sin publicar detalles hasta tener
mitigaciones y parches desplegados**. Ese es el modelo de divulgación responsable
para bioseguridad.

*Fuente:* Ars Technica, "A biological 0-day? Threat-screening tools may miss
AI-designed proteins", 3-oct-2025 (John Timmer).

### Por qué esto es el hallazgo que ayuda

Porque es **un hueco real, verificable, publicado y sin resolver del todo**. No es
un escenario hipotético: es un 1-3% medido de evasión residual en software que
protege a la humanidad. Y el propio estudio nombra lo que falta: **una señal de
función, no de forma.**

---

## La brecha central (la tesis de este programa)

> El cribado biológico pregunta *"¿se parece a algo peligroso?"*.
> La defensa necesita preguntar *"¿hace algo peligroso?"*, aunque no se parezca a nada.

La primera pregunta es la que la IA puede eludir por diseño. La segunda es
mucho más difícil y **nadie la ha resuelto**. Ahí está el trabajo.

---

## Las direcciones de investigación

Cada una con hipótesis falsable, prueba, lo que la mata y costo.

### D1 — Cribado por función, no por forma

- **Hipótesis:** un predictor de actividad (no de estructura) reduce la evasión
  residual del cribado muy por debajo del 1-3% publicado, a costo de cómputo aceptable.
- **Prueba:** sobre un banco de evasores conocidos, medir el área bajo la curva del
  predictor contra cada uno de los cuatro cribadores actuales.
- **La mata:** que el predictor no supere a la similitud estructural, o que solo
  funcione en las toxinas del conjunto de entrenamiento.
- **Costo:** cómputo, sin banco húmedo. Meses, no años.
- **Riesgo dual-use:** **alto**. Es un clasificador de función. Por decisión de
  `01-ALCANCE`, **no lo construye este programa solo**: se hace en consorcio con
  supervisión estatal, o se contribuye con datos y evaluación a quien ya lo hace.

### D2 — Priorizar qué validar en húmedo

- **Hipótesis:** para un lote de variantes generadas, existe un subconjunto pequeño
  (≤1%) que concentra casi toda la probabilidad de ser funcional y evasor; ordenarlo
  permite que un laboratorio real valide con pocos cientos de pruebas en vez de 75.000.
- **Prueba:** comparar el orden propuesto contra un conjunto pequeño ya validado en húmedo.
- **La mata:** que el orden no correlacione con la función real mejor que el azar.
- **Costo:** cómputo + un banco húmedo pequeño y con licencia.
- **Riesgo dual-use:** **medio**. Es priorización defensiva, pero sirve a ambos lados.
  Requiere revisión.

### D3 — Radar de biosurveilancia multi-fuente

- **Hipótesis:** correlacionar señales públicas heterogéneas (brotes, genómica,
  aguas residuales, pedidos anómalos, preprints) detecta una anomalía **antes** de que
  los sistemas actuales la marquen.
- **Prueba:** retrospectiva. Reproducir tres brotes conocidos con datos públicos y
  medir el adelanto en días contra la línea base de cada uno.
- **La mata:** cero adelanto, o adelanto solo con datos a los que no se tendría
  acceso en tiempo real.
- **Costo:** casi todo cómputo y scraping. **Barato y empezable hoy.**
- **Riesgo dual-use:** **bajo**. Es esta la que arranca primero.

### D4 — Evals de salvaguardas bio, reproducibles

- **Hipótesis:** existe un conjunto público de pruebas, con criterios explícitos,
  que mide la **tasa de sobre-negativa y de falso-refusal** de los modelos en bio
  y que cualquier tercero puede correr y comparar.
- **Prueba:** correr la suite sobre dos o más modelos y publicar el número.
- **La mata:** que los resultados no sean reproducibles entre corridas, o que
  mida lo mismo que los evals ya existentes.
- **Costo:** bajo. **Publicable.**
- **Riesgo dual-use:** **bajo-medio**. Mide negativas, no elicita capacidad.

### D5 — Diagnóstico y antivirales de amplio espectro: mapa de preparación

- **Hipótesis:** la brecha de preparación no es científica sino de capacidad de
  fabricación y de plataforma; un mapa de desempeño por plataforma adelanta la
  respuesta en una pandemia novel.
- **Prueba:** comparar tiempos históricos de plataforma (mRNA, nanopartícula,
  CRISPR-dx) contra lo prometido.
- **La mata:** que no haya diferencia operativa entre plataformas.
- **Riesgo dual-use:** **bajo**. Es análisis de política y capacidad.

---

## Orden de arranque

| Prioridad | Dirección | Por qué primero |
|---|---|---|
| 1 | **D3 — Radar** | Barata, hoy, sin permisos, y da reputación |
| 2 | **D4 — Evals** | Reproducible, publicable, abre puertas |
| 3 | **D5 — Mapa** | Análisis puro, útil para financiación |
| 4 | **D2 — Priorización** | Necesita socio húmedo |
| 5 | **D1 — Función** | Solo con consorcio y supervisión |

**D1 es el hallazgo grande. Y es precisamente la que no se hace en solitario.** Ese
es el precio de hacerlo bien.