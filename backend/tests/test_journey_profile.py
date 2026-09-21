import copy
import unittest
from unittest.mock import AsyncMock, patch

from app.api.chat import ChatRequest
from app.db import candidate_profiles as store
from app.services import journey_profile as service
from app.services.report_builder import build
from app.services.cv_service import _merge_into_profile
from app.documents.extractor import Extraction
from app.api.profiles import public_router
from fastapi import FastAPI
from fastapi.testclient import TestClient


class ExtractionTests(unittest.TestCase):
    def test_explicit_statements(self):
        fields, prefs, evidence = service.extract_assertions("Tôi tên Nam, tôi đã có N4, tôi muốn đi Osaka")
        self.assertEqual(fields, {"full_name": "Nam", "japanese_level": "N4"})
        self.assertEqual(prefs["desired_prefecture"], "Osaka")
        self.assertEqual(evidence["japanese_level"], "tôi đã có N4")

    def test_questions_third_party_and_hypotheticals_are_not_facts(self):
        for text in ("Bạn tôi đã có N1", "Nếu tôi đã có N1", "Tôi đã có N1?", "Tôi muốn học N1", "Tôi không muốn đi Osaka", "Tôi tên Nam muốn học N4"):
            with self.subTest(text=text):
                fields, prefs, _ = service.extract_assertions(text)
                self.assertEqual(fields, {})
                self.assertEqual(prefs, {})

    def test_uuid_representation_preserved(self):
        for sid in ("a" * 32, "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"):
            self.assertEqual(ChatRequest(message="hi", session_id=sid).session_id, sid)

    def test_legacy_consultation_view(self):
        prefs = {"desired_prefecture": store.cell("Tokyo", "user_confirmed")}
        self.assertEqual(store.consultation_view({"preferences": prefs})["preferences"], prefs)


class IntakeTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.profile = {"code": "UV-1", "session_id": "a" * 32, "version": 1,
                        "status": "confirmed", "fields": {}, "preferences": {}}

    async def run_capture(self, text):
        with patch.object(store, "get_by_session", AsyncMock(return_value=self.profile)), patch.object(store, "apply_changes", AsyncMock(return_value={"code": "UV-1"})) as update:
            await service.capture(self.profile["session_id"], text, "chung")
        return update.call_args.kwargs

    async def test_confirmed_values_not_overwritten_and_conflict_retained(self):
        self.profile["fields"]["japanese_level"] = store.cell("N4", "user_confirmed")
        values = await self.run_capture("Tôi đã có N1")
        self.assertEqual(values["fields"]["japanese_level"]["value"], "N4")
        self.assertEqual(values["consultation"]["conflicts"][0]["suggested"], "N1")
        self.assertIsNone(values["status"])

    async def test_new_machine_fields_require_confirmation(self):
        values = await self.run_capture("Tôi đã có N4")
        self.assertEqual(values["fields"]["japanese_level"]["source"], "chat")
        self.assertEqual(values["status"], "extracted")
        self.assertEqual(values["expected_version"], 1)

    async def test_context_is_bounded(self):
        self.profile["consultation"] = {"recent_messages": [{"content": str(i)} for i in range(30)]}
        values = await self.run_capture("Chi phí thế nào?")
        self.assertEqual(len(values["consultation"]["recent_messages"]), 20)
        self.assertEqual(values["consultation"]["recent_messages"][-1]["content"], "Chi phí thế nào?")

    async def test_concurrent_change_reloads_before_retry(self):
        second = copy.deepcopy(self.profile)
        second["version"] = 2
        second["fields"]["japanese_level"] = store.cell("N3", "staff")
        with patch.object(store, "get_by_session", AsyncMock(side_effect=[self.profile, second])), patch.object(store, "apply_changes", AsyncMock(side_effect=[None, second])) as update:
            await service.capture(self.profile["session_id"], "Tôi đã có N4", "chung")
        self.assertEqual(update.call_args.kwargs["expected_version"], 2)
        self.assertEqual(update.call_args.kwargs["fields"]["japanese_level"]["value"], "N3")

    async def test_new_chat_creates_candidate_once(self):
        with patch.object(store, "get_by_session", AsyncMock(return_value=None)), patch.object(store, "create_profile", AsyncMock(return_value=self.profile)) as create, patch.object(store, "apply_changes", AsyncMock(return_value=self.profile)):
            await service.capture(self.profile["session_id"], "Tôi tên Nam", "chung")
        self.assertEqual(create.call_args.args[0]["session_id"], self.profile["session_id"])

    async def test_report_includes_unverified_context(self):
        self.profile["consultation"] = {"recent_messages": [{"content": "Tôi muốn đi Osaka"}]}
        report = build(profile=self.profile, order_item={}, explanation_block="", documents=[])
        self.assertIn("Tôi muốn đi Osaka", report["text"])
        self.assertIn("CHƯA PHẢI THÔNG TIN ĐÃ XÁC NHẬN", report["text"])
        self.assertEqual(report["consultation_profile"]["candidate_code"], "UV-1")


class JourneyIntegrationTests(unittest.IsolatedAsyncioTestCase):
    """Real service, profile store, CV merge and HTTP handlers; only Mongo I/O fake."""

    async def test_chat_cv_confirm_and_chat_again_share_one_profile(self):
        saved = {}
        collection = AsyncMock()

        async def find(query, *args, **kwargs):
            return copy.deepcopy(saved) if saved and all(saved.get(k) == v for k, v in query.items()) else None

        async def insert(document):
            saved.update(copy.deepcopy(document))

        async def update(query, operations, **kwargs):
            if await find(query) is None:
                return None
            saved.update(copy.deepcopy(operations.get("$set", {})))
            for key, operation in operations.get("$push", {}).items():
                saved[key] = (saved.get(key, []) + copy.deepcopy(operation["$each"]))[operation["$slice"]:]
            return copy.deepcopy(saved)

        collection.find_one.side_effect = find
        collection.insert_one.side_effect = insert
        collection.find_one_and_update.side_effect = update
        app = FastAPI()
        app.include_router(public_router)
        sid = "d" * 32
        with patch.object(store, "get_db", return_value={store.COLLECTION: collection}):
            await service.capture(sid, "Tôi tên Nam, tôi đã có N4, tôi muốn đi Osaka", "chung")
            original_code = saved["code"]
            await _merge_into_profile(sid, Extraction(fields={"birth_year": 2000}, evidence={"birth_year": "Sinh năm 2000"}))
            self.assertEqual(saved["code"], original_code)
            self.assertEqual(saved["fields"]["birth_year"]["source"], "cv")
            with TestClient(app) as client:
                response = client.get(f"/public/profiles/{sid}")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["consultation_profile"]["preferences"]["desired_prefecture"]["value"], "Osaka")
                response = client.post(f"/public/profiles/{sid}/confirm")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["fields"]["japanese_level"]["source"], "user_confirmed")
            await service.capture(sid, "Tôi đã có N1", "chung")
            self.assertEqual(saved["fields"]["japanese_level"]["value"], "N4")
            self.assertEqual(saved["consultation"]["conflicts"][-1]["suggested"], "N1")
            self.assertEqual(collection.insert_one.await_count, 1)

    async def test_enrichment_failure_does_not_drop_saved_chat(self):
        from app.services import chat_service
        with patch.object(chat_service, "save_message", AsyncMock()) as save, patch.object(chat_service, "capture_profile", AsyncMock(side_effect=RuntimeError("offline"))), self.assertLogs(chat_service.__name__, level="WARNING"):
            await chat_service._save_exchange("e" * 32, "Xin chào", "Chào bạn", "chung")
        self.assertEqual(save.await_count, 2)
