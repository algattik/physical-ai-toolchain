"""Tests for the in-process issue journal that powers UI toasts."""

from __future__ import annotations

import time

import pytest

from scene_aligner import aligner


@pytest.fixture(autouse=True)
def _reset_journal():
    aligner._ISSUES.clear()
    aligner._ISSUES_THROTTLE.clear()
    aligner._ISSUES_SEQ = 0
    yield
    aligner._ISSUES.clear()
    aligner._ISSUES_THROTTLE.clear()
    aligner._ISSUES_SEQ = 0


def test_record_issue_appends_and_returns_via_since():
    aligner._record_issue('warning', 'demo', 'thing broke')
    seq, items = aligner._issues_since(since=0)
    assert seq == 1
    assert len(items) == 1
    entry = items[0]
    assert entry['level'] == 'warning'
    assert entry['source'] == 'demo'
    assert entry['message'] == 'thing broke'
    assert entry['count'] == 1
    assert entry['seq'] == 1


def test_throttles_duplicate_emissions_into_count():
    for _ in range(5):
        aligner._record_issue('error', 'src', 'same msg', key='same')
    _, items = aligner._issues_since(since=0)
    assert len(items) == 1
    assert items[0]['count'] == 5


def test_distinct_keys_get_separate_entries():
    aligner._record_issue('warning', 'src', 'first', key='k1')
    aligner._record_issue('warning', 'src', 'second', key='k2')
    _, items = aligner._issues_since(since=0)
    assert {it['key'] for it in items} == {'k1', 'k2'}


def test_since_filter_excludes_already_seen():
    aligner._record_issue('info', 'src', 'one', key='a')
    seq1, items1 = aligner._issues_since(since=0)
    assert len(items1) == 1
    aligner._record_issue('info', 'src', 'two', key='b')
    seq2, items2 = aligner._issues_since(since=seq1)
    assert seq2 > seq1
    assert len(items2) == 1
    assert items2[0]['message'] == 'two'


def test_throttle_window_releases_after_interval():
    aligner._record_issue('info', 'src', 'x', key='k', throttle_s=0.05)
    aligner._record_issue('info', 'src', 'x', key='k', throttle_s=0.05)
    _, items = aligner._issues_since(since=0)
    assert len(items) == 1
    assert items[0]['count'] == 2
    time.sleep(0.1)
    aligner._record_issue('info', 'src', 'x', key='k', throttle_s=0.05)
    _, items = aligner._issues_since(since=0)
    assert len(items) == 2


def test_journal_is_bounded():
    original_max = aligner._ISSUES.maxlen
    # We cannot resize the existing deque; just verify the configured cap.
    assert original_max is not None and original_max >= 100


def test_displayable_encodings_match_decoder_set():
    # Probe filter must stay in sync with the live decoder.
    decoder_supported = {'bgr8', 'rgb8', 'bgra8', 'rgba8', 'mono8', '8uc1'}
    assert aligner.DISPLAYABLE_ENCODINGS == decoder_supported
