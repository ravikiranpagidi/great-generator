"""Generate intentionally messy data for data-quality demos."""

from great_generator import generate_domain


def main() -> None:
    data = generate_domain(
        "ecommerce",
        scale="tiny",
        realism="realistic",
        seed=42,
        anomalies={
            "null_rate": 0.03,
            "duplicate_rate": 0.01,
            "late_arrival_rate": 0.02,
            "outlier_rate": 0.005,
            "invalid_status_rate": 0.02,
        },
    )

    print(data["orders"].head())
    print(f"orders rows: {len(data['orders'])}")


if __name__ == "__main__":
    main()
