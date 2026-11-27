"""The offline graph accepts Git newline transport, never stale content."""

import hashlib
import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "continuity_graph", Path(__file__).parents[1] / "tools/conversation_continuity_graph.py"
)
graph = importlib.util.module_from_spec(spec)
spec.loader.exec_module(graph)


@pytest.mark.parametrize("before,after", [
    (b"one\ntwo\n", b"one\r\ntwo\r\n"),
    (b"one\r\ntwo\r\n", b"one\ntwo\n"),
    (b"one\ntwo\n", b"one\ntwo\n"),
])
def test_exact_newline_transport_matches_without_refreshing_extraction(tmp_path, before, after):
    source = tmp_path / "reference.md"
    source.write_bytes(after)
    assert graph.source_hash_matches(source, hashlib.sha256(before).hexdigest())


def test_same_line_count_with_changed_content_is_still_rejected(tmp_path):
    source = tmp_path / "reference.md"
    source.write_bytes(b"one\r\nchanged\r\n")
    assert not graph.source_hash_matches(source, hashlib.sha256(b"one\ntwo\n").hexdigest())
