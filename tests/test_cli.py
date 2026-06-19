from great_generator.cli import main


def test_cli_list_domains_outputs_known_domain(capsys):
    exit_code = main(["list-domains"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "banking" in captured.out


def test_cli_describe_outputs_tables(capsys):
    exit_code = main(["describe", "ecommerce"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "customers" in captured.out


def test_cli_generate_writes_output(tmp_path):
    output = tmp_path / "data"

    exit_code = main(
        [
            "gen",
            "banking",
            "--scale",
            "tiny",
            "--seed",
            "42",
            "--out",
            str(output),
            "--format",
            "csv",
        ]
    )

    assert exit_code == 0
    assert (output / "customers" / "customers.csv").exists()
