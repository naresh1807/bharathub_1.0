"""
messaging/tests.py

కవర్ చేసేవి:
  - Conversation: 1-1 (direct) get_or_create_between idempotency, group create
  - Message: soft_delete, delivery_state_for (direct వర్సెస్ group సెమాంటిక్స్)
  - permissions.can_message: candidate<->employer (JobApplication ఉంటేనే),
    employer<->vendor (Order ఉంటేనే), సంబంధం లేని వాళ్ళు బ్లాక్
  - views.unread_total_for
  - ChatConsumer: auth లేని వాళ్ళు connect కాలేరు, participant కాని వాళ్ళు
    connect కాలేరు

రన్ చేయడానికి: python manage.py test messaging
(WebSocket టెస్ట్‌లకి ఇంకా ఏమీ ఇన్‌స్టాల్ చేయాల్సిన అవసరం లేదు --
Channels తనంతట తానే in-memory test transport అందిస్తుంది.)
"""
import asyncio

from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.test import TestCase, TransactionTestCase

from accounts.models import EmployeeProfile, EmployerProfile
from candidates.models import CandidateProfile
from employers.models import Job
from jobs.models import JobApplication
from shopping.models import Order
from vendor.models import VendorProfile

from .consumers import ChatConsumer
from .models import Conversation, Message, PushSubscription, UserPresence
from .permissions import avatar_url_for, can_message, contacts_for
from .views import unread_total_for

User = get_user_model()


def _make_user(username, **kwargs):
    return User.objects.create_user(username=username, password="testpass123", **kwargs)


class ConversationModelTests(TestCase):
    def setUp(self):
        self.alice = _make_user("alice")
        self.bob = _make_user("bob")
        self.carol = _make_user("carol")

    def test_get_or_create_between_is_idempotent_and_order_independent(self):
        """A->B మరియు B->A రెండూ ఒకే conversation row కి మ్యాప్ అవ్వాలి."""
        c1 = Conversation.get_or_create_between(self.alice, self.bob)
        c2 = Conversation.get_or_create_between(self.bob, self.alice)
        self.assertEqual(c1.pk, c2.pk)
        self.assertEqual(Conversation.objects.filter(chat_type=Conversation.ChatType.DIRECT).count(), 1)
        self.assertTrue(c1.is_participant(self.alice))
        self.assertTrue(c1.is_participant(self.bob))
        self.assertFalse(c1.is_participant(self.carol))

    def test_create_group_makes_creator_admin_and_member(self):
        group = Conversation.create_group("Test Group", self.alice, [self.bob, self.carol])
        self.assertEqual(group.admin_id, self.alice.id)
        self.assertTrue(group.is_participant(self.alice))
        self.assertTrue(group.is_participant(self.bob))
        self.assertTrue(group.is_participant(self.carol))
        self.assertEqual(group.members.count(), 3)


class MessageModelTests(TestCase):
    def setUp(self):
        self.alice = _make_user("alice")
        self.bob = _make_user("bob")
        self.carol = _make_user("carol")
        self.direct = Conversation.get_or_create_between(self.alice, self.bob)
        self.group = Conversation.create_group("Group", self.alice, [self.bob, self.carol])

    def test_soft_delete_clears_body_and_sets_flag(self):
        message = Message.objects.create(conversation=self.direct, sender=self.alice, body="hello")
        message.soft_delete()
        message.refresh_from_db()
        self.assertTrue(message.is_deleted)
        self.assertEqual(message.body, "")

    def test_delivery_state_direct_chat(self):
        """1-1 చాట్‌లో ఒకే ఒక్క గ్రహీత -- అతను చదివితే వెంటనే 'read'."""
        message = Message.objects.create(conversation=self.direct, sender=self.alice, body="hi bob")
        self.assertEqual(message.delivery_state_for(self.alice), "sent")

        message.delivered_to.add(self.bob)
        self.assertEqual(message.delivery_state_for(self.alice), "delivered")

        message.read_by.add(self.bob)
        self.assertEqual(message.delivery_state_for(self.alice), "read")

    def test_delivery_state_group_chat_requires_all_members(self):
        """గ్రూప్‌లో సభ్యుల్లో ఒక్కరు చదివితే సరిపోదు -- అందరూ
        చదివితేనే 'read' (WhatsApp సెమాంటిక్స్) -- ఇది మేము ఫిక్స్
        చేసిన బగ్."""
        message = Message.objects.create(conversation=self.group, sender=self.alice, body="hi all")

        message.read_by.add(self.bob)  # ఒక్క bob మాత్రమే చదివాడు
        self.assertNotEqual(message.delivery_state_for(self.alice), "read")

        message.read_by.add(self.carol)  # ఇప్పుడు అందరూ చదివారు
        self.assertEqual(message.delivery_state_for(self.alice), "read")


class UnreadCountTests(TestCase):
    def setUp(self):
        self.alice = _make_user("alice")
        self.bob = _make_user("bob")
        self.direct = Conversation.get_or_create_between(self.alice, self.bob)

    def test_unread_total_excludes_own_messages_and_already_read(self):
        Message.objects.create(conversation=self.direct, sender=self.bob, body="unread 1")
        m2 = Message.objects.create(conversation=self.direct, sender=self.bob, body="unread 2 (will be read)")
        Message.objects.create(conversation=self.direct, sender=self.alice, body="alice's own message")

        self.assertEqual(unread_total_for(self.alice), 2)  # own మెసేజ్ లెక్కలోకి రాదు

        m2.read_by.add(self.alice)
        self.assertEqual(unread_total_for(self.alice), 1)

    def test_unread_total_for_anonymous_is_zero(self):
        from django.contrib.auth.models import AnonymousUser
        self.assertEqual(unread_total_for(AnonymousUser()), 0)


class PermissionsTests(TestCase):
    """can_message() -- ఇద్దరు యూజర్ల మధ్య ఒక వ్యాపార సంబంధం
    (job application / order) ఉంటేనే చాట్ చేయగలరు, లేకపోతే బ్లాక్."""

    def setUp(self):
        self.employee_user = _make_user("employee1")
        self.employer_user = _make_user("employer1")
        self.vendor_user = _make_user("vendor1")
        self.unrelated_employer_user = _make_user("employer2")

        self.employee_profile = EmployeeProfile.objects.create(
            user=self.employee_user, bharathub_id="BH20260001",
            mobile_number="9000000001", father_name="Father",
            date_of_birth="1998-05-15", gender=EmployeeProfile.Gender.MALE,
        )
        self.candidate_profile = CandidateProfile.objects.create(user=self.employee_user)
        self.employer_profile = EmployerProfile.objects.create(
            user=self.employer_user, company_name="Acme Corp",
            corporate_email="acme@example.com", pan_number="ABCDE1234F",
        )
        self.unrelated_employer_profile = EmployerProfile.objects.create(
            user=self.unrelated_employer_user, company_name="Other Corp",
            corporate_email="other@example.com", pan_number="PQRST5678G",
        )
        self.vendor_profile = VendorProfile.objects.create(
            user=self.vendor_user, shop_name="Vendor Shop",
            vendor_email="vendor@example.com", vendor_mobile="9000000004",
        )
        self.job = Job.objects.create(
            employer=self.employer_profile, title="Python Dev",
            status=Job.Status.ACTIVE,
        )

    def test_candidate_and_employer_blocked_without_application(self):
        self.assertFalse(can_message(self.employee_user, self.employer_user))

    def test_candidate_and_employer_allowed_after_application(self):
        JobApplication.objects.create(job=self.job, candidate=self.candidate_profile)
        self.assertTrue(can_message(self.employee_user, self.employer_user))
        self.assertTrue(can_message(self.employer_user, self.employee_user))  # రెండు దిశలా

    def test_candidate_blocked_from_unrelated_employer(self):
        JobApplication.objects.create(job=self.job, candidate=self.candidate_profile)
        self.assertFalse(can_message(self.employee_user, self.unrelated_employer_user))

    def test_employer_and_vendor_blocked_without_order(self):
        self.assertFalse(can_message(self.employer_user, self.vendor_user))

    def test_employer_and_vendor_allowed_after_order(self):
        Order.objects.create(vendor=self.vendor_profile, buyer=self.employer_profile)
        self.assertTrue(can_message(self.employer_user, self.vendor_user))

    def test_candidate_and_vendor_never_allowed(self):
        """స్పెక్ ప్రకారం candidate<->vendor మధ్య ఏ వ్యాపార సంబంధం
        లేదు కాబట్టి, ఎప్పటికీ చాట్ చేయలేరు."""
        self.assertFalse(can_message(self.employee_user, self.vendor_user))

    def test_contacts_for_only_returns_related_users(self):
        JobApplication.objects.create(job=self.job, candidate=self.candidate_profile)
        contacts = [c["user"] for c in contacts_for(self.employee_user)]
        self.assertIn(self.employer_user, contacts)
        self.assertNotIn(self.unrelated_employer_user, contacts)
        self.assertNotIn(self.vendor_user, contacts)

    def test_avatar_url_for_no_photo_returns_none(self):
        """ఫోటో అప్‌లోడ్ చేయని యూజర్ కి None వస్తుంది (JS/template
        అప్పుడు initials fallback వాడతాయి) -- Employer కి ఎప్పుడూ ఏ
        ఫోటో ఫీల్డ్ లేదు కాబట్టి ఎప్పటికీ None."""
        self.assertIsNone(avatar_url_for(self.employee_user))
        self.assertIsNone(avatar_url_for(self.employer_user))
        self.assertIsNone(avatar_url_for(self.vendor_user))

    def test_avatar_url_for_anonymous_is_none(self):
        from django.contrib.auth.models import AnonymousUser
        self.assertIsNone(avatar_url_for(AnonymousUser()))


class PresenceAndPushSubscriptionTests(TestCase):
    def setUp(self):
        self.alice = _make_user("alice")

    def test_user_presence_defaults_to_offline(self):
        presence = UserPresence.objects.create(user=self.alice)
        self.assertFalse(presence.is_online)

    def test_push_subscription_unique_per_endpoint(self):
        PushSubscription.objects.create(
            user=self.alice, endpoint="https://push.example.com/abc",
            p256dh="key1", auth="auth1",
        )
        # అదే endpoint తో రెండోసారి క్రియేట్ చేయడానికి ప్రయత్నిస్తే DB
        # unique constraint దీన్ని ఆపాలి (update_or_create వాడాలి,
        # views.SavePushSubscriptionView అలాగే చేస్తుంది).
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            PushSubscription.objects.create(
                user=self.alice, endpoint="https://push.example.com/abc",
                p256dh="key2", auth="auth2",
            )


class ChatConsumerAuthTests(TransactionTestCase):
    """WebSocket-level auth + participant గార్డులు -- ఇవి security కి
    అత్యంత కీలకమైన చెక్‌లు, కాబట్టి ప్రత్యేకంగా టెస్ట్ చేస్తున్నాం."""

    def setUp(self):
        self.alice = _make_user("alice")
        self.bob = _make_user("bob")
        self.stranger = _make_user("stranger")
        self.conversation = Conversation.get_or_create_between(self.alice, self.bob)

    def _connect(self, user):
        async def _run():
            communicator = WebsocketCommunicator(
                ChatConsumer.as_asgi(),
                f"/ws/messaging/conversation/{self.conversation.id}/",
            )
            communicator.scope["user"] = user
            communicator.scope["url_route"] = {"kwargs": {"conversation_id": str(self.conversation.id)}}
            connected, _ = await communicator.connect()
            await communicator.disconnect()
            return connected
        return asyncio.run(_run())

    def test_anonymous_user_cannot_connect(self):
        from django.contrib.auth.models import AnonymousUser
        self.assertFalse(self._connect(AnonymousUser()))

    def test_non_participant_cannot_connect(self):
        """conversation లో లేని యూజర్ (stranger) కనెక్ట్ కాలేకూడదు --
        ఇది IDOR-తరహా దాడిని ఆపే ముఖ్యమైన చెక్."""
        self.assertFalse(self._connect(self.stranger))

    def test_participant_can_connect(self):
        self.assertTrue(self._connect(self.alice))
