"""Tests for the anomaly detector."""

import pytest

from app.ml.anomaly import AnomalyDetector


@pytest.mark.asyncio
async def test_detect_anomalies(mock_provider, mock_llm):
    detector = AnomalyDetector(mock_provider, mock_llm)
    results = await detector.detect_anomalies(mock_provider.transactions)

    assert len(results) >= 1
    anomaly = results[0]
    assert anomaly.is_anomaly is True
    assert anomaly.severity == "high"
    assert anomaly.transaction.id == "txn4"
    assert anomaly.score > 0.5


@pytest.mark.asyncio
async def test_detect_anomalies_empty(mock_provider, mock_llm):
    detector = AnomalyDetector(mock_provider, mock_llm)
    results = await detector.detect_anomalies([])
    assert results == []


@pytest.mark.asyncio
async def test_compute_stats(mock_provider, mock_llm):
    detector = AnomalyDetector(mock_provider, mock_llm)
    stats = detector._compute_stats(mock_provider.transactions)

    assert stats["total_transactions"] == 4
    assert "by_contact" in stats
    assert "Acme Corp" in stats["by_contact"]
