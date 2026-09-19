# 14 — Metadatos multifuente y continuidad

## Qué hace y qué NO hace

HN sigue siendo el recolector predeterminado. Se añaden feeds públicos sin llaves:

| Selector | Feed observado el2026-09-19 | Límite |
|---|---|---|
| `cdc` | CDC Online Newsroom, tools.cdc.gov/api/v2/resources/media/132608.rss | primeros500 items |
| `ecdc` | ECDC CDTR, www.ecdc.europa.eu/en/taxonomy/term/1505/feed | primeros500 items |
| `oms` | OMS noticias, www.who.int/rss-feeds/news-english.xml | primeros500 items |

No son tres sistemas exhaustivos de vigilancia epidemiológica. Noticias, comunicados
y reportes semanales tienen frecuencias y sesgos distintos. Una respuesta200 no prueba
actualidad: el manifiesto registra antigüedad, items omitidos y errores. El endpoint
antiguo CDC `/mmwr/rss/mmwr.xml` devolvió2018; CIDRAP `/rss.xml`,2022. No se incorporaron.
El feed OMS probado tenía publicación más reciente206 días antes; se conserva esa
advertencia, no se presenta como alerta reciente. Nunca se heredan aprobaciones del XML.

## Recolección de una tanda

```bash
python3 -m bio.recolector.multifuente \
  --fuentes cdc ecdc --salida salidas/fuentes/tanda-001
```

`--salida` debe ser carpeta nueva. Produce XML crudos, `senales.jsonl` y `manifest.json`
con hashes, URL, instante real de recolección y estadísticas por fuente. No sobrescribe
históricos. `RECOLECCION_COMPLETA` significa que se procesó el lote acotado, NO cobertura
completa ni verdad científica. Una fuente fallida o items inválidos dan salida2 y estado
parcial conservando evidencia; todas vacías tampoco son éxito. No publica.

Cada descarga: HTTPS, host fijo/443, sin seguir redirecciones automáticamente
(un cambio de endpoint exige revisión),2MiB máximo,15s mediante proceso hijo. El hijo tiene además vigilancia de su propio
plazo y del padre; si el padre muere, no queda una descarga indefinida. Solo termina
su propio proceso, no usa PIDs del estado para matar otros procesos. XML UTF8 RSS2/Atom,
sin DTD/entidades declaradas y con límites de estructura. Fechas ausentes, sin zona o
futuras no se inventan. `recolectado_en` no se sustituye por fecha de publicación.

## Vigilancia finita (sin cron ni daemon instalado)

```bash
python3 -m bio.vigilar --fuentes cdc ecdc \
  --salida salidas/vigilancia/rss-dia-001 \
  --max-vueltas 24 --intervalo-segundos 3600 --max-segundos 86400
```

Respeta STOP, señales y los límites existentes. Cada ciclo guarda la recolección
original antes de agregar URLs nuevas; comprueba el hash del snapshot antes de usarlo.
Un ciclo parcial no habilita un informe. No mezclar `--fuentes` con `--sin-red`.
Para detener: crear `STOP` dentro de la carpeta de esa corrida. Sin `--fuentes`, HN.
No está instalado como tarea del sistema. No promete que el Mac siga despierto ni que
24h produzcan90 días de historia. Tras terminar, conservar la carpeta y elegir otra.

## Unir historia sin inventarla

```bash
python3 -m bio.historial \
  --entrada salidas/fuentes/tanda-001/senales.jsonl \
            salidas/vigilancia/otra-corrida/titulares.jsonl \
  --salida salidas/historial/acumulado-001
python3 -m bio.preparacion \
  --entrada salidas/historial/acumulado-001/senales.jsonl \
  --salida salidas/preparacion/acumulado-001 --corte 2026-09-20
```

Sustituir rutas y corte UTC exclusivo por los reales. La unión admite1–32 entradas,
10MB sumados y5000 URLs únicas; valida todo antes de reservar carpeta. Conserva copia
y hash de cada entrada, primera observación por URL y únicamente campos fuente en la
salida normalizada. No escribe en `datos/dorado`, no infiere independencia entre fuentes
ni borra originales. Un conflicto de IDs se detiene, no se silencia.

El detector léxico actual exige90 días distintos con señales únicas por fuente. **Un
feed semanal puede no satisfacer nunca esa guardia**, aunque se consulte diariamente.
No basta con dejarlo corriendo90 días. Antes de cambiar el criterio hace falta definir
con revisión de dominio una política de cobertura/base por frecuencia y calibrarla;
no se reduce la guardia para obtener resultados. Los manifiestos de ingesta conservan
las observaciones para ese trabajo futuro. Este recolector no implementa esa calibración.

## Evidencia real de esta ampliación

Una vuelta con CDC/ECDC/OMS produjo535 URLs:500 CDC,10 ECDC,25 OMS; cero errores. Se
omitieron1342 items CDC por el límite declarado, no por una supuesta ausencia de noticias.
Unida con129 HN:664 URLs,4 fuentes, **solo1 día observado**. Preparación:
`PREPARACION_COMPLETA`, `PENDIENTE_DORADO`, `publicable:false`. Hashes comprobados y
originales intactos. Operación previa a añadir la comprobación adicional de hash del
snapshot en el vigilante; esa guardia tiene pruebas de aceptación/rechazo y los hashes
reales se cotejaron por separado. No confundir la muestra con etiquetas completadas.

## Qué necesitas decidir o hacer tú

1. **Revisión de dominio.** Muestra nueva preparada en
   `salidas/preparacion/multifuente-20260919/revision/`:50 casos ciegos. Distribución
   observada33 CDC,15 HN,1 ECDC,1 OMS; no es estratificada ni garantiza representatividad.
   Revisar los casos y la pertinencia de la muestra; excluir ambigüedades requiere
   ampliar después para mantener al menos50 evaluables. No mirar predicciones al etiquetar.
   El paquete anterior HN se conserva intacto; no hay que llenar ambos por obligación.
2. **Modelos locales.** Autorizar instalación de Ollama/modelo y uso de disco/CPU fuera
   del proyecto, o proporcionar un servicio local ya disponible. El preflight encontró
   CLI ausente y11434 no disponible. No se instaló ni descargó nada por inferencia.
3. **Analista/refutador.** Definir proveedores/modelos distintos y techo de gasto/cuota,
   o decidir continuar sin modelos. El diseño histórico no concede acceso ni presupuesto.
   Sus clientes/ejecución real siguen pendientes de esas decisiones; no se fingieron
   con reglas ni mocks. Después de decidir, todavía habrá implementación/verificación.
4. **Cobertura/calibración.** Aprobar protocolo de evaluación, fuentes y definición de
   anomalía con un revisor competente antes de sustituir guardias o publicar resultados.
5. **Operación prolongada y publicación.** Decidir dónde mantener la ingesta y su
   duración; no se instaló cron ni se consumirá red indefinidamente. Publicar hallazgos,
   contactar organizaciones o usar datos con acceso restringido exige aprobación aparte.

Comprobación sin importar nada:

```bash
python3 -m bio.dorado comprobar salidas/preparacion/multifuente-20260919/revision
```

No se declara "todo el proyecto terminado": están cerradas capacidades de metadatos;
modelos, calibración y ciencia siguen sujetos a decisiones, datos y revisión humana.
