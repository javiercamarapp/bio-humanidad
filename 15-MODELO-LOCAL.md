# 15 — Modelo local instalado: evidencia y límites

Actualización: 2026-09-20 UTC. Instalación autorizada por el operador; presupuesto
para APIs de pago: USD 0. No se cambió código del radar, etiquetas ni criterios humanos.

## Selección informada, no un «mejor modelo» demostrado

Se contrastaron las fichas oficiales de Qwen3.5-27B, Qwen3.6-27B, Qwen3.5-35B,
Qwen3-32B y Gemma4-26B/31B. Para priorizar calidad y programación se eligió probar
**Qwen3.6-27B, GGUF Q4_K_M**, no una variante modificada para eliminar salvaguardas.

La ficha de Qwen3.6 publica 77.2 en SWE-bench Verified frente a 75.0 de Qwen3.5-27B,
y 87.8 frente a 85.5 en GPQA Diamond. Son resultados del proveedor y de su entorno,
no evaluaciones independientes ni mediciones de esta cuantización en este Mac.
Su evaluación usa contextos muy superiores al ensayo local de 4.096 tokens. No se
extrapolan resultados a Bio Humanidad ni se confunde ausencia de negativas con calidad.

Fuentes consultadas:
- [Requisitos macOS de Ollama](https://docs.ollama.com/macos)
- [Qwen3.6-27B en Ollama](https://ollama.com/library/qwen3.6:27b)
- [Ficha y metodología Qwen3.6-27B](https://huggingface.co/Qwen/Qwen3.6-27B)
- [Gemma4-26B](https://ollama.com/library/gemma4:26b)
- [Gemma4-31B](https://ollama.com/library/gemma4:31b)
- [Modo exclusivamente local de Ollama](https://docs.ollama.com/faq#how-do-i-disable-ollamas-cloud-features)

## Instalación observada

- Equipo de prueba: Apple M3, 24 GiB de memoria unificada; unos 91 GiB de disco libre
  antes de descargar. Es una observación local, no un mínimo certificado.
- Ollama 0.34.2 mediante Homebrew, con su dependencia mlx-c; sin actualización general
  de paquetes ni `brew services`, launch agents o arranque automático.
- Modelo `qwen3.6:27b`, tamaño instalado reportado: **17.769.076.933 bytes**.
- Digest observado: `9d5803d493a991af27b9441c098aa56f2ed7bbd260877f075ec09b575c049bc3`.
  El tag puede cambiar; registrar el digest en futuras comparaciones.
- Pesos almacenados localmente en `~/.ollama/models`, NO dentro de Git.
- Servidor temporal escuchando solo en `127.0.0.1:11434`, con `OLLAMA_NO_CLOUD=1`,
  un modelo cargado, una petición simultánea, contexto 4096 y caché KV q8_0.

## Prueba real: pasa el arranque, pero es pesada

Se envió una petición real a `/api/chat`, `stream:false`, `think:false`, temperatura0,
salida máxima96 tokens y esquema JSON de dos campos. Respondió exactamente:

```json
{"estado":"listo","idioma":"español"}
```

Resultado observado: `done:true`, `done_reason:stop`, 23 tokens generados,
**4.01 tokens/s** y **27.75 s de tiempo total**, incluyendo carga. Una respuesta corta
no caracteriza todo el rendimiento ni prueba estabilidad prolongada.

Ollama reportó un modelo cargado de 17.94 GB y 15.10 GB en GPU. El swap usado reportado
por macOS pasó de `2070.06M` antes de cargar a `8024.00M` después de la prueba; la
medición no aísla otros procesos. La memoria libre reportada pasó de 86% a 12% entre
los preflights y el ensayo. **No es una configuración cómoda para uso continuo con
otras aplicaciones, ni se certifica como mejor opción operativa.**

Se descargó el modelo de RAM con `keep_alive:0`, se verificó `/api/ps` vacío y se
cerró el servidor temporal. Los pesos siguen instalados. No se modificaron límites
de memoria del kernel, ajustes de energía, firewall ni permisos para forzar la carga.
El recolector de metadatos es un proceso distinto y no llama al modelo.

## Repetir una prueba bajo demanda

Primero comprueba que el puerto no pertenezca a un servidor ajeno. En una terminal:

```bash
OLLAMA_HOST=127.0.0.1:11434 OLLAMA_NO_CLOUD=1 \
OLLAMA_CONTEXT_LENGTH=4096 OLLAMA_NUM_PARALLEL=1 OLLAMA_MAX_LOADED_MODELS=1 \
OLLAMA_FLASH_ATTENTION=1 OLLAMA_KV_CACHE_TYPE=q8_0 OLLAMA_KEEP_ALIVE=0 \
ollama serve
```

Es un servidor en primer plano: permanece activo hasta detenerlo. No instala un servicio
persistente. Las variables se aplican a ese proceso, no a futuros servidores arbitrarios.
En otra terminal:

```bash
curl --noproxy '*' --fail-with-body --max-time 180 \
  http://127.0.0.1:11434/api/chat -H 'Content-Type: application/json' -d '{
    "model":"qwen3.6:27b", "stream":false, "think":false, "keep_alive":0,
    "options":{"num_ctx":4096,"num_predict":96,"temperature":0},
    "format":{"type":"object","properties":{"estado":{"type":"string"},
      "idioma":{"type":"string"}},"required":["estado","idioma"],
      "additionalProperties":false},
    "messages":[{"role":"user","content":"Prueba técnica local. Devuelve exactamente un objeto JSON con estado igual a listo e idioma igual a español."}]
  }'
```

Detén tu servidor con Ctrl+C al terminar. Ante presión de memoria o lentitud, detén
la prueba; no mates procesos ajenos ni cambies límites del sistema. Un contexto grande
consume más recursos: el máximo declarado por el modelo no es capacidad verificada aquí.

## Pendientes reales

1. Comparativa acotada con una alternativa menor o cuantización más compacta antes de
   fijar el modelo por defecto. No se han descargado varios modelos para aparentar progreso.
2. Cliente del extractor, contratos de salida, controles de error e integración con
   evaluación: **todavía no implementados por esta instalación**.
3. Etiquetas humanas reales y evaluación de calidad. No se ha elegido un revisor a partir
   de una plantilla de respuesta que conservaba todas sus opciones.
4. Analista/refutador, calibración y publicación: siguen siendo decisiones/capacidades
   separadas, sin acceso automático a proveedores pagados ni aprobación científica.

Evidencia local ignorada por Git: `salidas/verificacion/ollama-local-20260920/`.
Incluye instalación, fuentes consultadas, petición/respuesta, digest y memoria reportada.
No publicar logs completos, claves de Ollama, pesos ni CSV humanos.
