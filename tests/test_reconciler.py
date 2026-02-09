"""Tests for the bank reconciler."""

from datetime import date

import pytest

from app.ml.reconciler import Reconciler


@pytest.mark.asyncio
async def test_reconcile(mock_provider, mock_llm):
    reconciler = Reconciler(mock_provider, mock_llm)
    matches = await reconciler.reconcile(
        "bank1", date(2024, 1, 1), date(2024, 1, 31)
    )

    assert len(matches) >= 1
    match = matches[0]
    assert match.bank_transaction.id == "bt2"
    assert match.matched_entity.id == "inv1"
    assert match.confidence == 0.95
    assert match.match_type == "exact_amount"


@pytest.mark.asyncio
async def test_reconcile_no_unmatched(mock_provider, mock_llm):
    # Mark all bank transactions as matched
    for bt in mock_provider.bank_transactions:
        bt.is_matched = True

    reconciler = Reconciler(mock_provider, mock_llm)
    matches = await reconciler.reconcile("bank1", date(2024, 1, 1), date(2024, 1, 31))
    assert matches == []


@pytest.mark.asyncio
async def test_apply_matches(mock_provider, mock_llm):
    reconciler = Reconciler(mock_provider, mock_llm)
    matches = await reconciler.reconcile("bank1", date(2024, 1, 1), date(2024, 1, 31))

    applied = await reconciler.apply_matches(matches, min_confidence=0.8)
    assert applied == 1
