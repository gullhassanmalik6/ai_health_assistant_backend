"""Seeded AI doctor categories, Cardiologist content, and daily tips."""

from __future__ import annotations

CATEGORIES = [
    {"slug": "general-physician", "name": "General Physician", "tint_key": "blue", "sort_order": 1},
    {"slug": "cardiologist", "name": "Cardiologist", "tint_key": "coral", "sort_order": 2},
    {"slug": "dermatologist", "name": "Dermatologist", "tint_key": "amber", "sort_order": 3},
    {"slug": "neurologist", "name": "Neurologist", "tint_key": "purple", "sort_order": 4},
    {"slug": "orthopedist", "name": "Orthopedist", "tint_key": "teal", "sort_order": 5},
    {"slug": "gynecologist", "name": "Gynecologist", "tint_key": "pink", "sort_order": 6},
    {"slug": "pediatrician", "name": "Pediatrician", "tint_key": "blue", "sort_order": 7},
    {"slug": "psychiatrist", "name": "Psychiatrist", "tint_key": "purple", "sort_order": 8},
    {"slug": "nutritionist", "name": "Nutritionist", "tint_key": "green", "sort_order": 9},
    {"slug": "dentist", "name": "Dentist", "tint_key": "teal", "sort_order": 10},
    {"slug": "ent", "name": "ENT", "tint_key": "amber", "sort_order": 11},
    {"slug": "ophthalmologist", "name": "Ophthalmologist", "tint_key": "blue", "sort_order": 12},
    {"slug": "gastroenterologist", "name": "Gastroenterologist", "tint_key": "green", "sort_order": 13},
    {"slug": "urologist", "name": "Urologist", "tint_key": "teal", "sort_order": 14},
    {"slug": "nephrologist", "name": "Nephrologist", "tint_key": "coral", "sort_order": 15},
    {"slug": "pulmonologist", "name": "Pulmonologist", "tint_key": "pink", "sort_order": 16},
    {"slug": "oncologist", "name": "Oncologist", "tint_key": "purple", "sort_order": 17},
]

CARDIOLOGIST_DESCRIPTION = "Heart health guidance, symptoms, lifestyle & more."

CONCERNS = [
    {
        "id": "chest-pain",
        "category_slug": "cardiologist",
        "title": "Chest Pain",
        "subtitle": "Tightness, heaviness or discomfort",
        "tint_key": "coral",
        "sort_order": 1,
        "symptoms": [
            "Pressure, squeezing or tightness in the chest",
            "Pain spreading to the arm, jaw, neck or back",
            "Shortness of breath",
            "Sweating, nausea or dizziness",
            "Pain that gets worse with activity",
        ],
        "suggested_questions": [
            "My chest feels tight when I climb stairs",
            "Could my chest pain be acid reflux?",
            "When should I worry about chest pain?",
        ],
    },
    {
        "id": "high-blood-pressure",
        "category_slug": "cardiologist",
        "title": "High Blood Pressure",
        "subtitle": "Hypertension and related issues",
        "tint_key": "coral",
        "sort_order": 2,
        "symptoms": [],
        "suggested_questions": [],
    },
    {
        "id": "rapid-heartbeat",
        "category_slug": "cardiologist",
        "title": "Rapid Heartbeat",
        "subtitle": "Palpitations and arrhythmia",
        "tint_key": "coral",
        "sort_order": 3,
        "symptoms": [],
        "suggested_questions": [],
    },
]

HEALTH_TIPS = [
    {
        "id": "heart-health-tips",
        "category_slug": "cardiologist",
        "title": "Heart Health Tips",
        "subtitle": "Daily habits for a strong heart",
        "tint_key": "blue",
        "sort_order": 1,
        "daily_habits": [
            "Walk or exercise 30 minutes most days",
            "Cut back on salt, sugar and fried food",
            "Sleep 7–9 hours a night",
            "Don't smoke, and limit alcohol",
            "Check your blood pressure regularly",
        ],
        "suggested_questions": [
            "What is a heart-healthy breakfast?",
            "How much exercise do I need each week?",
            "How can I lower my cholesterol?",
        ],
    },
]

DAILY_TIPS = [
    "Drink at least 8 glasses of water daily to keep your body hydrated and healthy.",
    "Walk or exercise 30 minutes most days.",
    "Sleep 7–9 hours a night.",
]


def category_ai_title(name: str) -> str:
    return f"AI {name}"


def category_description(slug: str, name: str) -> str:
    if slug == "cardiologist":
        return CARDIOLOGIST_DESCRIPTION
    return f"{name} guidance. Full content is coming soon."
