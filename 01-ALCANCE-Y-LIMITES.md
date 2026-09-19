# 01 — Alcance y límites

Aplica `goal-writer`: separar el resultado del proceso, y separar **éxito** de **límite**.

---

## Objetivo de la fase 1 (medible)

Producir un **programa de investigación de defensa biológica** con:

1. Entre 4 y 6 direcciones de investigación, cada una con:
   - hipótesis enunciada como predicción **falsable**,
   - experimento mínimo que la prueba,
   - qué resultado la **mataría**,
   - costo y tiempo estimados,
   - estado del arte y quién más lo intenta.
2. Un pipeline de IA reproducible que genere y refute esas hipótesis.
3. El modelo financiero y de mercado que lo sostiene.
4. Una guía de ejecución por fases.

## Qué cuenta como éxito

- Un tercero puede leer el programa y **ejecutar la fase 1 sin preguntarte nada**.
- Cada hipótesis tiene una prueba de falsación explícita y un costo estimado.
- El pipeline corre y produce el informe semanal sin intervención manual.
- Todo lo afirmado tiene marca `[V]` / `[I]` / `[P]` y fuente cuando es `[V]`.

## Qué cuenta como límite (y detiene el trabajo)

- Se agota el presupuesto de tiempo o vueltas declarado en `02-PROGRAMA-BUCLE.md`.
- Una decisión exige gasto, contratación o acceso que no controlas.
- Aparece una cuestión de alcance: cambiar de dirección de investigación.

Al alcanzar el límite **se informa estado parcial y trabajo pendiente**. No se
interpreta el límite como objetivo cumplido.

---

## Alcance

**Dentro:**
- Biosurveilancia y alerta temprana.
- Cribado de síntesis de ácidos nucleicos.
- Inteligencia dual-use: qué se publica y quién.
- Evals de salvaguardas de modelos.
- Vacunas, antivirales de amplio espectro y diagnóstico **como direcciones de
  preparación**, no como desarrollo de producto propio.
- Política, estándares y financiación de preparación.

**Fuera, y por qué:**

| Fuera | Razón |
|---|---|
| Mejora de patógenos, gain-of-function | Un mapa de peligrosidad invertido es un optimizador de peligrosidad |
| Clasificadores de función de secuencias nuevas | Dual-use; requiere consorcio con supervisión estatal |
| Generación de instrucciones de síntesis | El artefacto hace daño, no la intención |
| Operación de modelos con salvaguardas removidas | Descalifica de todo consorcio y agencia; no es una estrategia |
| Pretender validar en húmedo sin laboratorio | Mentira técnica |

## Restricciones

- Sin acceso a BSL-3/4 ni a patógenos. Todo el trabajo es **de datos y de cómputo**.
- Todo dato de entrada es **público** o propio.
- Ningún artefacto de esta carpeta es un protocolo de mejora.
- El pipeline no decide: propone, y un humano firma.

## Comportamiento esperado

- El sistema propone anomalías e hipótesis, y **también sus refutaciones**.
- Cuando no hay señal, lo dice. El silencio es una salida válida.
- Nunca inventa una fuente ni un resultado.

## Verificación

- El pipeline corre con `python3 -m bio.radar --semana actual` y escribe un informe.
- Cada informe cita la fuente primaria de cada afirmación.
- Existe un conjunto dorado de 50 señales etiquetadas a mano; la precisión se mide
  contra él y se publica el número, aunque sea bajo.
- Un refutador independiente intenta tumbar cada hallazgo antes de publicarlo.

## Intervenciones que exigen humano

- Cambiar de dirección de investigación.
- Publicar cualquier cosa fuera de la carpeta.
- Escribir a una organización externa.
- Cualquier gasto fuera del presupuesto declarado.
- Tocar los archivos protegidos del bucle.