# Estado verificable — 2026-09-19

## Construido

- Recolector de **una fuente (HN/Algolia)**, deduplicación e informe de fallos.
- Radar léxico offline: se abstiene cuando falta historia; no estima riesgo biológico.
- Extractor de referencia por reglas, evaluador por hashes y preparación con muestra ciega.
- Comprobador/importador de revisión humana, sin generar etiquetas ni autenticar personas.
- `bio.bucle`: consumidor acotado de candidatos existentes, con guardias y reanudación.
- `bio.vigilar`: ingesta/preparación finitas, STOP, señales, límites y control de errores.
  **No soporta reanudación ni es un proceso de investigación.** Guía: documento 13.
- Demo sintética offline y GitHub Actions para Python **3.9 y 3.12**.

## Evidencia local de la continuación

```bash
python3 -m unittest discover -s tests -v
python3.12 -m unittest discover -s tests -v
```

Ambas ejecuciones: **164 pruebas, OK** (Python 3.9.6 y 3.12.14). Se conservaron las
pruebas anteriores. El vigilante tiene 23 pruebas; la suite incluye los contratos
separados de crash, deduplicación, presupuesto y reanudación de `bio.bucle`.

La reproducción inicial del vigilante dio **16 pruebas, 1 fallo**: suspensión civil
sin avance monotónico terminaba en `MAX_VUELTAS`. Se corrigió usando tiempo consumido
conservador entre ambos relojes y parada al observar retroceso civil. Se probaron
STOP, SIGTERM, timeout y SIGKILL con procesos reales; suspensión/retroceso se simularon,
**no se suspendió físicamente el Mac**.

Revisión independiente mediante Codex, contexto limpio y sandbox de solo lectura:
identificó dos defectos reproducibles adicionales (entrega tardía durante checkpoint
y estado con código 0 tras excepción inesperada del padre). Ambos se reprodujeron
con nuevas regresiones rojas y se corrigieron; las regresiones pasan en ambas versiones.
El revisor pudo ejecutar 3 pruebas sin temporales por versión; su suite completa
quedó bloqueada por falta de directorio temporal escribible. **No hubo segunda revisión
independiente de los parches finales**: no se presenta su dictamen inicial como aprobación.

### Operación real, sin etiquetas inventadas

```bash
python3 -m bio.vigilar --salida salidas/vigilancia/continuacion-red-20260919 \
  --max-vueltas 1 --max-segundos 90
```

Resultado observado: **1 vuelta, 129 señales únicas, 0 errores**, consultas fallidas 0,
`PREPARACION_COMPLETA`, `PENDIENTE_DORADO`, detector `DATOS_INSUFICIENTES`,
`publicable:false`, `proceso_activo:false`; final `MAX_VUELTAS` en 4.19 s.
Esta vuelta precedió a los dos parches de checkpoint/error; después se ejecutó la
versión final offline sobre los mismos datos, sin otra petición de red:

```bash
python3 -m bio.vigilar --sin-red \
  --entrada salidas/vigilancia/continuacion-red-20260919/titulares.jsonl \
  --salida salidas/vigilancia/continuacion-offline-final-20260919 \
  --max-vueltas 2 --intervalo-segundos 1 --max-segundos 10
```

Resultado: **2 vueltas, 0 errores, un informe**, `PREPARACION_COMPLETA → SIN_CAMBIOS`,
`MAX_VUELTAS` y `publicable:false`. No se reescribieron las corridas previas.

```bash
python3 -m bio.demo --salida salidas/demo/continuacion-20260919
python3 -m bio.dorado comprobar salidas/vigilancia/continuacion-red-20260919/ciclo-001/preparacion/revision
python3 -m bio.bucle --sin-red --max-vueltas 1 --max-segundos 10
```

- Demo: `DEMO_COMPLETA`, 60 registros sintéticos, 0 etiquetas humanas, 0 llamadas de red.
- Revisión: exit 2, `PENDIENTE_REVISION_HUMANA`, **50 pendientes, 0 válidas**.
- Bucle: exit 2, `DORADO_PENDIENTE`, **0 vueltas, 0 aceptadas**, proceso detenido.

Logs, revisión independiente y resultados completos quedan locales en
`salidas/verificacion/continuacion-20260919/` (ignorados por Git).

## CI remoto: separado de las pruebas locales

Se revalidó la [corrida 35460152595](https://github.com/javiercamarapp/bio-humanidad/actions/runs/35460152595)
de `18b7088`: **success**, con pasos de suite realmente ejecutados en Python 3.9 y 3.12.
La nota antigua de CI bloqueado corresponde a la corrida histórica `35458465535`,
no al estado actual. No se cambiaron pagos ni límites de cuenta en esta continuación.
CI de esta nueva entrega: pendiente de push/PR y comprobación remota; no inferirlo del verde local.

## Publicación y privacidad

Repositorio remoto verificado **PUBLIC**; `main` y `feat/radar-reproducible` apuntaban
a `18b7088` al comenzar. No se cambió visibilidad, permisos ni identidad Git existente.
Código/documentación propia bajo MIT; contenido de terceros no se relicencia.

`git ls-files datos salidas` contiene únicamente `.gitkeep` y `datos/ESQUEMA.md`.
Datos crudos, revisiones, salidas y credenciales permanecen ignorados. Gitleaks sobre
el historial previo: **18 commits, no leaks found**. El escaneo no garantiza ausencia
de secretos; se revisa también el conjunto exacto de archivos que se publica. El nombre
y correo del autor existente forman parte del historial público.

## Resultado del presupuesto y límites

- Cambios funcionales: **3/3** (relojes; checkpoint tardío; excepción inesperada).
- Métrica inicial: 1 fallo en las 16 pruebas previas del vigilante; final: 0 fallos
  en las 164 pruebas de suite. No se eliminó ni debilitó ninguna prueba anterior.
- Retenidos: los tres arreglos, pruebas adicionales y guía de operación.
- Descartados: ninguno; se conservó la evidencia roja y los hallazgos del revisor.
- Operación: 1/1 corrida de red, 2/2 corridas offline; ninguna quedó activa.
- Parada de construcción: presupuesto de cambios agotado y bloqueos humanos explícitos.

**Esto NO demuestra** precisión científica, amenazas, descubrimientos, curas ni alertas
sanitarias. Siguen pendientes 50 etiquetas humanas reales, historia multifuente útil,
calibración retrospectiva, extractor por modelo, analista y refutador. No se construyen
variantes biológicas ni evasión de cribados. No basta pasar un validador para declarar
una hipótesis verdadera.

## Siguiente intervención humana

Revisar una muestra sin mirar las sugerencias; comprobar/importar solo etiquetas
realmente completadas siguiendo `12-REVISION-HUMANA.md`. Después, preparar otra
corrida para medir concordancia técnica. La revisión de cada candidato sigue siendo
independiente. Revisar también los parches finales antes de integrar la PR.
