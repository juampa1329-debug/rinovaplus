"""The ingress access log is useful without exposing webhook contents."""

import re
from pathlib import Path


def test_siie_proxy_logs_only_status_timing_and_preserves_delivery_guards():
    config = (
        Path(__file__).resolve().parents[2] / "docker/nginx.coolify-frontend.conf"
    ).read_text(encoding="utf-8")
    format_value = re.search(r"log_format siie_webhook '([^']+)';", config)[1]
    # iso8601 has digits; explicitly exclude every other Nginx variable, including
    # URL/query, headers, client address, cookies and body.
    assert set(re.findall(r"\$[a-z_0-9]+", format_value)) == {
        "$time_iso8601", "$status", "$upstream_status", "$request_time"
    }
    block = config.split("location = /hooks/siie/v1 {", 1)[1].split("\n        }", 1)[0]
    assert "access_log /dev/stdout siie_webhook;" in block
    assert "client_max_body_size 64k;" in block
    assert "proxy_next_upstream off;" in block
    assert "proxy_pass $backend;" in block
