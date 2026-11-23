"""Meaningful offline boundaries: snapshot overlap, identity and time provenance."""

import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from classify_preinscritos import bucket, classify, mobile, safe_csv


def record(
    name="Persona de prueba", phone="3001234567", email="test@example.org", **values
):
    raw = {
        "Aspirante": name,
        "Celular": phone,
        "Telefono": "0",
        "Mail": email,
        "Programa de Interes": "Programa A",
        "Fecha": "2026-10-01T10:00:00",
        "Estado": "",
        "Ultimo asesor": "",
    }
    raw.update(values)
    return {"source": "test.xls", "sheet": "Sheet1", "row": 2, "raw": raw}


class ClassificationTests(unittest.TestCase):
    def classify(self, rows):
        return classify(rows, date(2026, 11, 23))

    def test_overlap_preserves_evidence_and_nonblank_state(self):
        result = self.classify(
            [
                record(),
                record(
                    Estado="En Negociación", **{"Ultimo asesor": "ASESOR 2026-10-24"}
                ),
            ]
        )
        self.assertEqual(len(result["contacts"]), 1)
        self.assertEqual(len(result["applications"]), 1)
        self.assertEqual(len(result["evidence"]), 2)
        self.assertEqual(result["applications"][0]["stage"], "En negociación")
        self.assertEqual(result["applications"][0]["management_bucket"], "30–59 días")

    def test_shared_phone_does_not_merge_different_people(self):
        result = self.classify(
            [record(), record(name="Otra persona", email="other@example.org")]
        )
        self.assertEqual(len(result["contacts"]), 2)
        self.assertEqual(result["summary"]["shared_coordinates"], 1)
        self.assertTrue(all("compartido" in c["review"] for c in result["contacts"]))

    def test_same_name_without_shared_coordinates_is_reviewed(self):
        result = self.classify(
            [record(), record(phone="3117654321", email="other@example.org")]
        )
        self.assertEqual(len(result["contacts"]), 2)
        self.assertTrue(all("Mismo nombre" in c["review"] for c in result["contacts"]))

    def test_missing_management_never_uses_registration_as_contact(self):
        app = self.classify([record()])["applications"][0]
        self.assertEqual(app["registration_days"], 53)
        self.assertIsNone(app["management_days"])
        self.assertIsNone(app["last_contact_verified"])
        self.assertEqual(app["management_bucket"], "Sin gestión registrada")
        self.assertFalse(app["send_eligible"])

    def test_separate_programs_and_dates_survive(self):
        result = self.classify(
            [
                record(),
                record(**{"Programa de Interes": "Programa B"}),
                record(Fecha="2026-11-01T10:00:00"),
            ]
        )
        self.assertEqual(len(result["contacts"]), 1)
        self.assertEqual(len(result["applications"]), 3)

    def test_conflicting_states_are_not_silently_chosen(self):
        app = self.classify(
            [record(Estado="Inscrito"), record(Estado="En Negociación")]
        )["applications"][0]
        self.assertEqual(app["stage"], "Etapas contradictorias: revisar")
        self.assertEqual(app["segment"], "revision_datos")

    def test_future_or_pre_registration_management_is_rejected(self):
        for stamp in ["2026-11-24", "2026-09-30"]:
            app = self.classify([record(**{"Ultimo asesor": "ASESOR " + stamp})])[
                "applications"
            ][0]
            self.assertEqual(app["last_management"], "")
            self.assertIn("Fecha de gestión", app["review"])

    def test_declined_and_enrolled_are_not_acquisition(self):
        for state, segment in [
            ("Inscrito", "sin_captacion"),
            ("Negociación No Aceptada", "pausado_no_aceptada"),
        ]:
            app = self.classify([record(Estado=state)])["applications"][0]
            self.assertEqual(app["segment"], segment)

    def test_age_boundaries(self):
        self.assertEqual(
            [bucket(n) for n in [7, 8, 14, 15, 29, 30, 59, 60, 89, 90]],
            [
                "0–7 días",
                "8–14 días",
                "8–14 días",
                "15–29 días",
                "15–29 días",
                "30–59 días",
                "30–59 días",
                "60–89 días",
                "60–89 días",
                "90+ días",
            ],
        )
        self.assertEqual(bucket(-1), "Fecha futura: revisar")

    def test_phone_and_formula_safety(self):
        self.assertEqual(mobile("+57 (300) 123-4567"), "+573001234567")
        self.assertEqual(mobile("0"), "")
        self.assertEqual(mobile("3000000000"), "")
        self.assertEqual(mobile("3001234567 ext 9"), "")
        self.assertEqual(safe_csv('=HYPERLINK("https://example.org")')[0], "'")
        self.assertEqual(safe_csv(" +573001234567")[0], "'")

    def test_phone_entered_as_name_is_held_for_review(self):
        contact = self.classify([record(name="3001234567")])["contacts"][0]
        self.assertIn("Nombre no utilizable", contact["review"])

    def test_unmatched_homonyms_without_coordinates_have_distinct_references(self):
        first = record(phone="0", email="")
        second = record(phone="0", email="", Fecha="2026-11-01T10:00:00")
        second["row"] = 3
        contacts = self.classify([first, second])["contacts"]
        self.assertEqual(len(contacts), 2)
        self.assertNotEqual(contacts[0]["contact_ref"], contacts[1]["contact_ref"])


if __name__ == "__main__":
    unittest.main()
