"""Pruebas sintéticas de software, NO un conjunto dorado científico."""
import csv
import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch


def senal(i, dia="2026-09-19", titulo="Public health surveillance report", fuente="HN"):
    return {"id": str(i), "fuente": fuente, "fecha": dia,
            "claim_literal": titulo, "url": f"https://example.org/article/{i}",
            "recolectado_en": f"{dia}T12:00:00Z", "verificado": False}


class CollectorTests(unittest.TestCase):
    def test_repetir_corrida_no_duplica(self):
        from bio.recolector.recolector import main
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "senales.jsonl"
            with patch("bio.recolector.recolector.recolecta", return_value=([senal(1)], [])), \
                 patch("sys.argv", ["recolector", "--salida", str(p)]):
                self.assertEqual(main(), 0)
                self.assertEqual(main(), 0)
            self.assertEqual(len(p.read_text().splitlines()), 1)

    def test_fallo_parcial_no_es_exito(self):
        from bio.recolector.recolector import main
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "senales.jsonl"
            with patch("bio.recolector.recolector.recolecta", return_value=([senal(1)], ["fallo"])), \
                 patch("sys.argv", ["recolector", "--salida", str(p)]):
                self.assertEqual(main(), 2)
            self.assertEqual(len(p.read_text().splitlines()), 1)

    def test_no_escribe_si_archivo_previo_esta_corrupto(self):
        from bio.recolector.recolector import guardar
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "senales.jsonl"
            p.write_text('{mal JSON}\n')
            antes = p.read_bytes()
            with self.assertRaises(ValueError):
                guardar(p, [senal(1)])
            self.assertEqual(p.read_bytes(), antes)

    def test_archivo_sin_salto_final(self):
        from bio.recolector.recolector import guardar
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "senales.jsonl"
            p.write_text(json.dumps(senal(1)))
            self.assertEqual(guardar(p, [senal(2), senal(2)]), 1)
            self.assertEqual(len([json.loads(x) for x in p.read_text().splitlines()]), 2)

    def test_recoleccion_informa_consultas_fallidas(self):
        from bio.recolector.recolector import recolecta
        with patch("bio.recolector.recolector.TERMINOS", ["a", "b"]), \
             patch("bio.recolector.recolector.hn", side_effect=[[senal(1)], OSError("timeout")]):
            datos, errores = recolecta()
        self.assertEqual(len(datos), 1)
        self.assertEqual(len(errores), 1)


class RadarTests(unittest.TestCase):
    def test_json_invalido_indica_linea(self):
        from bio.radar import leer
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "s.jsonl"
            p.write_text(json.dumps(senal(1)) + '\nno json\n')
            with self.assertRaisesRegex(ValueError, "línea 2"):
                leer(p)

    def test_rechaza_fechas_invalidas_naive_y_urls_no_web(self):
        from bio.radar import normalizar
        for campo, valor in [("fecha", "2026-02-30"), ("recolectado_en", "2026-09-19T12:00:00"),
                             ("url", "file:///etc/passwd"), ("id", ""), ("fuente", ""),
                             ("claim_literal", ""), ("fecha", "2027-01-01")]:
            with self.subTest(campo=campo, valor=valor):
                with self.assertRaises(ValueError):
                    normalizar([{**senal(1), campo: valor}])

    def test_dedup_url_conserva_primera_observacion(self):
        from bio.radar import normalizar
        vieja = senal(1, "2026-01-01")
        nueva = {**senal(2), "url": vieja["url"] + "#section"}
        resultado = normalizar([nueva, vieja])
        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0]["id"], "1")

    def test_id_reutilizado_para_otra_url_falla(self):
        from bio.radar import normalizar
        with self.assertRaisesRegex(ValueError, "id.*conflictivo"):
            normalizar([senal(1), {**senal(2), "id": "1"}])

    def test_misma_observacion_con_titulares_contradictorios_se_rechaza(self):
        from bio.radar import normalizar
        first = senal(1, titulo='Outbreak bulletin')
        second = {**first, 'claim_literal': 'Surveillance bulletin'}
        for rows in ([first, second], [second, first]):
            with self.assertRaisesRegex(ValueError, 'contradictori'):
                normalizar(rows)

    def test_json_claves_repetidas_y_numeros_no_finitos_se_rechaza(self):
        from bio.radar import parsear_jsonl
        raw = json.dumps(senal(1))
        invalid = [raw[:-1] + ', "claim_literal": "otro titular"}',
                   raw[:-1] + ', "extra": NaN}', raw[:-1] + ', "extra": 1e999}']
        for text in invalid:
            with self.subTest(text=text), self.assertRaises(ValueError):
                parsear_jsonl(text)

    def test_muestra_reproducible_no_etiquetada_y_no_sobrescribe(self):
        from bio.radar import preparar
        datos = [senal(i) for i in range(60)]
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "a", Path(tmp) / "b"
            preparar(datos, a)
            preparar(list(reversed(datos)), b)
            self.assertEqual((a / "revision.csv").read_bytes(), (b / "revision.csv").read_bytes())
            with (a / "revision.csv").open() as f:
                filas = list(csv.DictReader(f))
            self.assertEqual(len(filas), 50)
            self.assertTrue(all(not x["categoria_humana"] and not x["revisor"] for x in filas))
            manifest = json.loads((a / "estado.json").read_text())
            self.assertEqual(manifest["etiquetas_humanas"], 0)
            self.assertEqual(manifest["estado"], "PENDIENTE_REVISION_HUMANA")
            with self.assertRaises(FileExistsError):
                preparar(datos, a)

    def test_no_copia_aprobaciones_inyectadas_en_las_senales(self):
        from bio.radar import preparar
        datos = [{**senal(1), "categoria_humana": "brote", "revisor": "falso", "revisado_en": "hoy", "clase": "tipico", "nota": "aprobado"}]
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "a"
            preparar(datos, p, cantidad=1)
            with (p / "revision.csv").open() as f:
                fila = next(csv.DictReader(f))
            snapshot = json.loads((p / "muestra.jsonl").read_text().strip())
            for campo in ("categoria_humana", "revisor", "revisado_en", "clase", "nota"):
                self.assertEqual(fila[campo], "")
                self.assertNotIn(campo, snapshot)

    def test_csv_no_ejecuta_formula(self):
        from bio.radar import preparar
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "a"
            preparar([senal(1, titulo='  =HYPERLINK("https://example.org")')], p, cantidad=1)
            with (p / "revision.csv").open() as f:
                fila = next(csv.DictReader(f))
            self.assertTrue(fila["claim_literal"].startswith("'"))

    def test_muestra_insuficiente_no_crea_entrega(self):
        from bio.radar import preparar
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "a"
            with self.assertRaises(ValueError):
                preparar([senal(1)], p)
            self.assertFalse(p.exists())

    def test_titulares_antiguos_no_fabrican_90_dias_de_cobertura(self):
        from bio.radar import detectar
        datos = [{**senal(i), "fecha": (date(2025, 1, 1) + timedelta(days=i)).isoformat()} for i in range(100)]
        r = detectar(datos, date(2026, 9, 20))
        self.assertEqual(r["estado"], "DATOS_INSUFICIENTES")
        self.assertEqual(r["novedades"], [])
        self.assertEqual(r["fuentes"]["HN"]["dias_observados_base"], 0)
        self.assertFalse(r["publicable"])

    def historia(self):
        corte = date(2026, 9, 20)
        inicio = corte - timedelta(days=97)
        return [senal(i, (inicio + timedelta(days=i)).isoformat(), "Weekly public health report") for i in range(90)]

    def test_compara_novedad_sin_confundirla_con_riesgo(self):
        from bio.radar import detectar
        datos = self.historia() + [senal(100, titulo="Weekly public health report"),
                                 senal(101, titulo="Municipal monitoring dashboard launched")]
        r = detectar(datos, date(2026, 9, 20))
        self.assertEqual(r["estado"], "EXPLORATORIO_NO_CALIBRADO")
        self.assertEqual([x["id"] for x in r["novedades"]], ["101"])
        self.assertFalse(r["publicable"])
        self.assertNotIn("riesgo", r["novedades"][0])
        self.assertEqual(r, detectar(list(reversed(datos)), date(2026, 9, 20)))

    def test_fuente_nueva_no_hereda_cobertura(self):
        from bio.radar import detectar
        r = detectar(self.historia() + [senal(100, fuente="otra")], date(2026, 9, 20))
        self.assertEqual(r["estado"], "DATOS_INSUFICIENTES")
        self.assertEqual(r["novedades"], [])

    def test_fuera_de_ventana_y_futuro_no_se_usan(self):
        from bio.radar import detectar
        datos = self.historia() + [senal(200, "2026-09-20"), senal(201, "2020-01-01")]
        r = detectar(datos, date(2026, 9, 20))
        self.assertEqual(r["candidatas"], 0)
        self.assertEqual(r["excluidas_fuera_ventana"], 2)
        self.assertEqual(r["estado"], "SIN_CANDIDATAS")

    def test_un_dia_faltante_obliga_abstencion(self):
        from bio.radar import detectar
        r = detectar(self.historia()[1:] + [senal(100)], date(2026, 9, 20))
        self.assertEqual(r["estado"], "DATOS_INSUFICIENTES")

    def test_sin_historia_ni_candidatas(self):
        from bio.radar import detectar
        r = detectar([], date(2026, 9, 20))
        self.assertEqual(r["estado"], "SIN_CANDIDATAS")
        self.assertFalse(r["publicable"])

    def test_umbral_invalido_falla(self):
        from bio.radar import detectar
        for x in [-1, 2, float("nan")]:
            with self.assertRaises(ValueError):
                detectar([], date(2026, 9, 20), umbral=x)


if __name__ == "__main__":
    unittest.main()
