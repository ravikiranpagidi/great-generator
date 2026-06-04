"""Healthcare domain pack."""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

from great_generator.distributions.time_patterns import (
    random_timestamps_on_dates,
    weighted_calendar_dates,
)
from great_generator.distributions.weighted import normalize
from great_generator.relationships.keys import KeyRegistry
from great_generator.schemas.models import ColumnSpec, DomainSchema, ForeignKey, TableSchema
from great_generator.utils.random import get_rng


def _c(name: str, dtype: str, nullable: bool = False, description: str = "") -> ColumnSpec:
    return ColumnSpec(name=name, dtype=dtype, nullable=nullable, description=description)


def schema() -> DomainSchema:
    tables = {
        "patients": TableSchema(
            name="patients",
            primary_key="patient_id",
            description="Patient master records with demographics and risk indicators.",
            columns=(
                _c("patient_id", "int64"),
                _c("patient_code", "string"),
                _c("age", "int64"),
                _c("gender", "string"),
                _c("region", "string"),
                _c("risk_band", "string"),
                _c("chronic_condition", "bool"),
                _c("enrolled_date", "date"),
            ),
        ),
        "providers": TableSchema(
            name="providers",
            primary_key="provider_id",
            description="Clinicians and care teams with specialty and network status.",
            columns=(
                _c("provider_id", "int64"),
                _c("provider_name", "string"),
                _c("specialty", "string"),
                _c("provider_type", "string"),
                _c("network_status", "string"),
            ),
        ),
        "facilities": TableSchema(
            name="facilities",
            primary_key="facility_id",
            description="Care delivery locations.",
            columns=(
                _c("facility_id", "int64"),
                _c("facility_name", "string"),
                _c("facility_type", "string"),
                _c("region", "string"),
            ),
        ),
        "encounters": TableSchema(
            name="encounters",
            primary_key="encounter_id",
            foreign_keys=(
                ForeignKey("patient_id", "patients", "patient_id"),
                ForeignKey("provider_id", "providers", "provider_id"),
                ForeignKey("facility_id", "facilities", "facility_id"),
            ),
            description="Visits, admissions, and care interactions.",
            columns=(
                _c("encounter_id", "int64"),
                _c("patient_id", "int64"),
                _c("provider_id", "int64"),
                _c("facility_id", "int64"),
                _c("encounter_ts", "datetime64[ns]"),
                _c("event_date", "date"),
                _c("encounter_type", "string"),
                _c("diagnosis_group", "string"),
                _c("encounter_status", "string"),
                _c("billed_amount", "float64"),
            ),
        ),
        "claims": TableSchema(
            name="claims",
            primary_key="claim_id",
            foreign_keys=(
                ForeignKey("encounter_id", "encounters", "encounter_id"),
                ForeignKey("patient_id", "patients", "patient_id"),
                ForeignKey("provider_id", "providers", "provider_id"),
            ),
            description="Insurance claims derived from encounters.",
            columns=(
                _c("claim_id", "int64"),
                _c("encounter_id", "int64"),
                _c("patient_id", "int64"),
                _c("provider_id", "int64"),
                _c("claim_ts", "datetime64[ns]"),
                _c("claim_status", "string"),
                _c("allowed_amount", "float64"),
                _c("paid_amount", "float64"),
                _c("denial_reason", "string", nullable=True),
            ),
        ),
        "prescriptions": TableSchema(
            name="prescriptions",
            primary_key="prescription_id",
            foreign_keys=(
                ForeignKey("patient_id", "patients", "patient_id"),
                ForeignKey("provider_id", "providers", "provider_id"),
            ),
            description="Medication orders with refill and chronic-care behavior.",
            columns=(
                _c("prescription_id", "int64"),
                _c("patient_id", "int64"),
                _c("provider_id", "int64"),
                _c("medication_class", "string"),
                _c("prescribed_date", "date"),
                _c("days_supply", "int64"),
                _c("refill_count", "int64"),
                _c("drug_cost", "float64"),
            ),
        ),
        "lab_results": TableSchema(
            name="lab_results",
            primary_key="lab_result_id",
            foreign_keys=(
                ForeignKey("encounter_id", "encounters", "encounter_id"),
                ForeignKey("patient_id", "patients", "patient_id"),
            ),
            description="Lab observations connected to encounters.",
            columns=(
                _c("lab_result_id", "int64"),
                _c("encounter_id", "int64"),
                _c("patient_id", "int64"),
                _c("lab_test", "string"),
                _c("result_value", "float64"),
                _c("normal_range", "string"),
                _c("abnormal_flag", "bool"),
                _c("result_ts", "datetime64[ns]"),
            ),
        ),
    }
    return DomainSchema(
        name="healthcare",
        tables=tables,
        description="A healthcare domain with patients, providers, encounters, claims, prescriptions, and labs.",
        behaviors=(
            "Chronic and high-risk patients generate more encounters",
            "Encounter type influences diagnosis group and billed amount",
            "Claims can be paid, pending, denied, or adjusted",
            "Lab abnormality is more common for high-risk and chronic patients",
        ),
    )


def _base_or_sample(keys: np.ndarray, rows: int, rng: np.random.Generator) -> np.ndarray:
    if rows <= 0:
        return np.array([], dtype=np.int64)
    if len(keys) == 0:
        return np.array([], dtype=np.int64)
    if rows <= len(keys):
        return rng.choice(keys, size=rows, replace=False)
    extras = rng.choice(keys, size=rows - len(keys), replace=True)
    values = np.concatenate([keys, extras])
    rng.shuffle(values)
    return values


def generate_pandas(
    row_counts: Mapping[str, int], seed: int | None = None
) -> dict[str, pd.DataFrame]:
    registry = KeyRegistry()

    patient_rng = get_rng(seed, "healthcare.patients")
    patient_count = row_counts["patients"]
    patient_ids = np.arange(1, patient_count + 1, dtype=np.int64)
    risk_bands = patient_rng.choice(
        ["low", "moderate", "high"], patient_count, p=[0.62, 0.28, 0.10]
    )
    chronic = patient_rng.random(patient_count) < np.where(risk_bands == "high", 0.48, 0.16)
    patients = pd.DataFrame(
        {
            "patient_id": patient_ids,
            "patient_code": [f"PAT{value:08d}" for value in patient_ids],
            "age": patient_rng.integers(1, 91, patient_count),
            "gender": patient_rng.choice(["F", "M", "X"], patient_count, p=[0.51, 0.48, 0.01]),
            "region": patient_rng.choice(
                ["northeast", "south", "midwest", "west"],
                patient_count,
                p=[0.22, 0.36, 0.20, 0.22],
            ),
            "risk_band": risk_bands,
            "chronic_condition": chronic,
            "enrolled_date": weighted_calendar_dates(
                patient_rng,
                patient_count,
                start="2019-01-01",
                end="2025-12-31",
                weekend_multiplier=1.0,
                holiday_multiplier=1.0,
            ).date,
        }
    )
    registry.register("patients", patient_ids)

    provider_rng = get_rng(seed, "healthcare.providers")
    provider_count = row_counts["providers"]
    provider_ids = np.arange(1, provider_count + 1, dtype=np.int64)
    specialties = provider_rng.choice(
        ["primary_care", "cardiology", "endocrinology", "orthopedics", "behavioral_health"],
        provider_count,
        p=[0.46, 0.14, 0.12, 0.16, 0.12],
    )
    providers = pd.DataFrame(
        {
            "provider_id": provider_ids,
            "provider_name": [f"Provider {value:05d}" for value in provider_ids],
            "specialty": specialties,
            "provider_type": provider_rng.choice(
                ["physician", "nurse_practitioner", "physician_assistant"],
                provider_count,
                p=[0.62, 0.25, 0.13],
            ),
            "network_status": provider_rng.choice(
                ["in_network", "out_of_network"], provider_count, p=[0.88, 0.12]
            ),
        }
    )
    registry.register("providers", provider_ids)

    facility_rng = get_rng(seed, "healthcare.facilities")
    facility_count = row_counts["facilities"]
    facility_ids = np.arange(1, facility_count + 1, dtype=np.int64)
    facilities = pd.DataFrame(
        {
            "facility_id": facility_ids,
            "facility_name": [f"Facility {value:04d}" for value in facility_ids],
            "facility_type": facility_rng.choice(
                ["clinic", "hospital", "urgent_care", "lab"],
                facility_count,
                p=[0.48, 0.24, 0.18, 0.10],
            ),
            "region": facility_rng.choice(
                ["northeast", "south", "midwest", "west"], facility_count
            ),
        }
    )
    registry.register("facilities", facility_ids)

    encounter_rng = get_rng(seed, "healthcare.encounters")
    encounter_count = row_counts["encounters"]
    encounter_ids = np.arange(1, encounter_count + 1, dtype=np.int64)
    patient_weights = (
        patients["risk_band"].map({"low": 0.7, "moderate": 1.2, "high": 2.4}).to_numpy()
    )
    patient_weights = patient_weights * np.where(patients["chronic_condition"].to_numpy(), 1.8, 1.0)
    encounter_patient_ids = registry.sample(
        "patients", encounter_count, encounter_rng, normalize(patient_weights)
    )
    encounter_types = encounter_rng.choice(
        ["office_visit", "telehealth", "emergency", "inpatient", "preventive"],
        encounter_count,
        p=[0.46, 0.18, 0.12, 0.08, 0.16],
    )
    diagnosis_groups = np.where(
        encounter_types == "preventive",
        "wellness",
        encounter_rng.choice(
            ["cardio", "diabetes", "respiratory", "musculoskeletal", "behavioral"],
            encounter_count,
            p=[0.24, 0.18, 0.20, 0.24, 0.14],
        ),
    )
    encounter_dates = weighted_calendar_dates(
        encounter_rng, encounter_count, weekend_multiplier=0.55, holiday_multiplier=0.80
    )
    encounter_ts = random_timestamps_on_dates(
        encounter_rng, encounter_dates, business_hours_bias=0.82
    )
    amount_base = pd.Series(encounter_types).map(
        {
            "office_visit": 180,
            "telehealth": 95,
            "emergency": 1350,
            "inpatient": 8500,
            "preventive": 140,
        }
    )
    billed_amount = np.round(
        amount_base.to_numpy() * encounter_rng.lognormal(0.0, 0.35, encounter_count), 2
    )
    encounters = pd.DataFrame(
        {
            "encounter_id": encounter_ids,
            "patient_id": encounter_patient_ids,
            "provider_id": registry.sample("providers", encounter_count, encounter_rng),
            "facility_id": registry.sample("facilities", encounter_count, encounter_rng),
            "encounter_ts": encounter_ts,
            "event_date": encounter_ts.dt.date,
            "encounter_type": encounter_types,
            "diagnosis_group": diagnosis_groups,
            "encounter_status": encounter_rng.choice(
                ["completed", "cancelled", "no_show"], encounter_count, p=[0.91, 0.05, 0.04]
            ),
            "billed_amount": billed_amount,
        }
    )
    registry.register("encounters", encounter_ids)

    claim_rng = get_rng(seed, "healthcare.claims")
    claim_count = row_counts["claims"]
    claim_ids = np.arange(1, claim_count + 1, dtype=np.int64)
    claim_encounter_ids = _base_or_sample(encounter_ids, claim_count, claim_rng)
    claim_base = encounters.set_index("encounter_id").loc[claim_encounter_ids]
    claim_status = claim_rng.choice(
        ["paid", "pending", "denied", "adjusted"], claim_count, p=[0.76, 0.11, 0.07, 0.06]
    )
    allowed_amount = np.round(
        claim_base["billed_amount"].to_numpy() * claim_rng.uniform(0.58, 0.94, claim_count), 2
    )
    paid_amount = np.where(
        claim_status == "denied",
        0.0,
        np.round(allowed_amount * claim_rng.uniform(0.72, 0.98, claim_count), 2),
    )
    claims = pd.DataFrame(
        {
            "claim_id": claim_ids,
            "encounter_id": claim_encounter_ids,
            "patient_id": claim_base["patient_id"].to_numpy(),
            "provider_id": claim_base["provider_id"].to_numpy(),
            "claim_ts": pd.to_datetime(claim_base["encounter_ts"].to_numpy())
            + pd.to_timedelta(claim_rng.integers(1, 21, claim_count), unit="D"),
            "claim_status": claim_status,
            "allowed_amount": allowed_amount,
            "paid_amount": paid_amount,
            "denial_reason": np.where(
                claim_status == "denied",
                claim_rng.choice(["coverage", "coding", "eligibility"], claim_count),
                None,
            ),
        }
    )

    rx_rng = get_rng(seed, "healthcare.prescriptions")
    rx_count = row_counts["prescriptions"]
    rx_ids = np.arange(1, rx_count + 1, dtype=np.int64)
    rx_patient_ids = registry.sample("patients", rx_count, rx_rng, normalize(patient_weights))
    med_classes = rx_rng.choice(
        ["antihypertensive", "diabetes", "antibiotic", "statin", "mental_health"],
        rx_count,
        p=[0.24, 0.18, 0.22, 0.22, 0.14],
    )
    days_supply = rx_rng.choice([7, 14, 30, 90], rx_count, p=[0.08, 0.12, 0.58, 0.22])
    prescriptions = pd.DataFrame(
        {
            "prescription_id": rx_ids,
            "patient_id": rx_patient_ids,
            "provider_id": registry.sample("providers", rx_count, rx_rng),
            "medication_class": med_classes,
            "prescribed_date": weighted_calendar_dates(rx_rng, rx_count).date,
            "days_supply": days_supply,
            "refill_count": np.where(days_supply >= 30, rx_rng.integers(0, 5, rx_count), 0),
            "drug_cost": np.round(rx_rng.lognormal(4.5, 0.55, rx_count), 2),
        }
    )

    lab_rng = get_rng(seed, "healthcare.lab_results")
    lab_count = row_counts["lab_results"]
    lab_ids = np.arange(1, lab_count + 1, dtype=np.int64)
    lab_encounter_ids = _base_or_sample(encounter_ids, lab_count, lab_rng)
    lab_base = encounters.set_index("encounter_id").loc[lab_encounter_ids]
    lab_tests = lab_rng.choice(
        ["a1c", "ldl", "cbc", "creatinine", "troponin"],
        lab_count,
        p=[0.20, 0.24, 0.32, 0.18, 0.06],
    )
    abnormal_probability = np.where(
        lab_base["diagnosis_group"].to_numpy() == "wellness", 0.08, 0.22
    )
    abnormal = lab_rng.random(lab_count) < abnormal_probability
    lab_results = pd.DataFrame(
        {
            "lab_result_id": lab_ids,
            "encounter_id": lab_encounter_ids,
            "patient_id": lab_base["patient_id"].to_numpy(),
            "lab_test": lab_tests,
            "result_value": np.round(lab_rng.normal(100, np.where(abnormal, 35, 12), lab_count), 2),
            "normal_range": ["varies"] * lab_count,
            "abnormal_flag": abnormal,
            "result_ts": pd.to_datetime(lab_base["encounter_ts"].to_numpy())
            + pd.to_timedelta(lab_rng.integers(1, 72, lab_count), unit="h"),
        }
    )

    return {
        "patients": patients,
        "providers": providers,
        "facilities": facilities,
        "encounters": encounters,
        "claims": claims,
        "prescriptions": prescriptions,
        "lab_results": lab_results,
    }
