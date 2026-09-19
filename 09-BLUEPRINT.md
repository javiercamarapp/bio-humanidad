# 09 — Blueprint

La forma completa del programa, en una página. Une `03`, `04` y `05` en un sistema.

---

## Tesis

> El cribado biológico pregunta *"¿se parece a algo peligroso?"*.
> La defensa necesita preguntar *"¿hace algo peligroso?"*.
> Nadie ha resuelto la segunda pregunta, y es resoluble.

## Modelo de amenaza

Una IA baja el costo de diseñar, adquirir o soltar una amenaza biológica. Los cuellos
de botella existentes —síntesis de ADN, conocimiento, materiales, diseminación— se
estrechan donde había barreras de conocimiento, no de física. **La barrera de física
es el cribado de síntesis, y esa barrera tiene un agujero de 1-3% medido.** `[V]`

## Los cuatro pilares

```
PILAR 1  Detección temprana        →  Radar multi-fuente (D3)
PILAR 2  Cribado que funciona       →  Por función, no por forma (D1)
PILAR 3  Medición honesta           →  Evals de salvaguardas (D4)
PILAR 4  Preparación y política     →  Mapa de plataformas (D5) + estándares
```

## Arquitectura técnica

```
 Fuentes públicas  →  Recolector (código)  →  Extractor (local)
        →  Detector (clustering)  →  Analista (frontera)
        →  Refutador (OTRO frontera)  →  Validador (código)
        →  HUMANO firma  →  Informe público
```

Costo <$50/mes. Sin entrenar. Sin GPU. Sin banco húmedo en fase 0.

## El trinquete (fase de investigación)

Bucle acotado (`02`) que **acumula hipótesis falsables** y descarta las malas.
200 vueltas, 14 días, $150. Se detiene si 25 vueltas no mejoran. **No descubre:
prepara el terreno para que un laboratorio descubra.**

## Modelo financiero

| Fase | Costo | Fuente |
|---|---|---|
| 0 — radar + evals | <$500 | propio |
| 1 — informe público | $2-8K | beca pequeña |
| 2 — credibilidad | $30-80K | grant + contrato |
| 3 — banco húmedo | $300K-2M | BARDA / filantropía / consorcio |

## Go-to-market

Empezar por dolor existente, no por necesidad inventada: gobiernos de biodefensa y
salud pública global. Validar el comprador asegurador con cinco llamadas antes de
construir nada para él.

## Las siete decisiones que definen el programa

1. **Defensa, no mejora.** Sin excepciones.
2. **Verificar antes de publicar.** El guardia anti-alucinación no es opcional.
3. **Refutador distinto del analista.** Siempre.
4. **Publicar los fracasos.** Es el activo de credibilidad.
5. **D1 (el hallazgo grande) solo en consorcio con supervisión estatal.** Ese es el
   precio de hacerlo bien.
6. **El bucle prepara; el humano decide.**
7. **No prometer descubrimiento. Prometer evidencia, método y divulgación responsable.**

## Riesgos y qué los mata

| Riesgo | Mitigación |
|---|---|
| Sospecha dual-use | Alcance escrito y auditado; D1 en consorcio |
| El comprador no existe aún | Fase 0 filantrópica, no comercial |
| Optimizar el proxy de la rúbrica | Guardias + revisión humana |
| Burnout por dispersión | Una dirección a la vez; el radar primero |
| Falsa sensación de seguridad | Declarar qué no se resuelve |

## Estado actual

- [x] Encuadre, alcance y límites.
- [x] Especificación del bucle.
- [x] Agenda de investigación con el hallazgo 0-day verificado.
- [x] Arquitectura y orquestación.
- [x] Finanzas, mercado, pitch y guía.
- [ ] Recolector corriendo (siguiente).
- [ ] Conjunto dorado de 50 señales.
- [ ] Primer informe público.

**El siguiente paso no es pensar más. Es `ollama pull` y el primer recolector.**