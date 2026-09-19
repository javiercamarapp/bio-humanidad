# Esquema de señal y de hipótesis

## Señal (datos/senales/*.jsonl)
```json
{"id":"sha1(url)","fuente":"","fecha":"YYYY-MM-DD","entidad":"",
 "claim_literal":"","categoria":"brote|vigilancia|sintesis|dual-use|politica|capacidad|otro",
 "metodo_mencionado":null,"salvaguarda_mencionada":null,"url":"","cita":"",
 "recolectado_en":"ISO8601","verificado":false}
```

## Hipótesis (salidas/hipotesis/*.md)
Frontmatter obligatorio para que la rúbrica la valide:
```yaml
---
id: slug
falsable: "resultado observable que la mataría"
prueba: "experimento mínimo"
costo: "USD y tiempo"
alcance: "defensa|preparacion|vigilancia|evals"
fuentes: ["url1","url2"]
estado: propuesta|refutada|sobrevive
---
```

## Regla
Un archivo sin `falsable` no pasa. Una fuente que no se re-verifica no pasa.
Una hipótesis fuera de `alcance` permitido se escala a humano, no se descarta en silencio.
