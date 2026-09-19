# bio humanidad

[![Pruebas](https://github.com/javiercamarapp/bio-humanidad/actions/workflows/tests.yml/badge.svg)](https://github.com/javiercamarapp/bio-humanidad/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**Software open source para preparar y auditar metadatos públicos de salud y bioseguridad.**
Recolecta titulares, conserva procedencia, propone categorías con abstención y prepara
revisión humana. Es una herramienta de calidad de datos: **no descubre curas, no valida
amenazas biológicas y no publica alertas automáticamente**.

El código y la documentación propia se distribuyen bajo [MIT](LICENSE). Los artículos,
datos y servicios externos conservan sus derechos y condiciones; no se relicencian.

## Inicio rápido — sin cuenta, red ni modelos

Requisitos: Python **3.9+**, macOS o Linux; en Windows, usar WSL. Solo biblioteca
estándar. No requiere API keys, instalación de dependencias ni acceso a un laboratorio.

```bash
git clone https://github.com/javiercamarapp/bio-humanidad.git
cd bio-humanidad
python3 -m unittest discover -s tests -v
python3 -m bio.demo --salida salidas/demo/primera
```

Abre `salidas/demo/primera/preparacion/informe.md`. La demo produce 60 registros
**explícitamente sintéticos**, 50 casos sin etiquetar y métricas pendientes. No crea
un conjunto dorado humano ni hace peticiones de red. Usa otra carpeta para repetirla;
no sobrescribe resultados anteriores.

## Qué está construido

| Componente | Comportamiento real |
|---|---|
| `bio.recolector.recolector` | Titulares de HN/Algolia, una fuente; deduplicación y fallos visibles |
| `bio.radar` | Normalización, muestra ciega y comparación léxica; se abstiene sin historia suficiente |
| `bio.extractor` | Reglas versionadas; evidencia literal y abstención, no un LLM |
| `bio.evaluacion` | Cobertura, exactitud global/selectiva, errores de esquema y hashes incompatibles |
| `bio.preparacion` | Pipeline offline con snapshots, reporte y hashes de artefactos/código |
| `bio.dorado` | Comprueba e importa revisiones realmente completadas, con confirmación explícita |
| `bio.validador.validar` | Controles técnicos, revisión humana por hash y citas; no prueba verdad científica |
| `bio.bucle` | Consume candidatos existentes con límites, historial y guardias; no genera hipótesis |
| `bio.demo` | Demostración reproducible con datos sintéticos, sin coste API |
| `bio.vigilar` | Ingesta/preparación acotadas, STOP y presupuesto; no investigación autónoma |

## Procesar datos reales

El siguiente comando **sí consulta HN/Algolia**. Respeta sus términos y límites. La
fuente es parcial y sesgada: HN no equivale a vigilancia sanitaria multifuente.

```bash
python3 -m bio.recolector.recolector --salida datos/senales/senales.jsonl
python3 -m bio.preparacion \
  --entrada datos/senales/senales.jsonl \
  --salida salidas/preparacion/primera \
  --corte 2026-09-20
```

Elige un corte UTC adecuado: es exclusivo (`2026-09-20` incluye observaciones hasta
el día 19). Las fechas antiguas de publicación **no fabrican 90 días de recolección**.

La salida contiene `informe.md`, `manifest.json`, snapshots, predicciones,
`deteccion.json`, `metricas.json` y `revision/revision.csv`.
`PREPARACION_COMPLETA` significa archivos producidos, **no** investigación validada.
Sin etiquetas humanas, la calidad queda sin medir; sin historia, el detector se abstiene.

## Vigilancia pública finita

Para coordinar ingesta y preparación en una carpeta nueva:

```bash
python3 -m bio.vigilar --salida salidas/vigilancia/primera \
  --max-vueltas 1 --max-segundos 90
```

Consulta HN/Algolia, no ejecuta modelos y mantiene `publicable:false`. Ofrece
`--sin-red --entrada ARCHIVO`, deduplicación por corrida, parada con archivo `STOP`
y límites que incluyen suspensión simulada. No es un daemon ni soporta reanudación;
una corrida interrumpida se conserva, nunca se sobrescribe. Guía y límites:
[13-VIGILANCIA-ACOTADA.md](13-VIGILANCIA-ACOTADA.md).

## Revisión humana — no se salta

```bash
python3 -m bio.dorado comprobar salidas/preparacion/primera/revision
```

Una persona completa categoría, severidad, origen, fecha y revisor **sin consultar las
sugerencias automáticas**. El importador exige todos los casos revisados, al menos
50 evaluables y fuentes intactas. No inventa etiquetas ni reemplaza un archivo existente.

Solo después de esa revisión:

```bash
python3 -m bio.dorado importar salidas/preparacion/primera/revision \
  --salida datos/dorado/senales.jsonl --confirmar-revision-humana
```

Detalles y exclusiones por ambigüedad: [12-REVISION-HUMANA.md](12-REVISION-HUMANA.md).
Los nombres declarados no son autenticación criptográfica ni validación científica.

## Bucle de candidatos

```bash
python3 -m bio.bucle --max-vueltas 200 --max-segundos 900
python3 -m bio.bucle --reanudar salidas/bucle/ID_DE_CORRIDA
```

Sin dorado válido, termina con `DORADO_PENDIENTE` antes de la primera vuelta. Después
requiere revisión humana por candidato. No propone variantes biológicas, no escribe
aprobaciones, no publica y no llama modelos. Presupuesto, exclusión entre procesos,
checkpoints y paradas: [10-OPERACION-BUCLE.md](10-OPERACION-BUCLE.md).

## Lo que falta y lo que está fuera de alcance

**Pendiente:** datos humanos reales, ingesta multifuente con historia, calibración
retrospectiva, extractor por modelo local, analista y refutador. No se presentan
componentes pendientes como si ya corrieran.

**Fuera de alcance:** mejora de patógenos, síntesis, secuencias, predicción de
peligrosidad, selección de variantes funcionales/evasivas y optimización de evasión
de cribado. Estos límites describen el proyecto y las contribuciones aceptadas;
no añaden restricciones a la licencia MIT.

Los documentos iniciales `00–09` contienen propuestas históricas, no resultados
científicos. Se corrigieron afirmaciones que confundían periodismo con fuentes
primarias o estructura predicha con funcionalidad demostrada. Véase
[la referencia y sus límites](referencias/HALLAZGO-0DAY.md).

## Pruebas, CI y publicación

```bash
python3 -m unittest discover -s tests -v
```

La suite usa fixtures temporales, sin red ni datos reales. CI está configurado para
Python 3.9 y 3.12 en GitHub Actions, con permisos de lectura y acciones fijadas por SHA.
Consulta el badge y [ESTADO.md](ESTADO.md): las pruebas locales no sustituyen a un
job remoto que no llegó a ejecutarse. Los runners estándar de repos públicos suelen
ser gratuitos; restricciones de cuenta pueden impedir ejecutarlos igualmente.

Git ignora `datos/**`, `salidas/**`, cachés y credenciales, salvo esquemas y estructura
explícitamente versionados. Abrir el repositorio no publica los datos locales ni
convierte contenido externo en MIT. El historial de Git incluye nombre y correo de autor.

## Documentación y comunidad

- [Estado verificable](ESTADO.md)
- [Alcance y límites](01-ALCANCE-Y-LIMITES.md)
- [Programa operativo](PROGRAMA.md)
- [Operación del bucle](10-OPERACION-BUCLE.md)
- [Preparación offline](11-PREPARACION-OFFLINE.md)
- [Revisión humana](12-REVISION-HUMANA.md)
- [Vigilancia pública acotada](13-VIGILANCIA-ACOTADA.md)
- [Contribuir](CONTRIBUTING.md) · [Seguridad](SECURITY.md) · [Licencia](LICENSE)

Autor: Javier Cámara Portepetit · [GitHub](https://github.com/javiercamarapp)
