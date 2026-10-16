import asyncio
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.db.models.water_body import WaterBody
from app.db.models.satellite_observation import SatelliteObservation
from app.services.satellite.image_resolver import (
    ObservationImageResolver,
    SUPPORTED_IMAGE_EXTENSIONS,
)
from app.services.telegram.intent_service import (
    TelegramIntentService,
    TelegramIntent,
)
from app.services.telegram.models import (
    TelegramMessage,
    TelegramChat,
    TelegramUser,
    TelegramCallbackQuery,
)
from app.services.telegram.client import TelegramClient
from app.services.telegram.handlers import TelegramCommandHandler


@pytest.fixture
def mock_telegram_client():
    client = MagicMock(spec=TelegramClient)
    client.is_configured = True
    client.send_message = AsyncMock(return_value=True)
    client.send_photo = AsyncMock(return_value=True)
    client.answer_callback_query = AsyncMock(return_value=True)
    client.get_me = AsyncMock(return_value={"id": 12345, "is_bot": True, "username": "jalNetra_Helperbot"})
    client.get_updates = AsyncMock(return_value=[])
    client.close = AsyncMock()
    return client


def make_msg(chat_id: int, text: str) -> TelegramMessage:
    return TelegramMessage(
        message_id=1,
        chat=TelegramChat(id=chat_id, type="private"),
        date=1729000000,
        text=text,
        from_user=TelegramUser(id=chat_id, is_bot=False, first_name="TestUser"),
    )


def make_callback(chat_id: int, data: str) -> TelegramCallbackQuery:
    return TelegramCallbackQuery(
        id="query_123",
        from_user=TelegramUser(id=chat_id, is_bot=False, first_name="TestUser"),
        message=make_msg(chat_id, ""),
        data=data,
    )


# ==============================================================================
# 1. IMAGE RESOLVER TESTS
# ==============================================================================

def test_image_resolver_valid_relative_and_absolute_paths(tmp_path: Path):
    """Test resolving images from relative, absolute, and observation directories."""
    wb_id = str(uuid.uuid4())
    obs_dir = tmp_path / "water_bodies" / wb_id / "observations" / "scene_1"
    obs_dir.mkdir(parents=True, exist_ok=True)
    img_file = obs_dir / "rgb.jpg"
    img_file.write_bytes(b"dummy_jpeg_data_content")

    # 1. Relative path 'water_bodies/...'
    obs1 = SatelliteObservation(
        id=str(uuid.uuid4()),
        water_body_id=wb_id,
        external_scene_id="scene_1",
        sensing_date=datetime(2026, 10, 10, tzinfo=timezone.utc),
        local_visual_path=f"water_bodies/{wb_id}/observations/scene_1/rgb.jpg",
    )
    resolved = ObservationImageResolver.resolve_visual_image(obs1, data_dir=tmp_path)
    assert resolved is not None
    assert resolved.exists()
    assert resolved.name == "rgb.jpg"

    # 2. 'data/...' prefix
    obs2 = SatelliteObservation(
        id=str(uuid.uuid4()),
        water_body_id=wb_id,
        external_scene_id="scene_1",
        sensing_date=datetime(2026, 10, 10, tzinfo=timezone.utc),
        local_visual_path=f"data/water_bodies/{wb_id}/observations/scene_1/rgb.jpg",
    )
    resolved2 = ObservationImageResolver.resolve_visual_image(obs2, data_dir=tmp_path)
    assert resolved2 is not None
    assert resolved2.exists()

    # 3. Absolute path
    obs3 = SatelliteObservation(
        id=str(uuid.uuid4()),
        water_body_id=wb_id,
        external_scene_id="scene_1",
        sensing_date=datetime(2026, 10, 10, tzinfo=timezone.utc),
        local_visual_path=str(img_file.resolve()),
    )
    resolved3 = ObservationImageResolver.resolve_visual_image(obs3, data_dir=tmp_path)
    assert resolved3 is not None
    assert resolved3 == img_file.resolve()

    # 4. Directory convention scan when local_visual_path is missing
    obs4 = SatelliteObservation(
        id=str(uuid.uuid4()),
        water_body_id=wb_id,
        external_scene_id="scene_1",
        sensing_date=datetime(2026, 10, 10, tzinfo=timezone.utc),
        local_visual_path=None,
    )
    resolved4 = ObservationImageResolver.resolve_visual_image(obs4, data_dir=tmp_path)
    assert resolved4 is not None
    assert resolved4.name == "rgb.jpg"


def test_image_resolver_invalid_and_traversal_paths(tmp_path: Path):
    """Test that zero-byte files, invalid extensions, and directory traversals return None."""
    wb_id = str(uuid.uuid4())
    obs_dir = tmp_path / "water_bodies" / wb_id / "observations" / "scene_2"
    obs_dir.mkdir(parents=True, exist_ok=True)

    # 1. 0-byte file
    zero_file = obs_dir / "rgb.jpg"
    zero_file.write_bytes(b"")
    obs_zero = SatelliteObservation(
        id=str(uuid.uuid4()),
        water_body_id=wb_id,
        external_scene_id="scene_2",
        sensing_date=datetime(2026, 10, 10, tzinfo=timezone.utc),
        local_visual_path=f"water_bodies/{wb_id}/observations/scene_2/rgb.jpg",
    )
    assert ObservationImageResolver.resolve_visual_image(obs_zero, data_dir=tmp_path) is None

    # 2. Unsupported extension
    txt_file = obs_dir / "image.txt"
    txt_file.write_bytes(b"not an image")
    obs_txt = SatelliteObservation(
        id=str(uuid.uuid4()),
        water_body_id=wb_id,
        external_scene_id="scene_2",
        sensing_date=datetime(2026, 10, 10, tzinfo=timezone.utc),
        local_visual_path=f"water_bodies/{wb_id}/observations/scene_2/image.txt",
    )
    assert ObservationImageResolver.resolve_visual_image(obs_txt, data_dir=tmp_path) is None

    # 3. Path traversal attempt
    obs_traversal = SatelliteObservation(
        id=str(uuid.uuid4()),
        water_body_id=wb_id,
        external_scene_id="scene_2",
        sensing_date=datetime(2026, 10, 10, tzinfo=timezone.utc),
        local_visual_path="../../secret.jpg",
    )
    assert ObservationImageResolver.resolve_visual_image(obs_traversal, data_dir=tmp_path) is None


def test_get_latest_visual_observation_skips_missing_newest(db_session, tmp_path: Path):
    """
    Test newest-first search:
    If the newest observation's image file is missing,
    get_latest_visual_observation returns the older observation that HAS a valid file!
    """
    wb = WaterBody(
        id=str(uuid.uuid4()),
        name="Multi Observation Lake",
        normalized_name="multi observation lake",
        source="osm",
    )
    db_session.add(wb)
    db_session.commit()

    # Observation 1 (Older: 2026-10-01) - Has valid image file on disk
    obs_dir1 = tmp_path / "water_bodies" / wb.id / "observations" / "scene_older"
    obs_dir1.mkdir(parents=True, exist_ok=True)
    img_file1 = obs_dir1 / "rgb.jpg"
    img_file1.write_bytes(b"valid_image_bytes_123")

    obs_older = SatelliteObservation(
        id=str(uuid.uuid4()),
        water_body_id=wb.id,
        external_scene_id="scene_older",
        sensing_date=datetime(2026, 10, 1, tzinfo=timezone.utc),
        local_visual_path=f"water_bodies/{wb.id}/observations/scene_older/rgb.jpg",
    )

    # Observation 2 (Newer: 2026-10-10) - File is MISSING on disk
    obs_newer = SatelliteObservation(
        id=str(uuid.uuid4()),
        water_body_id=wb.id,
        external_scene_id="scene_newer",
        sensing_date=datetime(2026, 10, 10, tzinfo=timezone.utc),
        local_visual_path=f"water_bodies/{wb.id}/observations/scene_newer/rgb.jpg",
    )

    db_session.add_all([obs_older, obs_newer])
    db_session.commit()

    # When querying latest, it should skip obs_newer and successfully return obs_older!
    result = ObservationImageResolver.get_latest_visual_observation(wb.id, db_session, data_dir=tmp_path)
    assert result is not None
    obs, path = result
    assert obs.id == obs_older.id
    assert path.name == "rgb.jpg"


# ==============================================================================
# 2. INTENT SERVICE TESTS
# ==============================================================================

def test_intent_classification_deterministic():
    wb1 = WaterBody(id="wb-1", name="Salim Ali Lake", normalized_name="salim ali lake")
    wb2 = WaterBody(id="wb-2", name="Chilika Lake", normalized_name="chilika lake")
    wb3 = WaterBody(id="wb-3", name="Ooty Lake", normalized_name="ooty lake")
    all_wbs = [wb1, wb2, wb3]

    intent_svc = TelegramIntentService()

    # 1. List
    res = intent_svc.classify_intent("list water bodies", 100, all_wbs)
    assert res.intent == TelegramIntent.LIST_WATER_BODIES

    res = intent_svc.classify_intent("what water bodies do you have?", 100, all_wbs)
    assert res.intent == TelegramIntent.LIST_WATER_BODIES

    # 2. Latest Image
    res = intent_svc.classify_intent("Give me the latest image of Salim Ali Lake", 100, all_wbs)
    assert res.intent == TelegramIntent.LATEST_IMAGE
    assert res.water_body == wb1

    res = intent_svc.classify_intent("Show satellite photo of ooty", 100, all_wbs)
    assert res.intent == TelegramIntent.LATEST_IMAGE
    assert res.water_body == wb3

    # 3. Location / Maps
    res = intent_svc.classify_intent("Where is Salim Ali Lake?", 100, all_wbs)
    assert res.intent == TelegramIntent.LOCATION
    assert res.water_body == wb1

    res = intent_svc.classify_intent("Open Chilika Lake on maps", 100, all_wbs)
    assert res.intent == TelegramIntent.LOCATION
    assert res.water_body == wb2

    # 4. Water quality
    res = intent_svc.classify_intent("What is the water quality of Chilika Lake?", 100, all_wbs)
    assert res.intent == TelegramIntent.WATER_QUALITY
    assert res.water_body == wb2

    # 5. Monitoring frequency
    res = intent_svc.classify_intent("How often does Salim Ali Lake change?", 100, all_wbs)
    assert res.intent == TelegramIntent.MONITORING_FREQUENCY
    assert res.water_body == wb1

    # 6. Today phrasing
    res = intent_svc.classify_intent("How is Salim Ali Lake today?", 100, all_wbs)
    assert res.intent == TelegramIntent.WATER_BODY_INFO
    assert res.water_body == wb1
    assert res.is_today_query is True


# ==============================================================================
# 3. CONVERSATIONAL CONTEXT FOLLOW-UP TESTS
# ==============================================================================

def test_conversational_context_multi_turn(mock_telegram_client, db_session, tmp_path):
    """
    Test conversational sequence:
    User: Tell me about Salim Ali Lake
    Bot: [summary]
    User: Show its image
    Bot: [photo]
    User: Where is it?
    Bot: [Google Maps]
    User: How is the water?
    Bot: [quality summary]
    """
    wb = WaterBody(
        id=str(uuid.uuid4()),
        name="Salim Ali Lake",
        normalized_name="salim ali lake",
        source="osm",
        centroid_lat=19.89,
        centroid_lon=75.34,
        area_sq_km=0.18,
    )
    db_session.add(wb)
    db_session.commit()

    # Add observation with image
    obs_dir = tmp_path / "water_bodies" / wb.id / "observations" / "scene_salim"
    obs_dir.mkdir(parents=True, exist_ok=True)
    img = obs_dir / "rgb.jpg"
    img.write_bytes(b"salim_ali_visual_bytes")

    obs = SatelliteObservation(
        id=str(uuid.uuid4()),
        water_body_id=wb.id,
        external_scene_id="scene_salim",
        sensing_date=datetime(2026, 10, 10, tzinfo=timezone.utc),
        cloud_cover_percent=2.0,
        local_visual_path=f"water_bodies/{wb.id}/observations/scene_salim/rgb.jpg",
    )
    db_session.add(obs)
    db_session.commit()

    async def run():
        with patch.object(settings, "DATA_DIR", tmp_path):
            handler = TelegramCommandHandler(mock_telegram_client, db_factory=lambda: db_session)
            chat_id = 9999

            # 1. Turn 1: "Tell me about Salim Ali Lake"
            msg1 = make_msg(chat_id, "Tell me about Salim Ali Lake")
            await handler.handle_message(msg1)

            assert mock_telegram_client.send_message.call_count >= 1
            reply1 = mock_telegram_client.send_message.call_args[0][1]
            assert "SALIM ALI LAKE" in reply1
            # Context must now remember wb.id
            assert handler.intent_service.get_chat_context(chat_id) == wb.id

            mock_telegram_client.send_message.reset_mock()
            mock_telegram_client.send_photo.reset_mock()

            # 2. Turn 2: "Show its image" (Uses context!)
            msg2 = make_msg(chat_id, "Show its image")
            await handler.handle_message(msg2)

            mock_telegram_client.send_photo.assert_called_once()
            _, photo_kwargs = mock_telegram_client.send_photo.call_args
            assert photo_kwargs["chat_id"] == chat_id
            assert photo_kwargs["photo_bytes"] == b"salim_ali_visual_bytes"

            mock_telegram_client.send_message.reset_mock()
            mock_telegram_client.send_photo.reset_mock()

            # 3. Turn 3: "Where is it?" (Uses context!)
            msg3 = make_msg(chat_id, "Where is it?")
            await handler.handle_message(msg3)

            mock_telegram_client.send_message.assert_called_once()
            reply3 = mock_telegram_client.send_message.call_args[0][1]
            assert "Salim Ali Lake" in reply3
            assert "maps.google.com" in reply3 or "google.com/maps" in reply3

            mock_telegram_client.send_message.reset_mock()

            # 4. Turn 4: "How is the water?" (Uses context!)
            msg4 = make_msg(chat_id, "How is the water?")
            await handler.handle_message(msg4)

            mock_telegram_client.send_message.assert_called_once()
            reply4 = mock_telegram_client.send_message.call_args[0][1]
            assert "Water Quality" in reply4
            assert "Salim Ali Lake" in reply4

    asyncio.run(run())


# ==============================================================================
# 4. TELEGRAM CALLBACK QUERY TESTS
# ==============================================================================

def test_telegram_callback_queries(mock_telegram_client, db_session, tmp_path):
    wb = WaterBody(
        id=str(uuid.uuid4()),
        name="Chilika Lake",
        normalized_name="chilika lake",
        source="osm",
        centroid_lat=19.72,
        centroid_lon=85.32,
    )
    db_session.add(wb)
    db_session.commit()

    async def run():
        with patch.object(settings, "DATA_DIR", tmp_path):
            handler = TelegramCommandHandler(mock_telegram_client, db_factory=lambda: db_session)
            mock_telegram_client.answer_callback_query = AsyncMock(return_value=True)

            # 1. Quality button callback
            cb_qual = make_callback(777, f"wb_qual:{wb.id}")
            await handler.handle_callback_query(cb_qual)
            mock_telegram_client.answer_callback_query.assert_called_with("query_123")
            reply = mock_telegram_client.send_message.call_args[0][1]
            assert "Water Quality" in reply
            assert "Chilika Lake" in reply

            mock_telegram_client.send_message.reset_mock()

            # 2. Monitoring button callback
            cb_mon = make_callback(777, f"wb_mon:{wb.id}")
            await handler.handle_callback_query(cb_mon)
            reply = mock_telegram_client.send_message.call_args[0][1]
            assert "Monitoring History" in reply
            assert "Chilika Lake" in reply

    asyncio.run(run())


# ==============================================================================
# 5. REST API VISUAL STATUS & STREAMING TESTS
# ==============================================================================

def test_api_visual_status_and_streaming(client: TestClient, db_session, tmp_path: Path):
    wb = WaterBody(
        id=str(uuid.uuid4()),
        name="Ooty Lake",
        normalized_name="ooty lake",
        source="osm",
    )
    db_session.add(wb)
    db_session.commit()

    # 1. When 0 observations exist:
    res = client.get(f"/api/v1/water-bodies/{wb.id}/visual-status")
    assert res.status_code == 200
    data = res.json()
    assert data["observation_count"] == 0
    assert data["image_available"] is False

    # 2. Add an observation with file
    obs_dir = tmp_path / "water_bodies" / wb.id / "observations" / "scene_ooty"
    obs_dir.mkdir(parents=True, exist_ok=True)
    img_file = obs_dir / "rgb.jpg"
    img_file.write_bytes(b"ooty_test_jpeg_bytes")

    obs = SatelliteObservation(
        id=str(uuid.uuid4()),
        water_body_id=wb.id,
        external_scene_id="scene_ooty",
        sensing_date=datetime(2026, 10, 10, tzinfo=timezone.utc),
        local_visual_path=f"water_bodies/{wb.id}/observations/scene_ooty/rgb.jpg",
    )
    db_session.add(obs)
    db_session.commit()

    with patch.object(settings, "DATA_DIR", tmp_path):
        # Check visual-status
        res2 = client.get(f"/api/v1/water-bodies/{wb.id}/visual-status")
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2["observation_count"] == 1
        assert data2["image_available"] is True
        assert data2["image_size_bytes"] == len(b"ooty_test_jpeg_bytes")

        # Test streaming endpoint
        res3 = client.get(f"/api/v1/water-bodies/{wb.id}/observations/{obs.id}/visual")
        assert res3.status_code == 200
        assert res3.headers["content-type"] == "image/jpeg"
        assert res3.content == b"ooty_test_jpeg_bytes"

        # Test non-existent observation returns 404
        bad_id = str(uuid.uuid4())
        res4 = client.get(f"/api/v1/water-bodies/{wb.id}/observations/{bad_id}/visual")
        assert res4.status_code == 404
