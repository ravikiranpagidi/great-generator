"""CDC pipeline demo."""

from great_generator import generate_cdc


def main() -> None:
    cdc = generate_cdc(
        "banking",
        table="customers",
        rows=1000,
        operations=["insert", "update", "delete"],
        late_arrival_rate=0.02,
        duplicate_rate=0.005,
        seed=42,
    )

    print(cdc.head())
    print(cdc["operation"].value_counts())


if __name__ == "__main__":
    main()
