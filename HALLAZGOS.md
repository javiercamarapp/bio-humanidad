# Hallazgos — continuación operativa

## 2026-09-20 — integración local
- Instalación autorizada y USD0 en APIs. Ollama0.34.2, Qwen27B conservado; modelos
  Gemma4-12B y Qwen3.5-9B para perfil operativo de menor memoria.
- Prueba27B: primer registro completó3 roles; segundo agotó180s en analista. Lote
  ERROR sin manifiesto final. No se borró evidencia ni se amplió el plazo para verde.
- Perfil menor:2 señales reales fuera de ambos paquetes ciegos,6 solicitudes,
  92.85s, pipeline completo técnicamente/no publicable. Hashes cotejados.
- Muestreo del servidor: máximo1 modelo cargado,7.83GB de tamaño reportado. Esto no
  certifica memoria residente total ni calidad. La primera prueba sintética de
  Gemma se abstuvo: no convertir una respuesta válida en prueba de precisión.
- Presupuesto enmendado ANTES de segunda descarga por fallo observado: máximo2
  modelos nuevos y<15GB en total; tiempo60min/12 solicitudes/USD0 sin ampliar.
  Gastadas12 solicitudes reales (1 prueba,5 en fallo,6 en lote completo).
- RPC hijos limitados, sin proxy/redirect/cloud/pull. Alias no simulan independencia;
  schema/citas/identidad incompletos abortan. Defaults offline anteriores intactos.
- 223 pruebas por Python3.9/3.12. Las205 anteriores intactas por bytes; fixtures
  humanos solo en temporales rotulados y sin contaminar los paquetes reales.

## 2026-09-19
- Base main afa99ad: entrega previa183 pruebas, PR1 integrada. No volver a revisar ese
  mismo parche sin defecto nuevo; esta fase amplía capacidades de metadatos.
- Recolector actual soloHN (bio/recolector/recolector.py); preparación acepta campos
  genéricos y ya conserva hashes (bio/preparacion.py). Reutilizar esos contratos.
- Ollama: command -v sin resultado y GET loopback11434/api/tags devuelve URLError.
  No existe integración real de modelos disponible para certificar en este entorno.
- Documentos00–09 son históricos, pero08 aún ordena descargar modelos y crear dorado
  vacío;09 aún marca verificación científica. Deben remitir al estado operativo real.
- Fechas de publicación no prueban90 días de ingesta: mantener abstención existente.
- Preflight HTTP real: OMS noticias25 items (última publicación206 días antes),
  ECDC CDTR10 (última1 día), CDC Newsroom1842 (última9 días; se procesan500).
  CDC/mmwr antiguo devolvió2018 y CIDRAP/rss.xml,2022: endpoints no incorporados.
- Operación real:535 URLs RSS,0 errores, una preparación no publicable. Con HN previo:
  664 URLs,4 fuentes,1 día observado. Hashes de entradas/salidas comprobados.
- La muestra nueva es50 casos:33 CDC,15 HN,1 ECDC,1 OMS; no es representatividad
  garantizada. Paquete HN anterior intacto. Ninguna etiqueta humana se generó.
- ECDC semanal puede no cumplir nunca la guardia de90 días con señales únicas por
  fuente. Esperar90 días NO basta; hace falta protocolo de cobertura/calibración
  aprobado antes de cambiar esa guardia. No fabricar observaciones duplicando URLs.
- Descargas hijas necesitan cierre propio si el recolector muere: añadido watchdog
  de plazo/padre que termina solo su proceso. Pruebas reales sin red de timeout y
  muerte del padre; no modificar el manejador legacy que mata solo su hijo.
- 205 pruebas OK localmente por versión;12 archivos de pruebas previas idénticos
  a afa99ad. Fixtures y mocks no se presentan como integraciones de modelos reales.
- urllib puede leer sin límite el cuerpo de una redirección antes de seguirla:
  se rechazan también las redirecciones del mismo host. Los endpoints reales probados
  son directos. Regresión comprueba que no se lee ese cuerpo; no se elude bloqueo web.
- Primera revisión: deduplicar cada snapshot ocultaba conflictos conjuntos; ahora se
  conservan todas las filas para validar antes de deduplicar. También se compara el
  instante completo de publicación con observación antes de truncar a fecha. Cuatro
  fallos sintéticos reproducidos en rojo, dos pruebas nuevas; suite205 OK por versión.
