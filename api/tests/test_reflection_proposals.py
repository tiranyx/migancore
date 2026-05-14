from routers import reflection_daemon


def test_extract_upgrade_proposal_from_reflection_line():
    text = """
[Reflection - 24h | 1 success, 0 fail]

1. **Belajar apa** - routing cepat berguna.
2. **Gagal apa** - belum ada eval misfire.
3. **Perlu alat apa** - dataset probe kecil.
4. **Usul upgrade apa** - Buat eval routing reflex/lightweight/full dengan 10 prompt.
"""

    proposal = reflection_daemon._proposal_from_reflection_text("reflection_123", text)

    assert proposal is not None
    assert proposal["title"] == "Reflection upgrade: Buat eval routing reflex/lightweight/full dengan 10 prompt."
    assert proposal["source"] == "eval_failure"
    assert proposal["created_by"] == "reflection_daemon"
    assert proposal["metadata"]["reflection_key"] == "reflection_123"


def test_extract_upgrade_proposal_skips_empty_upgrade():
    text = "4. **Usul upgrade apa** - -"

    proposal = reflection_daemon._proposal_from_reflection_text("reflection_123", text)

    assert proposal is None
