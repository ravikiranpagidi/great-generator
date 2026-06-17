"""Banking realistic values demo."""

from great_generator import generate_domain


def main() -> None:
    data = generate_domain("banking", scale="tiny", realism="realistic", seed=42)

    print("Customers")
    print(data["customers"][["customer_id", "customer_name", "email"]].head())

    print("\nAccounts")
    print(data["accounts"][["account_id", "customer_id", "account_type", "balance"]].head())

    print("\nMerchants")
    print(data["merchants"][["merchant_id", "merchant_name", "merchant_category"]].head())


if __name__ == "__main__":
    main()
