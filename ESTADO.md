# Estado verificable — 2026-09-19

## Construido

- Recolector de **una fuente (HN/Algolia)**, deduplicación e informe de fallos.
- Radar léxico offline: se abstiene cuando falta historia; no estima riesgo biológico.
- Extractor de referencia por reglas con abstención, sin modelo de IA conectado.
- Evaluador de categorías con cobertura, errores de esquema y trazabilidad por hash.
- Pipeline de preparación con snapshots, muestra ciega y reporte no publicable.
- Ejecutor acotado con guardias, historial, presupuesto y reanudación.
- Comprobador e importador explícito de revisión humana, sin generar etiquetas.
- Workflow de GitHub Actions para ejecutar la suite offline en Python 3.12.

## Evidencia local

```bash
python3 -m unittest discover -s tests -v
```

Última ejecución local: **137 pruebas, OK**. Se usan fixtures sintéticos y temporales,
no un conjunto dorado inventado dentro del proyecto. El estado actual del CI remoto
se consulta en la pestaña Actions; esta nota no sustituye al resultado de cada corrida.

Preparación real verificada: **129 señales de HN**, 52 sugerencias temáticas, 77
abstenciones y 50 casos sin etiquetar para revisión. Se verificaron hashes de artefactos,
reproducibilidad de predicciones y conservación de los datos originales.

`bio.dorado comprobar` sobre esa muestra devuelve `PENDIENTE_REVISION_HUMANA`, con
**50 pendientes y 0 válidas**. No se ha importado un dorado real.

## Lo que esto NO demuestra

- No es validación científica, descubrimiento ni una alerta sanitaria.
- No hay precisión real medida: falta el conjunto dorado humano.
- No hay línea base multifuente de 90 días utilizable.
- No se han conectado extractor por LLM, analista ni refutador.
- Los nombres de revisores son registros locales, no autenticación criptográfica.
- El bucle de hipótesis se detiene en `DORADO_PENDIENTE`, con cero vueltas.
- No hay un proceso de investigación ejecutándose en segundo plano.

## Qué se sube y qué permanece local

Código, pruebas, prompts, documentación y este resumen agregado están versionados.
`datos/**` y `salidas/**` permanecen ignorados salvo los archivos explícitos de esquema
y estructura. No se publican datos crudos, CSV de revisores, aprobaciones humanas,
cachés ni credenciales. No se cambió la visibilidad privada del repositorio.

## Continuación operativa

1. Revisar la muestra sin consultar las sugerencias automáticas.
2. Comprobar e importar únicamente la revisión humana completada:
   [`12-REVISION-HUMANA.md`](12-REVISION-HUMANA.md).
3. Ejecutar una preparación nueva y medir calidad sin ocultar abstenciones.
4. Ampliar ingesta e historia, antes de interpretar novedades como anomalías.

No basta con hacer pasar un validador para declarar una hipótesis verdadera.
