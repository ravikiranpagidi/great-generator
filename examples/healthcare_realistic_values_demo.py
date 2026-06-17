"""Healthcare realistic values demo."""

from great_generator import generate_domain


def main() -> None:
    data = generate_domain("healthcare", scale="tiny", realism="realistic", seed=42)

    print("Patients")
    print(data["patients"][["patient_id", "patient_name", "email", "risk_band"]].head())

    print("\nProviders")
    print(data["providers"][["provider_id", "provider_name", "specialty"]].head())

    print("\nClaims")
    print(data["claims"][["claim_id", "patient_id", "claim_status", "allowed_amount"]].head())


if __name__ == "__main__":
    main()
