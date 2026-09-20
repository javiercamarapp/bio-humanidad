# Progreso — continuación operativa

## Verificado
- Recolector RSS/Atom CDC/ECDC/OMS, unión offline e integración de vigilancia.
- Operación real:535 RSS; unión664/4 fuentes/1 día. Hashes intactos, sin etiquetas humanas.
- 223 pruebas OK en Python3.9.6/3.12.14. Las205 anteriores intactas por bytes.
- Ollama instalado y pipeline local opt-in conectado: extractor, analista documental y
  refutador de otra familia/digest. Dos señales reales,6 solicitudes,92.85s y hashes
  comprobados. Sin dorado: calidad no medida, no publicable.
- Perfil27B agotó180s en el segundo registro; fallo conservado. Perfil menor observado
  con máximo1 modelo cargado/7.83GB reportados. No se infiere calidad de la velocidad.

## Integración y operación vigente
- PR3 (fuentes) y PR4 (instalación documentada) integradas. Ampliación actual: issue5,
  su PR y checks son la referencia; no se supone integración antes de revisión/CI.
- Corrida anterior detenida por STOP tras2 vueltas/0 errores antes de construir.
  Continuidad posterior: máximo22 vueltas y tiempo civil restante del presupuesto
  original, sin LLM automáticos. Estado real en salidas/vigilancia/ y
  salidas/verificacion/pipeline-local-20260920/cierre.json.
  Este documento no es prueba de que haya un proceso activo.

## Siguiente
- Integrar solo con controles cumplidos; continuar ingesta dentro del presupuesto
  restante original, sin cambiar código mientras corre. Guía16 documenta flujo local.

## Bloqueos reales
- Revisión de50 señales por una persona.
- Revisión de criterios/representatividad/cobertura y observaciones históricas reales.
- Calidad semántica de los roles no probada sin referencia humana. Modelos frontera
  del diseño histórico no sustituidos por estos roles documentales.
- APIs pagadas siguen sin autorizar (USD0); ningún proveedor externo habilitado.
