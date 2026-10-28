import gc
import os
import tempfile
import unittest

import app as stock_app


class StockNotesTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.original_database_file = stock_app.STOCK_DATABASE_FILE
        self.original_database_ready = stock_app.stock_database_ready
        stock_app.STOCK_DATABASE_FILE = os.path.join(
            self.temporary_directory.name,
            "stocks.db",
        )
        stock_app.stock_database_ready = False

    def tearDown(self):
        stock_app.STOCK_DATABASE_FILE = self.original_database_file
        stock_app.stock_database_ready = self.original_database_ready
        gc.collect()
        self.temporary_directory.cleanup()

    def test_stock_note_api_create_filter_update_and_delete(self):
        with stock_app.app.test_client() as client:
            created = client.post(
                "/stock-notes",
                json={
                    "symbol": "فولاد",
                    "text": "پیگیری گزارش ماهانه",
                    "importance": 4,
                },
            )
            self.assertEqual(created.status_code, 201)
            note = created.get_json()["note"]
            self.assertEqual(note["symbol"], "فولاد")
            self.assertEqual(note["importance"], 4)

            client.post(
                "/stock-notes",
                json={
                    "symbol": "خودرو",
                    "text": "بررسی حجم معاملات",
                    "importance": 2,
                },
            )

            filtered = client.get("/stock-notes?symbol=فولاد")
            self.assertEqual(filtered.status_code, 200)
            self.assertEqual(filtered.get_json()["count"], 1)
            self.assertEqual(filtered.get_json()["notes"][0]["symbol"], "فولاد")

            updated = client.put(
                f"/stock-notes/{note['id']}",
                json={
                    "text": "گزارش ماهانه بررسی شد",
                    "importance": 5,
                },
            )
            self.assertEqual(updated.status_code, 200)
            self.assertEqual(updated.get_json()["note"]["importance"], 5)
            self.assertEqual(
                updated.get_json()["note"]["text"],
                "گزارش ماهانه بررسی شد",
            )

            all_notes = client.get("/stock-notes")
            self.assertEqual(all_notes.get_json()["count"], 2)
            self.assertEqual(all_notes.get_json()["symbol_count"], 2)

            deleted = client.delete(f"/stock-notes/{note['id']}")
            self.assertEqual(deleted.status_code, 200)
            self.assertTrue(deleted.get_json()["deleted"])
            self.assertEqual(client.get("/stock-notes?symbol=فولاد").get_json()["count"], 0)

            missing = client.delete(f"/stock-notes/{note['id']}")
            self.assertEqual(missing.status_code, 404)

    def test_stock_note_validation(self):
        with stock_app.app.test_client() as client:
            empty_text = client.post(
                "/stock-notes",
                json={"symbol": "فولاد", "text": "  ", "importance": 3},
            )
            self.assertEqual(empty_text.status_code, 400)

            invalid_importance = client.post(
                "/stock-notes",
                json={"symbol": "فولاد", "text": "یادداشت", "importance": 6},
            )
            self.assertEqual(invalid_importance.status_code, 400)


if __name__ == "__main__":
    unittest.main()
