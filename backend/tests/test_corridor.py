"""
backend/tests/test_corridor.py
────────────────────────────────
Unit tests for GreenCorridorService.

All tests use stub MQTT and in-memory Redis (redis_client=None) so no
external services are needed.
"""

from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.corridor import GreenCorridorService, EmergencyEvent, simulate_ambulance_route
from app.services.optimizer import SignalOptimizer


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture()
def stub_mqtt():
    m = MagicMock()
    m.publish = MagicMock()
    return m

@pytest.fixture()
def svc(stub_mqtt):
    """Corridor service with in-memory storage (no Redis)."""
    return GreenCorridorService(
        signal_optimizer=SignalOptimizer(),
        mqtt_client=stub_mqtt,
        redis_client=None,
        green_ttl=90,
    )

@pytest.fixture()
def sample_event():
    return simulate_ambulance_route(
        ["INT-01", "INT-02", "INT-03"],
        vehicle_id="AMB-TEST-001",
        vehicle_type="ambulance",
    )


# ── simulate_ambulance_route factory ─────────────────────────────────────────

class TestSimulateFactory:
    def test_returns_emergency_event(self, sample_event):
        assert isinstance(sample_event, EmergencyEvent)

    def test_event_id_is_uuid(self, sample_event):
        import uuid
        uuid.UUID(sample_event.event_id)   # raises if not valid UUID

    def test_status_is_active(self, sample_event):
        assert sample_event.status == "active"

    def test_route_preserved(self, sample_event):
        assert sample_event.route == ["INT-01", "INT-02", "INT-03"]

    def test_current_intersection_is_first(self, sample_event):
        assert sample_event.current_intersection == "INT-01"

    def test_vehicle_id_preserved(self, sample_event):
        assert sample_event.vehicle_id == "AMB-TEST-001"

    def test_estimated_arrival_after_dispatch(self, sample_event):
        assert sample_event.estimated_arrival > sample_event.dispatch_time


# ── activate_corridor ─────────────────────────────────────────────────────────

class TestActivateCorridor:
    @pytest.mark.asyncio
    async def test_force_green_sent_to_all_intersections(self, svc, stub_mqtt, sample_event):
        await svc.activate_corridor(sample_event)
        published_topics = [call.args[0] for call in stub_mqtt.publish.call_args_list]
        for iid in sample_event.route:
            assert f"traffic/signals/{iid}/command" in published_topics

    @pytest.mark.asyncio
    async def test_force_green_payload_correct(self, svc, stub_mqtt, sample_event):
        await svc.activate_corridor(sample_event)
        first_call = stub_mqtt.publish.call_args_list[0]
        payload = json.loads(first_call.args[1])
        assert payload["command"] == "FORCE_GREEN"
        assert payload["event_id"] == sample_event.event_id

    @pytest.mark.asyncio
    async def test_emergency_alert_broadcast(self, svc, stub_mqtt, sample_event):
        await svc.activate_corridor(sample_event)
        all_topics = [c.args[0] for c in stub_mqtt.publish.call_args_list]
        assert "traffic/emergency/alert" in all_topics

    @pytest.mark.asyncio
    async def test_event_appears_in_active_corridors(self, svc, sample_event):
        await svc.activate_corridor(sample_event)
        active = await svc.get_active_corridors()
        ids = [e.event_id for e in active]
        assert sample_event.event_id in ids

    @pytest.mark.asyncio
    async def test_status_set_to_active(self, svc, sample_event):
        await svc.activate_corridor(sample_event)
        assert sample_event.status == "active"


# ── deactivate_intersection ───────────────────────────────────────────────────

class TestDeactivateIntersection:
    @pytest.mark.asyncio
    async def test_restore_normal_published(self, svc, stub_mqtt):
        await svc.deactivate_intersection("INT-01")
        topics = [c.args[0] for c in stub_mqtt.publish.call_args_list]
        assert "traffic/signals/INT-01/restore" in topics

    @pytest.mark.asyncio
    async def test_restore_payload_correct(self, svc, stub_mqtt):
        await svc.deactivate_intersection("INT-99")
        call = stub_mqtt.publish.call_args_list[-1]
        payload = json.loads(call.args[1])
        assert payload["command"] == "RESTORE_NORMAL"
        assert payload["intersection_id"] == "INT-99"


# ── deactivate_full_corridor ──────────────────────────────────────────────────

class TestDeactivateFullCorridor:
    @pytest.mark.asyncio
    async def test_restores_all_intersections(self, svc, stub_mqtt, sample_event):
        await svc.activate_corridor(sample_event)
        stub_mqtt.publish.reset_mock()
        await svc.deactivate_full_corridor(sample_event.event_id)
        restore_topics = [
            c.args[0] for c in stub_mqtt.publish.call_args_list
            if "/restore" in c.args[0]
        ]
        for iid in sample_event.route:
            assert f"traffic/signals/{iid}/restore" in restore_topics

    @pytest.mark.asyncio
    async def test_clear_event_published(self, svc, stub_mqtt, sample_event):
        await svc.activate_corridor(sample_event)
        stub_mqtt.publish.reset_mock()
        await svc.deactivate_full_corridor(sample_event.event_id)
        topics = [c.args[0] for c in stub_mqtt.publish.call_args_list]
        assert "traffic/emergency/clear" in topics

    @pytest.mark.asyncio
    async def test_event_removed_from_active_list(self, svc, sample_event):
        await svc.activate_corridor(sample_event)
        await svc.deactivate_full_corridor(sample_event.event_id)
        active = await svc.get_active_corridors()
        ids = [e.event_id for e in active]
        assert sample_event.event_id not in ids

    @pytest.mark.asyncio
    async def test_deactivate_nonexistent_event_is_noop(self, svc, stub_mqtt):
        stub_mqtt.publish.reset_mock()
        await svc.deactivate_full_corridor("does-not-exist")
        # No publish calls should be made
        stub_mqtt.publish.assert_not_called()


# ── get_active_corridors ──────────────────────────────────────────────────────

class TestGetActiveCorridors:
    @pytest.mark.asyncio
    async def test_empty_initially(self, svc):
        active = await svc.get_active_corridors()
        assert active == []

    @pytest.mark.asyncio
    async def test_multiple_events_tracked(self, svc, stub_mqtt):
        e1 = simulate_ambulance_route(["INT-01"], vehicle_id="AMB-A")
        e2 = simulate_ambulance_route(["INT-02"], vehicle_id="AMB-B")
        await svc.activate_corridor(e1)
        await svc.activate_corridor(e2)
        active = await svc.get_active_corridors()
        assert len(active) == 2

    @pytest.mark.asyncio
    async def test_completed_corridor_absent(self, svc, stub_mqtt, sample_event):
        await svc.activate_corridor(sample_event)
        await svc.deactivate_full_corridor(sample_event.event_id)
        active = await svc.get_active_corridors()
        assert all(e.event_id != sample_event.event_id for e in active)


# ── EmergencyEvent serialisation ──────────────────────────────────────────────

class TestEmergencyEventSerialisation:
    def test_to_dict_contains_all_fields(self, sample_event):
        d = sample_event.to_dict()
        for key in ["event_id", "vehicle_id", "vehicle_type", "route",
                    "dispatch_time", "estimated_arrival", "status"]:
            assert key in d

    def test_to_json_parses_back(self, sample_event):
        restored = EmergencyEvent.from_dict(json.loads(sample_event.to_json()))
        assert restored.event_id == sample_event.event_id
        assert restored.route == sample_event.route
