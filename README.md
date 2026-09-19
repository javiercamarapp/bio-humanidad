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
| 10 | [Operar el bucle de validación](10-OPERACION-BUCLE.md) |
| 11 | [Pipeline de preparación offline](11-PREPARACION-OFFLINE.md) |
| 12 | [Comprobar e importar revisión humana](12-REVISION-HUMANA.md) |

## Código
```bash
python3 -m bio.recolector.recolector --salida datos/senales/senales.jsonl
python3 -m bio.validador.validar salidas/hipotesis/ --rubrica
python3 -m bio.preparacion --salida salidas/preparacion/mi-corrida --corte 2026-09-20
python3 -m bio.dorado comprobar salidas/preparacion/mi-corrida/revision
python3 -m bio.bucle --max-vueltas 200 --max-segundos 900
python3 -m unittest discover -s tests -v
```

Usa una carpeta nueva y el corte UTC apropiado para cada preparación.
`PREPARACION_COMPLETA` no significa validación científica: revisa `estado_validacion`.

## Estado
Fase 0. Recolector de HN, radar léxico offline, extractor de referencia por reglas,
evaluador de categorías, importador explícito de revisión humana y ejecutor acotado implementados. Sin modelos conectados,
sin banco húmedo ni contratos. La revisión humana y la historia multifuente siguen
pendientes: no hay alertas científicamente validadas ni publicación automática.

[Estado verificable y pendientes](ESTADO.md). GitHub Actions está configurado para la
suite offline en pushes a `main` y pull requests, sin datos reales ni credenciales de
servicios. **La primera ejecución remota fue bloqueada por facturación/límite de gasto
de GitHub; no está verificada en CI.** Las pruebas locales sí pasan.
