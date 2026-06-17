"""Curated business reference values used by realistic generation mode."""

from __future__ import annotations

BANK_MERCHANTS = [
    "Amazon",
    "Walmart",
    "Target",
    "Costco",
    "Starbucks",
    "Uber",
    "Netflix",
    "Apple",
    "Shell",
    "Home Depot",
    "Whole Foods",
    "Delta Air Lines",
    "Airbnb",
    "Best Buy",
    "Walgreens",
]

BANK_ACCOUNT_TYPES = [
    "Checking",
    "Savings",
    "Credit Card",
    "Auto Loan",
    "Mortgage",
    "Personal Loan",
    "Business Checking",
]

TRANSACTION_TYPES = [
    "Debit Card Purchase",
    "ACH Transfer",
    "Mobile Deposit",
    "ATM Withdrawal",
    "Wire Transfer",
    "Bill Payment",
    "Payroll Deposit",
]

PRODUCT_NAMES = [
    "Wireless Mouse",
    "Bluetooth Headphones",
    "Running Shoes",
    "Coffee Maker",
    "Laptop Backpack",
    "Smart Watch",
    "Office Chair",
    "Water Bottle",
    "Mechanical Keyboard",
    "Desk Lamp",
    "Yoga Mat",
    "Noise-Cancelling Earbuds",
]

ORDER_STATUSES = [
    "Pending",
    "Processing",
    "Shipped",
    "Delivered",
    "Returned",
    "Cancelled",
]

HEALTHCARE_DEPARTMENTS = [
    "Primary Care",
    "Cardiology",
    "Radiology",
    "Orthopedics",
    "Emergency",
    "Pediatrics",
    "Oncology",
    "Neurology",
]

CLAIM_STATUSES = [
    "Approved",
    "Denied",
    "Pending",
    "In Review",
    "Paid",
    "Adjusted",
]

POLICY_TYPES = [
    "Auto",
    "Home",
    "Life",
    "Health",
    "Renters",
    "Commercial Property",
]

CLAIM_TYPES = [
    "Collision",
    "Property Damage",
    "Medical",
    "Theft",
    "Liability",
    "Weather",
]

TELECOM_PLAN_NAMES = [
    "Starter 5G",
    "Family Unlimited",
    "Business Connect",
    "International Roam",
    "Fiber Plus",
]

MANUFACTURING_PRODUCT_NAMES = [
    "Control Module",
    "Hydraulic Pump",
    "Sensor Assembly",
    "Aerospace Bracket",
    "Power Supply Unit",
]

LOGISTICS_CARRIERS = [
    "DHL",
    "FedEx",
    "UPS",
    "Maersk",
    "Ryder",
    "XPO Logistics",
]

ENERGY_RATE_PLANS = [
    "Residential Time of Use",
    "Commercial Demand",
    "Solar Net Metering",
    "Industrial Fixed",
]

HOSPITALITY_PROPERTY_NAMES = [
    "Harbor Grand Hotel",
    "Summit Suites",
    "Lakeside Inn",
    "Metro Plaza",
    "Garden Court Resort",
]

DEVICE_MODELS = [
    "iPhone 15",
    "Galaxy S24",
    "Pixel Pro",
    "ThinkPad X1",
    "Surface Laptop",
]

AUTO_MODELS = [
    "Apex EV",
    "Summit SUV",
    "Harbor Sedan",
    "Ranger Truck",
    "Metro Hybrid",
]

SAAS_FEATURE_NAMES = [
    "Workflow Automation",
    "Advanced Reporting",
    "Single Sign-On",
    "Audit Logs",
    "API Access",
    "Data Export",
]

PUBLIC_PROGRAM_NAMES = [
    "Housing Assistance",
    "Small Business Grant",
    "Public Health Outreach",
    "Workforce Training",
    "Student Aid",
]

MEDIA_CONTENT_TITLES = [
    "The Last Signal",
    "City of Glass",
    "Frontier Kitchen",
    "Deep Space Atlas",
    "Match Day Live",
]

REFERENCE_VALUES_BY_FIELD = {
    "merchant_name": BANK_MERCHANTS,
    "account_type": BANK_ACCOUNT_TYPES,
    "transaction_type": TRANSACTION_TYPES,
    "product_name": PRODUCT_NAMES,
    "order_status": ORDER_STATUSES,
    "claim_status": CLAIM_STATUSES,
    "policy_type": POLICY_TYPES,
    "claim_type": CLAIM_TYPES,
    "department": HEALTHCARE_DEPARTMENTS,
    "carrier": LOGISTICS_CARRIERS,
    "plan_name": TELECOM_PLAN_NAMES,
    "rate_plan_name": ENERGY_RATE_PLANS,
    "property_name": HOSPITALITY_PROPERTY_NAMES,
    "feature_name": SAAS_FEATURE_NAMES,
    "program_name": PUBLIC_PROGRAM_NAMES,
    "content_title": MEDIA_CONTENT_TITLES,
    "content_name": MEDIA_CONTENT_TITLES,
    "model_name": AUTO_MODELS,
    "model": DEVICE_MODELS,
    "carrier_name": LOGISTICS_CARRIERS,
    "shipper_name": [
        "Northstar Foods",
        "Harbor Retail",
        "Apex Manufacturing",
        "Metro Medical",
        "Summit Wholesale",
    ],
    "supplier_name": [
        "Aster Components",
        "Keystone Metals",
        "Nimbus Electronics",
        "Harbor Plastics",
        "Northstar Supply",
    ],
}
