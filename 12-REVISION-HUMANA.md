# 12 — Del CSV revisado al conjunto dorado

Este comando resuelve la conversión de formato, **no el trabajo humano de etiquetar**.
Nunca propone etiquetas, copia predicciones ni autentica criptográficamente al revisor.

## Comprobar sin escribir

```bash
python3 -m bio.dorado comprobar salidas/preparacion/mi-corrida/revision
```

Lee `revision.csv`, `muestra.jsonl` y `estado.json` de la muestra preparada. Devuelve:

- `PENDIENTE_REVISION_HUMANA` (exit 2): quedan campos ausentes o inválidos.
- `MUESTRA_INSUFICIENTE` (exit 2): todos revisados, pero menos de 50 evaluables.
- `LISTO_PARA_IMPORTAR` (exit 0): revisión completa y al menos 50 casos evaluables.
- Error (exit 1): corrupción, claves/cabeceras repetidas, fuente cambiada, IDs omitidos
  o duplicados, hash incompatible, columnas desconocidas o archivos inválidos.

No modifica los archivos de revisión ni crea el conjunto dorado.

## Lo que completa una persona

En `revision.csv`, sin modificar las columnas fuente:

| Campo | Valores |
|---|---|
| `categoria_humana` | `brote`, `vigilancia`, `sintesis`, `dual-use`, `politica`, `capacidad`, `otro` |
| `severidad_humana` | `baja`, `media`, `alta`, `no_aplica` |
| `origen_etiqueta` | `humano`, únicamente si realmente hubo revisión humana |
| `fecha_revision` | `YYYY-MM-DD`, fecha válida |
| `revisor` | Persona que realizó la revisión, no un modelo |

El nombre y la declaración son registros locales, no prueba de identidad. Revise sin
consultar las predicciones automáticas para no contaminar la referencia.

Un caso ambiguo puede marcarse `informacion_insuficiente`, con revisión completa y
una `nota` que explique su exclusión. No se lo convierte en una etiqueta evaluable.
Todos los casos de la muestra deben seguir presentes: no se acepta borrar los difíciles.
Las exclusiones no reducen el mínimo de 50; prepara una muestra mayor si hace falta.

## Importar: decisión explícita

Solo **después de la revisión humana**:

```bash
python3 -m bio.dorado importar salidas/preparacion/mi-corrida/revision \
  --salida datos/dorado/senales.jsonl \
  --confirmar-revision-humana
```

Sin la confirmación o con revisión incompleta, falla sin crear el destino. Un dorado
existente nunca se sobrescribe, incluso si tiene cero bytes o es un enlace simbólico.
Para otra versión, elige otro archivo nuevo y realiza el cambio operativo conscientemente;
este comando no reemplaza automáticamente el dorado protegido del bucle.

Cada registro importado contiene los hashes del CSV revisado, el snapshot y el
manifiesto de muestra en `procedencia_revision`. Los campos fuente se recuperan del
snapshot, no se reconstruyen desde celdas escapadas para evitar fórmulas de Excel.
Se permite reordenar filas y guardar UTF-8 con BOM; no alterar el contenido fuente.

El archivo se publica completo mediante enlace duro exclusivo, después de escribir
y sincronizar un temporal. Si otro importador crea antes el destino, no lo reemplaza.
Si el filesystem no admite esta operación, se detiene sin publicar; no hay fallback
que sobrescriba. El soporte se comprobó en la carpeta local de este proyecto.

## Después de importar

Vuelve a ejecutar la preparación en una carpeta nueva para medir contra el dorado:

```bash
python3 -m bio.preparacion --salida salidas/preparacion/con-dorado --corte 2026-09-20
```

Usa el corte que corresponda a tu análisis. Cambiar el dorado invalida las huellas de
una corrida anterior del bucle: comienza una corrida nueva, no reutilices su estado.

Importar etiquetas no aprueba hipótesis, fuentes ni publicaciones. La revisión de
cada hipótesis sigue siendo independiente según `10-OPERACION-BUCLE.md`.
