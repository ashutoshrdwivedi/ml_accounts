"""Tests for the transaction categorizer."""

import pytest

from app.ml.categorizer import Categorizer


@pytest.mark.asyncio
async def test_categorize_transactions(mock_provider, mock_llm):
    categorizer = Categorizer(mock_provider, mock_llm)
    transactions = mock_provider.transactions

    results = await categorizer.categorize_transactions(transactions)

    assert len(results) == len(transactions)
    # txn1 should be categorized as Office Supplies
    assert results[0].account_id == "acc1"
    assert results[0].account_name == "Office Supplies"
    assert results[0].confidence == 0.95


@pytest.mark.asyncio
async def test_categorize_empty_list(mock_provider, mock_llm):
    categorizer = Categorizer(mock_provider, mock_llm)
    results = await categorizer.categorize_transactions([])
    assert results == []


@pytest.mark.asyncio
async def test_apply_categories_respects_confidence(mock_provider, mock_llm):
    categorizer = Categorizer(mock_provider, mock_llm)
    transactions = await categorizer.categorize_transactions(mock_provider.transactions)

    applied = await categorizer.apply_categories(transactions)

    # Only transactions with confidence >= 0.7 should be applied
    # txn4 has confidence 0.30, so it shouldn't be applied
    assert len(applied) == 3
    for t in applied:
        assert t.account_id != ""
