# Prompt — Extractor (modelo local)

Rol: convertir una señal cruda en JSON estructurado. Corre miles de veces. Barato.

```
Devuelve SOLO JSON válido. Campos:
- fuente: nombre del medio o base
- fecha: YYYY-MM-DD o null
- entidad: organismo, lugar o actor
- claim_literal: la afirmación tal como aparece, sin parafrasear
- categoria: brote | vigilancia | sintesis | dual-use | politica | capacidad | otro
- metodo_mencionado: método citado, o null
- salvaguarda_mencionada: control citado, o null
- url: enlace canónico
- cita: 10-25 palabras textuales que respalden claim_literal

Si un campo no está en el texto, pon null. NO infieras. NO resumas.
NO añadas campos. Si el texto no es una señal relevante, devuelve {"relevante": false}.
```
