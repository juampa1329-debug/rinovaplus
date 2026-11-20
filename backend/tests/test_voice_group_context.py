from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.institutional import voice_transcripts, voice_audio, sales_context


def group(monkeypatch, *, interpreted=(), attempted=0, count=2):
    ids = [str(uuid4()) for _ in range(count)]
    data = {"conversation": str(uuid4()), "identity": str(uuid4()), "incoming": ids[-1]}
    messages = [{"MessageId": k, "Sequence": i+10, "Direction":"incoming", "Body":"[audio]", "PriorAttempts":attempted}
                for i,k in enumerate(ids)]
    calls = []
    c = SimpleNamespace(context_cutoff=lambda _:8, audio_history=lambda _, ms:[
        {**m, **({"body_origin":"automatic_audio_transcription", "Body":"Programa interpretado"} if m["MessageId"] in interpreted else {})} for m in ms])
    settings = SimpleNamespace(ticket={"context":[[1,str(uuid4())]]})
    monkeypatch.setattr(voice_transcripts.db, "rows", lambda cursor, sql, *args:calls.append((sql,args)) or messages)
    monkeypatch.setattr(voice_audio, "input_audio", lambda cursor, profile, bound:calls.append(bound) or {"id":"fixture", "raw":b"voice"})
    return c, settings, data, ids, calls


def test_two_unanswered_audios_interpret_oldest_before_followup_and_reuse_the_saved_transcript(monkeypatch):
    c, settings, data, ids, calls = group(monkeypatch)
    first = voice_transcripts.pending_input(c, settings, data, 11)
    assert first["message_id"] == ids[0] and calls[-1]["incoming"] == ids[0]
    c.audio_history = lambda _, ms:[{**m, **({"body_origin":"automatic_audio_transcription"} if m["MessageId"]==ids[0] else {})} for m in ms]
    second = voice_transcripts.pending_input(c, settings, data, 11)
    assert second["message_id"] == ids[1]
    c.audio_history = lambda _, ms:[{**m,"body_origin":"automatic_audio_transcription"} for m in ms]
    assert voice_transcripts.pending_input(c, settings, data, 11) is None
    assert "sent.Direction='outgoing'" in calls[0][0] and "m.Sequence>?" in calls[0][0]
    assert calls[0][1][-2:] == (8,11)


def test_attempted_superseded_audio_cannot_trigger_an_automatic_paid_retry(monkeypatch):
    c, settings, data, _, calls = group(monkeypatch, attempted=1)
    with pytest.raises(HTTPException, match="voice_prior_audio_review_required"):
        voice_transcripts.pending_input(c, settings, data, 11)
    assert len(calls) == 1  # No asset read and no provider call.


def test_large_audio_group_requires_review_instead_of_truncating_or_skipping(monkeypatch):
    c, settings, data, _, calls = group(monkeypatch, count=7)
    with pytest.raises(HTTPException, match="voice_batch_review_required"):
        voice_transcripts.pending_input(c, settings, data, 16)
    assert len(calls) == 1


def test_interpreted_change_of_program_survives_a_generic_second_audio():
    programs = [{"program_id":1,"name":"BARISMO Y BARTENDER"}, {"program_id":2,"name":"DESARROLLO DE SOFTWARE Y APLICACIONES MOVILES","schedule":"DIURNA"}]
    history = [{"MessageId":"old","Sequence":1,"Direction":"incoming","Body":"Me interesa Barismo"},
               {"MessageId":"first","Sequence":2,"Direction":"incoming","Body":"Ahora prefiero desarrollo de software en jornada diurna"},
               {"MessageId":"second","Sequence":3,"Direction":"incoming","Body":"También quisiera saber cómo me ayudaría a crear mi negocio"}]
    assert sales_context.interest(programs,{},history)["program_id"] == 2
