"""Resource-bounded PDF text extraction subprocess; no network or execution."""

import io
import json
import logging
import sys


def main():
    import resource

    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024,) * 2)
    resource.setrlimit(resource.RLIMIT_CPU, (6, 6))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
    from pypdf import PdfReader, apply_configuration

    logging.disable(logging.CRITICAL)
    configuration = apply_configuration(zlib_maximum_output_length=4_000_000, lzw_maximum_output_length=4_000_000, maximum_declared_stream_length=5_000_000, array_maximum_element_count=10_000, dictionary_maximum_element_count=10_000)
    configuration.__enter__()
    data = sys.stdin.buffer.read(5_000_001)
    if not data or len(data) > 5_000_000:
        return 2
    reader = PdfReader(io.BytesIO(data), strict=True)
    if reader.is_encrypted or not 0 < len(reader.pages) <= 150:
        return 2
    pages, total, decoded = [], 0, 0
    for index, page in enumerate(reader.pages):
        content = page.get_contents()
        if content:
            decoded += len(content.get_data())
            if decoded > 12_000_000:
                return 2
        text = page.extract_text() or ""
        total += len(text)
        if total > 300_000 or len(text) > 40_000:
            return 2
        if text.strip():
            pages.append({"page": index + 1, "text": text})
    if not pages:
        return 3
    sys.stdout.write(json.dumps(pages, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(2)
