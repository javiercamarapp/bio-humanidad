# Referencia — El 0-day biológico

**Fuente primaria:** Ars Technica, "A biological 0-day? Threat-screening tools may
miss AI-designed proteins", John Timmer, 3-oct-2025.
https://arstechnica.com/science/2025/10/do-ai-designed-proteins-create-a-biosecurity-vulnerability/

**Marca:** [V] verificado en fuente pública.

## Hechos
- Equipo liderado por Microsoft; la vulnerabilidad se trató como zero-day.
- Cribado actual: similitud de secuencia y de estructura.
- 72 toxinas → ~75.000 variantes generadas con 3 paquetes de diseño de proteínas open source.
- Cuatro programas de cribado evaluados: 2 bien, 1 regular, 1 dejó pasar la mayoría.
- Tres programas se actualizaron; la evasión residual entre las variantes "muy similares"
  quedó en 1-3%.
- Las variantes no detectadas se concentraron en unas pocas toxinas.
- No hubo validación húmeda (inviable para 75.000 diseños). Se usaron dos aproximaciones
  por software: similitud de estructura predicha y diferencias de posición de aminoácidos.
  Ninguna indica con claridad si la proteína sería funcional.
- Divulgación responsable: contacto confidencial con IGSC, OSTP, NIST, DHS y la Oficina
  de Preparación ante Pandemias antes de publicar.

## Lectura
El hueco no es de implementación: es conceptual. Se mide forma, no función. Y la IA
puede cambiar la forma sin cambiar la función.

## Límites de esta fuente
- Los resultados son sobre estructura **predicha**, no medida.
- No hay confirmación biológica de que alguna variante evadida sea funcional.
- Es de oct-2025; verificar si hay seguimiento o mitigaciones posteriores. [P]
