from great_generator import generate_cdc, generate_domain

banking = generate_domain("banking", scale="small", seed=42)
cdc = generate_cdc(
    "banking", table="customers", rows=1_000, late_arrival_rate=0.02, duplicate_rate=0.005, seed=42
)

print(banking["transactions"].head())
print(cdc.head())
