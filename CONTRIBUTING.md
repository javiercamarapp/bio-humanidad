# Contribuir

Código y documentación propia: MIT. Al contribuir, debes tener derecho a aportar
el material bajo esa licencia. No incluyas contenido de terceros incompatible.

## Flujo

1. Abre un issue con el problema, alcance y reproducción; sin información sensible.
2. Trabaja en una rama. Añade una prueba que detecte la regresión.
3. Ejecuta `python3 -m unittest discover -s tests -v` y la demo offline del README.
4. Envía un pull request indicando qué verificaste y qué no. CI no recibe datos reales.

Python 3.9+, biblioteca estándar, macOS/Linux. Mantén cambios pequeños y salidas
compatibles; nunca arregles un fallo borrando la prueba o inventando una aprobación.
Documenta nuevos campos y estados. Las interfaces deben distinguir preparación,
validación técnica, revisión humana y evidencia científica.

## Datos y seguridad

- No subas credenciales, revisores reales, datos clínicos, información personal ni
  conjuntos de terceros sin derechos de distribución.
- Los fixtures deben ser sintéticos y estar identificados. No los presentes como
  conjunto dorado científico.
- No aceptamos contribuciones de generación/síntesis de secuencias, mejora de
  patógenos ni optimización de peligrosidad o evasión. Es el alcance mantenido por
  este proyecto, no una cláusula adicional de la licencia MIT.
- Vulnerabilidades sensibles: usa el canal privado descrito en `SECURITY.md`, no
  un issue con detalles que puedan causar daño.
- No subas `datos/` o `salidas/` mediante `git add -f` para hacer pasar una demo.

## Verificar antes de publicar

Revisa `git diff --cached` y, si tienes Gitleaks, ejecuta:

```bash
gitleaks git --log-opts='--all' --redact .
```

El escáner no garantiza ausencia de secretos: también revisa manualmente los archivos.
