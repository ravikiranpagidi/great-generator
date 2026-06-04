def test_legacy_enterprise_synth_import_alias_still_works():
    from enterprise_synth.utils.validation import validate_foreign_keys

    import enterprise_synth
    import great_generator

    assert enterprise_synth.generate_domain is great_generator.generate_domain
    assert callable(validate_foreign_keys)
