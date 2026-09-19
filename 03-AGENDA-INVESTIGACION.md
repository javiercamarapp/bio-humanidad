# 03 — Agenda de investigación

El hallazgo que abre todo, y las direcciones que salen de él.

---

## HALLAZGO 0 — El "0-day biológico": el cribado de ADN es de forma, no de función

**Marca:** `[P]` — resumen histórico de una fuente periodística secundaria. No se
ha cotejado aquí el estudio original. No es un hallazgo propio ni validación biológica.

**Qué pasó.** Un equipo liderado por Microsoft descubrió y reportó una
vulnerabilidad no reconocida ("biological 0-day") en los programas que examinan
las compras de ADN, según la nota citada. El reporte describe límites del cribado
por similitud de secuencia y estructura. **No demuestra que las variantes conservaran
función biológica**; no se debe deducir actividad peligrosa de una similitud predicha.

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

Es una motivación para revisar evidencia y controles defensivos, no un resultado
del proyecto. Las cifras descritas son de un reporte secundario; falta cotejar
método, población, mitigaciones y alcance. No representan una tasa de daño biológico.

---

## La brecha central (la tesis de este programa)

> El cribado biológico pregunta *"¿se parece a algo peligroso?"*.
> La defensa necesita preguntar *"¿hace algo peligroso?"*, aunque no se parezca a nada.

La primera pregunta es la que la IA puede eludir por diseño. La segunda es
mucho más difícil. No se afirma que nadie la haya resuelto ni que este software
pueda hacerlo: el producto abierto trabaja con metadatos públicos y trazabilidad.

---

## Las direcciones de investigación

Cada una con hipótesis falsable, prueba, lo que la mata y costo.

### D1 y D2 — Fuera del producto abierto

La propuesta original mencionaba predicción de función y priorización experimental.
**No se implementarán aquí clasificadores de peligrosidad, selección de variantes
funcionales/evasivas ni optimización del cribado mediante evasión.** Este repositorio
no distribuye secuencias, protocolos húmedos ni instrucciones para síntesis. Cualquier
investigación especializada requiere una evaluación institucional independiente;
no es una fase que el bucle de este proyecto pueda aprobar.

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

El orden de arriba es una propuesta histórica, no compromisos de implementación.
El alcance del producto abierto se limita a preparación, calidad de datos y metadatos;
D1 y D2 no son tareas pendientes que un agente pueda activar.