"""Tests for the bounded LRU caches used by reference/thumbnail storage."""

from __future__ import annotations

from collections import OrderedDict

from scene_aligner.aligner import _cache_get, _cache_put


def test_lru_evicts_oldest_when_over_capacity():
    cache: OrderedDict = OrderedDict()
    for k in range(5):
        _cache_put(cache, k, f'v{k}', max_items=3)
    assert list(cache.keys()) == [2, 3, 4]


def test_lru_get_promotes_recency():
    cache: OrderedDict = OrderedDict()
    for k in range(3):
        _cache_put(cache, k, f'v{k}', max_items=3)
    assert _cache_get(cache, 0) == 'v0'  # touch oldest, promoting it
    _cache_put(cache, 99, 'v99', max_items=3)
    # 1 is now LRU (since 0 was promoted) and gets evicted; 0, 2, 99 remain.
    assert list(cache.keys()) == [2, 0, 99]


def test_lru_get_returns_none_for_missing_key():
    cache: OrderedDict = OrderedDict()
    assert _cache_get(cache, 'missing') is None


def test_lru_distinguishes_episode_in_key():
    """Reference cache key includes episode_idx so two episodes from the same
    (dataset, camera) cache independently — there is no way for one episode's
    frame to be returned for another."""
    cache: OrderedDict = OrderedDict()
    _cache_put(cache, ('ds', 'cam', 0), 'frame0', max_items=10)
    _cache_put(cache, ('ds', 'cam', 1), 'frame1', max_items=10)
    assert _cache_get(cache, ('ds', 'cam', 0)) == 'frame0'
    assert _cache_get(cache, ('ds', 'cam', 1)) == 'frame1'
