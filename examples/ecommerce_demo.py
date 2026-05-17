from enterprise_synth import generate_domain

data = generate_domain("ecommerce", scale="small", seed=42)

print(data["customers"].head())
print(data["orders"].head())
print(data["order_items"].head())
