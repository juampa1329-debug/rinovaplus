"""Bounded PDF structure inspection in a disposable process; never render content."""

import logging
import sys
from urllib.parse import urlsplit


class ActiveContent(Exception):
    pass


def inspect(source):
    try:
        import resource

        resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024,) * 2)
        resource.setrlimit(resource.RLIMIT_CPU, (5, 5))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
        resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
        from pypdf import PdfReader, apply_configuration
        from pypdf.errors import LimitReachedError
        from pypdf.generic import (
            ArrayObject,
            DictionaryObject,
            IndirectObject,
            NameObject,
            NullObject,
            NumberObject,
            FloatObject,
            StreamObject,
            TextStringObject,
        )
    except (ImportError, OSError, ValueError):
        return 5
    logging.disable(logging.CRITICAL)
    active_keys = {
        "/JS",
        "/JavaScript",
        "/OpenAction",
        "/AA",
        "/Launch",
        "/EmbeddedFiles",
        "/EF",
        "/XFA",
        "/RichMediaContent",
        "/RichMediaSettings",
        "/Encrypt",
    }
    active_names = {
        "/JavaScript",
        "/Launch",
        "/EmbeddedFile",
        "/Filespec",
        "/RichMedia",
        "/FileAttachment",
        "/Sound",
        "/Movie",
        "/Screen",
        "/3D",
        "/SubmitForm",
        "/ImportData",
        "/GoToR",
        "/GoToE",
        "/Rendition",
        "/Thread",
        "/Hide",
        "/Named",
        "/ResetForm",
        "/SetOCGState",
        "/Trans",
        "/GoTo3DView",
    }

    def resolve(value):
        return value.get_object() if isinstance(value, IndirectObject) else value

    def validate_action(value):
        value = resolve(value)
        if not isinstance(value, DictionaryObject) or "/Next" in value:
            raise ActiveContent()
        action = resolve(value.get("/S"))
        if action == "/URI":
            address = resolve(value.get("/URI"))
            if (
                not isinstance(address, TextStringObject)
                or not 0 < len(address) <= 2048
                or any(ord(char) <= 32 or ord(char) == 127 for char in address)
                or "\\" in address
            ):
                raise ActiveContent()
            try:
                url = urlsplit(address)
                port = url.port
                if (
                    url.scheme.lower() not in ("http", "https")
                    or not url.hostname
                    or url.username is not None
                    or url.password is not None
                    or port is not None
                    and not 0 < port <= 65535
                ):
                    raise ActiveContent()
            except ValueError:
                raise ActiveContent() from None
        elif action == "/GoTo":
            destination = resolve(value.get("/D"))
            if isinstance(destination, (TextStringObject, NameObject)):
                if not 0 < len(destination) <= 2048:
                    raise ActiveContent()
            elif isinstance(destination, ArrayObject) and 2 <= len(destination) <= 6:
                page = resolve(destination[0])
                if (
                    not isinstance(page, DictionaryObject)
                    or resolve(page.get("/Type")) != "/Page"
                    or resolve(destination[1])
                    not in (
                        "/XYZ",
                        "/Fit",
                        "/FitH",
                        "/FitV",
                        "/FitR",
                        "/FitB",
                        "/FitBH",
                        "/FitBV",
                    )
                    or any(
                        not isinstance(
                            resolve(item), (NumberObject, FloatObject, NullObject)
                        )
                        for item in destination[2:]
                    )
                ):
                    raise ActiveContent()
            else:
                raise ActiveContent()
        else:
            raise ActiveContent()

    try:
        with apply_configuration(
            maximum_declared_stream_length=5_000_000,
            array_based_stream_maximum_output_length=10_000_000,
            array_maximum_element_count=10_000,
            dictionary_maximum_element_count=10_000,
            zlib_maximum_output_length=10_000_000,
            zlib_maximum_recovery_input_length=100_000,
            lzw_maximum_output_length=10_000_000,
            run_length_maximum_output_length=10_000_000,
            brotli_maximum_output_length=10_000_000,
            jbig2_maximum_output_length=10_000_000,
            jbig2dec_binary=None,
            image_maximum_buffer_size=10_000_000,
            stream_filters_maximum_length=8,
            stream_decoding_work_maximum_length=30_000_000,
            page_tree_maximum_entries=2000,
            page_tree_maximum_depth=64,
        ):
            with PdfReader(source, strict=True, root_object_recovery_limit=0) as reader:
                if reader.is_encrypted or "/Encrypt" in reader.trailer:
                    raise ActiveContent()
                references = {
                    (number, generation)
                    for generation, objects in reader.xref.items()
                    for number, offset in objects.items()
                    if number and offset
                }
                references.update((number, 0) for number in reader.xref_objStm)
                if not references or len(references) > 10_000:
                    return 4
                if reader.root_object.get("/Type") != "/Catalog":
                    return 3
                if not 0 < len(reader.pages) <= 2000:
                    return 4
                stack = [(reader.trailer, 0)]
                stack.extend(
                    (IndirectObject(number, generation, reader), 0)
                    for number, generation in references
                )
                visited_references, visited_objects = set(), set()
                count = decoded_bytes = 0
                while stack:
                    value, depth = stack.pop()
                    count += 1
                    if count > 100_000 or depth > 64:
                        return 4
                    if isinstance(value, IndirectObject):
                        key = (value.idnum, value.generation)
                        if key in visited_references:
                            continue
                        visited_references.add(key)
                        resolved = value.get_object()
                        if resolved is None:
                            return 3
                        stack.append((resolved, depth + 1))
                    elif isinstance(value, (DictionaryObject, ArrayObject)):
                        if id(value) in visited_objects:
                            continue
                        visited_objects.add(id(value))
                        if isinstance(value, DictionaryObject):
                            if active_keys.intersection(value):
                                raise ActiveContent()
                            if "/A" in value:
                                validate_action(value["/A"])
                            if (
                                resolve(value.get("/Type")) == "/Action"
                                or "/URI" in value
                                or resolve(value.get("/S")) in ("/URI", "/GoTo")
                            ):
                                validate_action(value)
                            stack.extend((item, depth + 1) for item in value.values())
                            if isinstance(value, StreamObject) and resolve(
                                value.get("/Type")
                            ) in ("/ObjStm", "/XRef"):
                                decoded_bytes += len(value.get_data())
                                if decoded_bytes > 30_000_000:
                                    return 4
                        else:
                            stack.extend((item, depth + 1) for item in value)
                    elif isinstance(value, NameObject) and value in active_names:
                        raise ActiveContent()
        return 0
    except ActiveContent:
        return 2
    except (MemoryError, RecursionError, LimitReachedError):
        return 4
    except Exception:
        return 3


if __name__ == "__main__":
    sys.exit(inspect(sys.argv[1]) if len(sys.argv) == 2 else 3)
