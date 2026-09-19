# bio humanidad

Programa de defensa biológica asistida por IA. **Encuadre y fase 0.**

> El cribado biológico pregunta *"¿se parece a algo peligroso?"*.
> La defensa necesita preguntar *"¿hace algo peligroso?"*.

Empieza por [`00-LEEME.md`](00-LEEME.md).

## Documentos
| # | Documento |
|---|---|
| 00 | [Qué es y qué no es](00-LEEME.md) |
| 01 | [Alcance y límites](01-ALCANCE-Y-LIMITES.md) |
| 02 | [Programa del bucle](02-PROGRAMA-BUCLE.md) |
| 03 | [Agenda de investigación](03-AGENDA-INVESTIGACION.md) |
| 04 | [Arquitectura y orquestación](04-ARQUITECTURA-ORQUESTACION.md) |
| 05 | [Finanzas](05-FINANZAS.md) |
| 06 | [Mercado](06-MERCADO.md) |
| 07 | [Pitch deck](07-PITCH-DECK.md) |
| 08 | [Guía paso a paso](08-GUIA-PASO-A-PASO.md) |
| 09 | [Blueprint](09-BLUEPRINT.md) |

## Código
```bash
python3 -m bio.recolector.recolector --salida datos/senales/senales.jsonl
python3 -m bio.validador.validar salidas/hipotesis/ --rubrica
```

## Estado
Fase 0. Recolector funcionando. Sin banco húmedo. Sin contratos.
