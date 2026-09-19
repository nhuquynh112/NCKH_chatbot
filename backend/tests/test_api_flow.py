import unittest
from unittest.mock import patch
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.database import SessionLocal
from app.main import app
from app.models import ChatMessage, Ticket
from app.schemas.ticket import TicketCreate, TicketUpdate


class CustomerSupportApiFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_issue_then_phone_updates_one_ticket(self):
        visitor_id = f"test-{uuid4()}"
        headers = {"X-Visitor-ID": visitor_id}
        created = self.client.post(
            "/api/chat/sessions",
            json={
                "visitor_id": visitor_id,
                "customer_name": "Khách kiểm thử",
            },
            headers=headers,
        )
        self.assertEqual(created.status_code, 201)
        session = created.json()["data"]
        self.assertEqual(session["title"], "New Chat")

        issue = self.client.post(
            "/api/chat/messages",
            json={
                "session_id": session["id"],
                "content": "Điện thoại của mình sạc không vào",
            },
            headers=headers,
        )
        self.assertEqual(issue.status_code, 201)
        self.assertTrue(issue.json()["data"]["ticket_created"])

        contact = self.client.post(
            "/api/chat/messages",
            json={"session_id": session["id"], "content": "ok sdt 0921154829"},
            headers=headers,
        )
        self.assertEqual(contact.status_code, 201)
        payload = contact.json()["data"]
        self.assertIn("0921***829", payload["message"]["content"])
        self.assertNotIn("có bán nhóm điện thoại", payload["message"]["content"].lower())

        with SessionLocal() as db:
            tickets = (
                db.query(Ticket)
                .filter(Ticket.session_id == UUID(session["id"]))
                .all()
            )
            self.assertEqual(len(tickets), 1)
            self.assertEqual(tickets[0].customer_phone, "0921154829")
            stored_phone_message = (
                db.query(ChatMessage)
                .filter(
                    ChatMessage.session_id == UUID(session["id"]),
                    ChatMessage.role == "user",
                    ChatMessage.content.like("%sdt%"),
                )
                .one()
            )
            self.assertIn("0921***829", stored_phone_message.content)
            self.assertNotIn("0921154829", stored_phone_message.content)

    def test_sensitive_credentials_are_redacted_and_do_not_create_ticket(self):
        visitor_id = f"privacy-{uuid4()}"
        headers = {"X-Visitor-ID": visitor_id}
        created = self.client.post(
            "/api/chat/sessions",
            json={"visitor_id": visitor_id},
            headers=headers,
        )
        self.assertEqual(created.status_code, 201)
        session_id = created.json()["data"]["id"]

        result = self.client.post(
            "/api/chat/messages",
            json={
                "session_id": session_id,
                "content": "mã OTP của tôi là 628194, kiểm tra giúp",
            },
            headers=headers,
        )
        self.assertEqual(result.status_code, 201)
        payload = result.json()["data"]
        self.assertFalse(payload["ticket_created"])
        self.assertIn("đã ẩn mã OTP", payload["message"]["content"])

        with SessionLocal() as db:
            user_message = (
                db.query(ChatMessage)
                .filter(
                    ChatMessage.session_id == UUID(session_id),
                    ChatMessage.role == "user",
                )
                .one()
            )
            self.assertNotIn("628194", user_message.content)
            self.assertIn("ĐÃ ẨN", user_message.content)

    def test_invalid_email_is_rejected(self):
        visitor_id = f"invalid-email-{uuid4()}"
        result = self.client.post(
            "/api/chat/sessions",
            json={"visitor_id": visitor_id, "customer_email": "sai-email"},
            headers={"X-Visitor-ID": visitor_id},
        )
        self.assertEqual(result.status_code, 422)

    def test_invisible_or_oversized_messages_are_rejected(self):
        visitor_id = f"input-validation-{uuid4()}"
        headers = {"X-Visitor-ID": visitor_id}
        created = self.client.post(
            "/api/chat/sessions",
            json={"visitor_id": visitor_id},
            headers=headers,
        )
        session_id = created.json()["data"]["id"]
        for content in ["\u200b\u200c", "x" * 2001]:
            with self.subTest(length=len(content)):
                result = self.client.post(
                    "/api/chat/messages",
                    json={"session_id": session_id, "content": content},
                    headers=headers,
                )
                self.assertEqual(result.status_code, 422)

    def test_other_visitor_cannot_read_modify_or_delete_session(self):
        owner = f"owner-{uuid4()}"
        created = self.client.post(
            "/api/chat/sessions",
            json={"visitor_id": owner},
            headers={"X-Visitor-ID": owner},
        )
        session_id = created.json()["data"]["id"]
        attacker_headers = {"X-Visitor-ID": f"other-{uuid4()}"}
        attempts = [
            self.client.get(
                f"/api/chat/sessions/{session_id}/messages",
                headers=attacker_headers,
            ),
            self.client.patch(
                f"/api/chat/sessions/{session_id}",
                json={"title": "Không được phép"},
                headers=attacker_headers,
            ),
            self.client.delete(
                f"/api/chat/sessions/{session_id}",
                headers=attacker_headers,
            ),
        ]
        self.assertTrue(all(response.status_code == 404 for response in attempts))
        owner_read = self.client.get(
            f"/api/chat/sessions/{session_id}/messages",
            headers={"X-Visitor-ID": owner},
        )
        self.assertEqual(owner_read.status_code, 200)

    def test_public_cannot_create_ticket_directly(self):
        result = self.client.post(
            "/api/tickets",
            json={
                "session_id": str(uuid4()),
                "subject": "Spam",
                "issue": "Không được tạo trực tiếp",
            },
        )
        self.assertIn(result.status_code, {401, 403})

    def test_ticket_schema_rejects_unknown_status_and_blank_issue(self):
        with self.assertRaises(ValidationError):
            TicketUpdate(status="waiting_forever")
        with self.assertRaises(ValidationError):
            TicketCreate(
                session_id=uuid4(),
                subject="Yêu cầu hỗ trợ",
                issue="   ",
            )

    def test_readiness_reports_database_and_ai_components(self):
        with patch("app.main.OllamaClient.is_available", return_value=True):
            result = self.client.get("/ready")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["status"], "ready")
        self.assertEqual(result.json()["database"], "ok")


if __name__ == "__main__":
    unittest.main()
