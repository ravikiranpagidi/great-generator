"""Ecommerce realistic values demo."""

from great_generator import generate_domain


def main() -> None:
    data = generate_domain("ecommerce", scale="tiny", realism="realistic", seed=42)

    print("Customers")
    print(data["customers"][["customer_id", "customer_name", "email"]].head())

    print("\nProducts")
    print(data["products"][["product_id", "product_name", "category", "list_price"]].head())

    print("\nOrders")
    print(data["orders"][["order_id", "customer_id", "order_status", "total_amount"]].head())


if __name__ == "__main__":
    main()
