# AI Doctor — Complete Flutter API Guide

**For:** Humaira / Flutter team  
**Backend:** FastAPI under `/api/v1` · Firebase Auth · PostgreSQL  
**Updated:** 11 October 2026

This is the only document you need to wire the app to the live backend. Interactive try-out: **Swagger** at `/docs` (click Authorize and paste a Bearer token).

---

## 1. What you must never put in the Flutter app

- OpenAI / Gemini keys
- Database passwords / `DATABASE_URL`
- Firebase Admin / service-account JSON / `FIREBASE_PRIVATE_KEY`

Passwords are **never stored** in our database. Firebase owns identity. This API owns health data and authorization.

Login is **email + password only**. Do not call Google, Apple, or guest APIs.

```
Flutter
    → Firebase Authentication   (email + password)
    → HTTPS REST /api/v1        (this backend)
        → PostgreSQL
```

---

## 2. Base URLs

| Environment | Base URL |
| --- | --- |
| Production | `https://aihealthassistantbackend-production.up.railway.app` |
| Local PC | `http://127.0.0.1:8000` |
| Android emulator → your PC | `http://10.0.2.2:8000` |
| iOS simulator | `http://127.0.0.1:8000` |
| API prefix | `/api/v1` |

Examples:

```
https://aihealthassistantbackend-production.up.railway.app/api/v1/auth/login
https://aihealthassistantbackend-production.up.railway.app/api/v1/users/me
https://aihealthassistantbackend-production.up.railway.app/docs
```

---

## 3. Headers, tokens, and identity

### Authenticated requests

```
Authorization: Bearer <Firebase ID token>
Content-Type: application/json
```

Photo upload uses `multipart/form-data` (no JSON body). Still send the Bearer header.

Daily tip (Home): also send

```
X-Timezone: Asia/Karachi
```

(IANA name. If omitted, the server uses UTC.)

### Rules

- **Never send `user_id`** in the body or path to choose whose data to load. The backend reads the user from the token.
- Another user’s resource returns **404** (ownership is hidden).
- Store in **Flutter Secure Storage**: `id_token`, `refresh_token`, `expires_in` (seconds, usually 3600).

### When the token expires

1. `POST /api/v1/auth/refresh` with `{ "refresh_token": "..." }`, **or**
2. `currentUser.getIdToken(true)` from the Firebase Auth SDK  
Then retry the failed request **once**.

| 401 `error_code` | What the app should do |
| --- | --- |
| `AUTH_TOKEN_EXPIRED` | Refresh once, then retry |
| `AUTH_TOKEN_MISSING` / `AUTH_TOKEN_INVALID` | Go to Login |
| `AUTH_SESSION_REVOKED` | Force logout → Login |

**Do not treat 400 as a token problem.** Change Password uses 400 when the current password is wrong, so the user stays signed in.

---

## 4. Standard response envelope

Every success:

```json
{
  "success": true,
  "message": "Login successful.",
  "data": {}
}
```

Every error:

```json
{
  "success": false,
  "message": "Please check the highlighted fields.",
  "error_code": "VALIDATION_ERROR",
  "details": {
    "email": "Enter a valid email address",
    "height": "Height must be between 50 and 250 cm"
  }
}
```

### HTTP status

| HTTP | Meaning |
| --- | --- |
| 200 | OK |
| 201 | Created (register, guest) |
| 400 | Business error (wrong code, wrong current password) |
| 401 | Token missing / invalid / expired / revoked, **or** wrong login password |
| 403 | Authenticated but not allowed (email not verified, guest on change-password) |
| 404 | Not found, or not yours |
| 409 | Email already registered |
| 422 | Validation — show `details` under each field |
| 429 | Rate limited (resend countdown, too many code attempts) |
| 500 | Server error — snackbar |

### Field-level 422

`details` is a **map of JSON field name → one short sentence** (no trailing period). Nested fields use dots (`height.value`).

Show `details[field]` in red under that input. Typing in the field clears its message.

---

## 5. Complete user journeys

### 5.1 First-time user

```
Splash (no token)
    → Onboarding 1 → 2 → 3   (local only, or Skip)
    → Sign Up
    → POST /auth/register     (NO tokens returned)
    → Verify Email            (6-digit code)
    → POST /auth/verify-email
    → Login Screen            (email filled, green “Email verified. Log in to continue.”)
    → POST /auth/login        (now you get tokens)
    → Profile Setup           (first login, profile_setup_seen = false)
    → Save Information or Skip
    → Home Dashboard
```

### 5.2 Returning user, signed out

```
Splash → Login → POST /auth/login
    profile complete        → Home
    profile incomplete
        profile_setup_seen false → Profile Setup
        profile_setup_seen true  → Profile Reminder
```

### 5.3 Returning user, still signed in

```
Splash → GET /auth/session
    401 → refresh or Login
    403 AUTH_EMAIL_NOT_VERIFIED → Verify Email
    profile complete → Home
    else setup not seen → Profile Setup
    else → Profile Reminder
```

### 5.4 Unverified user tries to log in

```
Login (correct password, email not verified)
    → 403 AUTH_EMAIL_NOT_VERIFIED
    → a new code is sent (unless one was sent in the last 60s)
    → Verify Email (show “email isn’t verified yet”)
    → after verify → Login again
```

A **wrong** password on an unverified account is still **401**. Never reveal verification status without the password.

---

## 6. Screen → API map (use this while building)

| Screen | Call | When |
| --- | --- | --- |
| Splash Screen | `GET /api/v1/auth/session` | Every cold start if a token exists |
| Onboarding 1 / 2 / 3 | none | Local. Then Login |
| Sign Up Screen | `POST /api/v1/auth/register` | Create Account |
| Verify Email | `POST /api/v1/auth/verify-email` | Verify Email button |
| Verify Email | `POST /api/v1/auth/resend-verification` | Resend (after countdown) |
| Login Screen | `POST /api/v1/auth/login` | Log In |
| Forgot Password | `POST /api/v1/auth/forgot-password` | Send Reset Link |
| Profile Setup — Save Information | see **§7** below | Exact order |
| Profile Setup — Skip | see **§7** below | Exact order |
| Profile Reminder | `GET /api/v1/profile/completion` | Show % and checklist |
| Home greeting | `GET /api/v1/users/me` | First name |
| Home completion | `GET /api/v1/profile/completion` | Optional |
| Home first 4 categories | `GET /api/v1/categories` | Take `items` 0–3 |
| Home Health Tip of the Day | `GET /api/v1/health-tips/daily` | Header `X-Timezone` |
| Home bell | `GET /api/v1/notifications/unread-count` | Badge. Count is 0 for now |
| AI Doctor Categories | `GET /api/v1/categories` | All items; search locally |
| Category Detail | `GET /api/v1/categories/{slug}` | |
| Concern Detail | `GET /api/v1/concerns/{id}` | |
| Health Tip Detail | `GET /api/v1/health-tips/{id}` | |
| Profile / Health Details | `GET /api/v1/profile` | One read |
| Edit Personal Information | `PATCH /api/v1/profile/personal` + photo | Save Changes |
| Edit Health Information | `PATCH /api/v1/profile/health` | Save Changes |
| Select Allergies / Conditions | none extra | Collect names, send in health PATCH |
| Change Password | `POST /api/v1/auth/change-password` | Update Password |
| Log Out Confirmation | `POST /api/v1/auth/logout` | Then clear storage → Login |
| Privacy / Terms | none | Local placeholder text |
| AI Chat | **none yet** | Mock only. See §16 |

---

## 7. Profile Setup — Save Information and Skip

This is the sequence the backend expects. Do it in this order. Partial data is allowed.

### 7.1 Save Information (user taps the bottom button)

Whatever they filled in is what you send. Skip a call if that section is empty (except step 4 — always send `profile_setup_seen`).

**Step 1 — photo (only if they picked one)**

```
POST /api/v1/profile/photo
Authorization: Bearer <id_token>
Content-Type: multipart/form-data
field name: file
```

JPEG, PNG or WebP, max 5 MB. Response is the full profile (`profile_photo_url`, `profile_photo_expires_at`).

If they did not pick a photo, skip this step.

**Step 2 — personal**

```
PATCH /api/v1/profile/personal
```

```json
{
  "name": "Humaira Khan",
  "date_of_birth": "1998-04-12",
  "gender": "female"
}
```

Send only fields they filled. Omitted fields stay unchanged. Do **not** send email.

- Name: 1–100 characters after trim. Empty/null → 422 `{ "name": "Enter your full name" }`
- `gender`: `female` | `male` | `other`
- `date_of_birth`: `YYYY-MM-DD`, not in the future, age 0–120

**Step 3 — health**

```
PATCH /api/v1/profile/health
```

```json
{
  "height": { "value": 165, "unit": "cm" },
  "weight": { "value": 55, "unit": "kg" },
  "blood_group": "B+",
  "allergies": ["Dust", "Pollen"],
  "conditions": ["Asthma"]
}
```

Send only what they filled.

- Height/weight are objects, never a bare number. App should send `cm` and `kg`.
- Blood group: one of `A+` `A-` `B+` `B-` `AB+` `AB-` `O+` `O-`, or **`unknown`** for “Not sure”.
- `allergies` / `conditions` are **string arrays**. They **replace the whole list**.
- Empty list `[]` clears that list. Omitting the key leaves the list unchanged.
- Max 50 names, 100 characters each. Duplicates are removed case-insensitively.

If height/weight/blood/allergies/conditions are all empty, you may skip this call.

**Step 4 — mark Profile Setup as seen (always)**

```
PATCH /api/v1/users/me
```

```json
{ "profile_setup_seen": true }
```

This is what stops Profile Setup from opening automatically again. Send it on **both** Save and Skip.

**Step 5 — go to Home Dashboard**

Both PATCH personal and PATCH health return the **full profile** (same shape as `GET /profile`), including updated `profile_completed` and `profile_completion_percentage`. You can keep that in memory.

### 7.2 Skip (user taps Skip at the top)

Do **not** save photo / personal / health.

1. `PATCH /api/v1/users/me` `{ "profile_setup_seen": true }`
2. Go to Home Dashboard

Later launches / logins with an incomplete profile will show **Profile Reminder**, not Profile Setup.

### 7.3 Edit screens later (not Setup)

- **Edit Personal Information → Save Changes**  
  `POST /profile/photo` if the photo changed, then `PATCH /profile/personal`.  
  Do **not** send `profile_setup_seen` again (already true).  
  Return to the screen you came from.

- **Edit Health Information → Save Changes**  
  One `PATCH /profile/health` with the current chips (full lists).  
  Return to the screen you came from.

- Clearing a health value: send `"blood_group": null` (or height/weight null).  
- Removing all allergies: `"allergies": []`.

---

## 8. Auth APIs (full contracts)

Public (no Bearer): register, login, verify-email, resend-verification, forgot-password, refresh.  
Bearer required: session, logout, change-password, and everything else below.

### 8.1 POST `/api/v1/auth/register` — Sign Up

**Request**

```json
{
  "email": "humaira.khan@email.com",
  "password": "Sup3rSecret",
  "name": "Humaira Khan"
}
```

Password 8–128 characters. Name is required.

**201 `data` — no tokens, user is not logged in**

```json
{
  "email": "humaira.khan@email.com",
  "verification_required": true,
  "resend_available_in": 60
}
```

Then open Verify Email. Start a 60-second resend countdown.

| Error | HTTP | error_code |
| --- | --- | --- |
| Email already registered | 409 | `AUTH_ACCOUNT_EXISTS` |
| Bad email / short password | 422 | `VALIDATION_ERROR` |

### 8.2 POST `/api/v1/auth/login` — Login

**Request**

```json
{
  "email": "humaira.khan@email.com",
  "password": "Sup3rSecret"
}
```

**200 `data` (verified user)**

```json
{
  "user": {
    "id": "uuid",
    "firebase_uid": "...",
    "email": "humaira.khan@email.com",
    "name": "Humaira Khan",
    "auth_provider": "email",
    "is_guest": false,
    "email_verified": true,
    "onboarding_completed": false,
    "profile_setup_seen": false,
    "profile_completion_percentage": 14,
    "profile_completed": false,
    "created_at": "2026-10-11T10:00:00Z",
    "last_login_at": "2026-10-11T10:00:00Z"
  },
  "tokens": {
    "id_token": "...",
    "refresh_token": "...",
    "expires_in": 3600,
    "token_type": "Bearer"
  },
  "is_guest": false,
  "email_verified": true,
  "profile_completed": false
}
```

Save `tokens`. Route with `profile_completed` and `user.profile_setup_seen`.

**403 — email not verified** (correct password)

```json
{
  "success": false,
  "message": "Verify your email to log in.",
  "error_code": "AUTH_EMAIL_NOT_VERIFIED",
  "details": {
    "email": "humaira.khan@email.com",
    "code_sent": true,
    "resend_available_in": 60
  }
}
```

Open Verify Email. Use `details.resend_available_in` for the countdown. `code_sent` is false if a code was already sent in the last 60 seconds.

**401** `AUTH_INVALID_CREDENTIALS` — wrong email or password. Snackbar. Fields stay filled.

### 8.3 POST `/api/v1/auth/verify-email` — no token

**Request**

```json
{
  "email": "humaira.khan@email.com",
  "code": "123456"
}
```

**200 `data`:** `{ "verified": true }`  
No tokens. Go to Login with the email filled and the green banner. Calling again when already verified is also 200.

| Case | HTTP | error_code | `details.code` |
| --- | --- | --- | --- |
| Wrong code, or unknown email | 400 | `AUTH_CODE_INVALID` | That code isn't right. Check the email and try again. |
| Older than 10 minutes | 400 | `AUTH_CODE_EXPIRED` | This code has expired. Resend the code to get a new one. |
| 5th wrong attempt | 429 | `AUTH_CODE_ATTEMPTS_EXCEEDED` | Too many attempts. Resend the code to get a new one. |

Unknown email looks like a wrong code (cannot be used to discover accounts).

Code rules (backend): 6 digits, hash only stored, 10 minutes, one active code per user, 60 seconds between sends, 5 wrong tries then they must resend.

### 8.4 POST `/api/v1/auth/resend-verification` — no token

**Request:** `{ "email": "humaira.khan@email.com" }`

**200 `data`:** `{ "resend_available_in": 60 }`  
Same answer for unknown or already-verified emails (nothing is emailed to those).

**429** `RATE_LIMITED` `{ "resend_available_in": 42 }` — seconds left. Show the countdown. A new code replaces the old one.

### 8.5 POST `/api/v1/auth/forgot-password` — no token

**Request:** `{ "email": "humaira.khan@email.com" }`

Always **200** with a generic message. Never show “email not found”. User sets the new password from the email link, not in the app.

### 8.6 GET `/api/v1/auth/session` — Bearer — Splash

Same `data` shape as login (usually `tokens` is null).  
Unverified email → 403 `AUTH_EMAIL_NOT_VERIFIED`.

### 8.7 POST `/api/v1/auth/refresh` — no Bearer required on the body

```json
{ "refresh_token": "..." }
```

Returns new `tokens`. Persist them. Unverified → 403.

### 8.8 POST `/api/v1/auth/logout` — Bearer

Then delete local tokens → Login Screen.

### 8.9 POST `/api/v1/auth/change-password` — Bearer — Change Password screen

```json
{
  "current_password": "oldpass123",
  "new_password": "healthy2026"
}
```

**200** — same auth `data` as login, with **new tokens**. Replace stored tokens. Old password stops working.

| Case | HTTP | error_code | details |
| --- | --- | --- | --- |
| Wrong current password | 400 | `AUTH_INVALID_CURRENT_PASSWORD` | `{ "current_password": "Current password is incorrect" }` |
| New == current | 400 | `AUTH_PASSWORD_UNCHANGED` | `{ "new_password": "Choose a password different from your current one" }` |
| Breaks the rule | 422 | `VALIDATION_ERROR` | `{ "new_password": "…" }` |
| Guest / social | 403 | `AUTH_PASSWORD_NOT_SUPPORTED` | — |

The screen may live-check “contains a number”. The API currently requires **8–128 characters only** (product has not turned the number rule on yet). You can still validate a number in the UI.

---

## 9. User APIs

### GET `/api/v1/users/me` — Home greeting, Profile header

```json
{
  "id": "uuid",
  "firebase_uid": "...",
  "email": "humaira.khan@email.com",
  "name": "Humaira Khan",
  "auth_provider": "email",
  "is_guest": false,
  "is_active": true,
  "email_verified": true,
  "onboarding_completed": false,
  "profile_setup_seen": true,
  "profile_completed": false,
  "profile_completion_percentage": 50,
  "created_at": "...",
  "last_login_at": "..."
}
```

Use `name` (split first word) for “Good Morning, Humaira”.

### PATCH `/api/v1/users/me`

```json
{
  "name": "Humaira Khan",
  "profile_setup_seen": true
}
```

Both fields optional. Current app mainly sends `profile_setup_seen: true` after Setup Save/Skip.

`onboarding_completed` still exists but the current app tracks onboarding locally — you do not need it.

### DELETE `/api/v1/users/me`

Deletes the account. **No delete-account screen yet.** Do not call it until that screen exists.

---

## 10. Profile APIs

### GET `/api/v1/profile` — Profile, Health Details, emergency-free summary

```json
{
  "id": "uuid",
  "user_id": "uuid",
  "name": "Humaira Khan",
  "email": "humaira.khan@email.com",
  "gender": "female",
  "date_of_birth": "1998-04-12",
  "height": { "value": 165, "unit": "cm" },
  "weight": { "value": 55, "unit": "kg" },
  "blood_group": "B+",
  "emergency_contact_name": null,
  "emergency_contact_phone": null,
  "profile_photo_url": "https://.../api/v1/profile/photo/file?key=...&exp=...&sig=...",
  "profile_photo_expires_at": "2026-10-11T12:00:00Z",
  "onboarding_completed": false,
  "profile_completed": false,
  "profile_completion_percentage": 83,
  "allergies": [
    {
      "id": "uuid",
      "allergy_name": "Pollen",
      "reaction": null,
      "severity": "unknown",
      "notes": null,
      "created_at": "...",
      "updated_at": "..."
    }
  ],
  "conditions": [
    {
      "id": "uuid",
      "condition_name": "Asthma",
      "diagnosed_date": null,
      "status": null,
      "notes": null,
      "created_at": "...",
      "updated_at": "..."
    }
  ],
  "medications": [],
  "created_at": "...",
  "updated_at": "..."
}
```

Empty fields are `null` or `[]`. Show a dash in the UI, never a made-up value.  
Age on Health Details = calculate from `date_of_birth` in the app.

`profile_photo_url` is a **signed** URL (Image.network can load it). When it expires, call GET profile again.

### PATCH `/api/v1/profile/personal`

See §7. Returns 200 + full profile.

### PATCH `/api/v1/profile/health`

See §7. Returns 200 + full profile. One atomic transaction for the lists.

### POST `/api/v1/profile/photo`

`multipart/form-data`, field **`file`**.  
Wrong type or over 5 MB → 422 `{ "file": "Use a JPG, PNG or WebP image up to 5 MB" }`.  
A new upload replaces the previous file.

### DELETE `/api/v1/profile/photo`

Clears the photo. 200 + full profile. Not an error if there was no photo.

### GET `/api/v1/profile/completion` — Profile Reminder

```json
{
  "percentage": 80,
  "is_complete": false,
  "completed": ["name", "gender", "date_of_birth", "height"],
  "missing": ["weight", "blood_group"]
}
```

Counted fields: `name`, `date_of_birth`, `gender`, `height`, `weight`, `blood_group`.  
Emergency contact, photo, allergies, and conditions do **not** count.  
`blood_group: "unknown"` counts as filled.  
**Do not hardcode this math** — always use this endpoint (or the same fields on GET profile).

### Shared PATCH rules (personal + health)

| Body | Effect |
| --- | --- |
| Field omitted | Unchanged |
| Field sent as `null` | Cleared (except `name`, which 422s) |
| `{}` | Valid, changes nothing |
| Response | 200, full profile, updated completion |

---

## 11. Categories and health tips

All require Bearer. Read-only. Search is done in the app.

`icon_key` and `tint_key` are **names**. Map them to your icons and colors. Never treat them as hex or image URLs.

`tint_key` values: `blue`, `coral`, `amber`, `purple`, `green`, `teal`, `pink`.

Lists come back in `sort_order`. IDs are stable slugs.

### GET `/api/v1/categories` — Home (first 4) and AI Doctor Categories (all)

```json
{
  "items": [
    {
      "slug": "general-physician",
      "name": "General Physician",
      "icon_key": "general-physician",
      "tint_key": "blue",
      "sort_order": 1
    },
    {
      "slug": "cardiologist",
      "name": "Cardiologist",
      "icon_key": "cardiologist",
      "tint_key": "coral",
      "sort_order": 2
    }
  ]
}
```

17 categories, this order:

| # | slug | name | tint_key |
| --- | --- | --- | --- |
| 1 | `general-physician` | General Physician | blue |
| 2 | `cardiologist` | Cardiologist | coral |
| 3 | `dermatologist` | Dermatologist | amber |
| 4 | `neurologist` | Neurologist | purple |
| 5 | `orthopedist` | Orthopedist | teal |
| 6 | `gynecologist` | Gynecologist | pink |
| 7 | `pediatrician` | Pediatrician | blue |
| 8 | `psychiatrist` | Psychiatrist | purple |
| 9 | `nutritionist` | Nutritionist | green |
| 10 | `dentist` | Dentist | teal |
| 11 | `ent` | ENT | amber |
| 12 | `ophthalmologist` | Ophthalmologist | blue |
| 13 | `gastroenterologist` | Gastroenterologist | green |
| 14 | `urologist` | Urologist | teal |
| 15 | `nephrologist` | Nephrologist | coral |
| 16 | `pulmonologist` | Pulmonologist | pink |
| 17 | `oncologist` | Oncologist | purple |

`icon_key` = the slug for every category.

### GET `/api/v1/categories/{slug}` — Category Detail

Unknown slug → 404.

Cardiologist example `data`:

```json
{
  "slug": "cardiologist",
  "name": "Cardiologist",
  "ai_title": "AI Cardiologist",
  "description": "Heart health guidance, symptoms, lifestyle & more.",
  "icon_key": "cardiologist",
  "tint_key": "coral",
  "concerns": [
    { "id": "chest-pain", "title": "Chest Pain", "subtitle": "Tightness, heaviness or discomfort", "tint_key": "coral" },
    { "id": "high-blood-pressure", "title": "High Blood Pressure", "subtitle": "Hypertension and related issues", "tint_key": "coral" },
    { "id": "rapid-heartbeat", "title": "Rapid Heartbeat", "subtitle": "Palpitations and arrhythmia", "tint_key": "coral" }
  ],
  "health_tips": [
    { "id": "heart-health-tips", "title": "Heart Health Tips", "subtitle": "Daily habits for a strong heart", "tint_key": "blue" }
  ]
}
```

Other 16 categories: placeholder description, empty `concerns` and `health_tips` until content is written. Still show the same layout.

### GET `/api/v1/concerns/{id}` — Concern Detail

Unknown id → 404.

Chest Pain `data`:

```json
{
  "id": "chest-pain",
  "category": { "slug": "cardiologist", "ai_title": "AI Cardiologist" },
  "title": "Chest Pain",
  "subtitle": "Tightness, heaviness or discomfort",
  "tint_key": "coral",
  "symptoms": [
    "Pressure, squeezing or tightness in the chest",
    "Pain spreading to the arm, jaw, neck or back",
    "Shortness of breath",
    "Sweating, nausea or dizziness",
    "Pain that gets worse with activity"
  ],
  "suggested_questions": [
    "My chest feels tight when I climb stairs",
    "Could my chest pain be acid reflux?",
    "When should I worry about chest pain?"
  ]
}
```

Tapping a suggested question should open AI Chat with that text as the first message (**chat is mock until the chat API is built**).

### GET `/api/v1/health-tips/{id}` — Health Tip Detail

Same idea as a concern, but `daily_habits` instead of `symptoms`.

Heart Health Tips `data`:

```json
{
  "id": "heart-health-tips",
  "category": { "slug": "cardiologist", "ai_title": "AI Cardiologist" },
  "title": "Heart Health Tips",
  "subtitle": "Daily habits for a strong heart",
  "tint_key": "blue",
  "daily_habits": [
    "Walk or exercise 30 minutes most days",
    "Cut back on salt, sugar and fried food",
    "Sleep 7–9 hours a night",
    "Don't smoke, and limit alcohol",
    "Check your blood pressure regularly"
  ],
  "suggested_questions": [
    "What is a heart-healthy breakfast?",
    "How much exercise do I need each week?",
    "How can I lower my cholesterol?"
  ]
}
```

### GET `/api/v1/health-tips/daily` — Home card

Header: `X-Timezone: Asia/Karachi`

```json
{
  "date": "2026-10-11",
  "text": "Drink at least 8 glasses of water daily to keep your body hydrated and healthy."
}
```

Same tip for everyone that calendar day. Show the full text on Home. Do **not** open a detail screen from this card.

---

## 12. Notifications

### GET `/api/v1/notifications/unread-count`

```json
{ "count": 0 }
```

Use for the Home bell badge. The Notifications screen is not designed yet.

---

## 13. Validation (show in the UI before submit)

| Field | Rule |
| --- | --- |
| Email | Valid email |
| Password | 8–128 characters |
| Confirm password | Must match (app-only) |
| Gender | `female` \| `male` \| `other` |
| Date of birth | `YYYY-MM-DD`, not future, age 0–120 on personal |
| Height | `{ "value": 165, "unit": "cm" }` — cm 50–250, ft 1.5–8.5, in 20–100 |
| Weight | `{ "value": 55, "unit": "kg" }` — kg 2–400, lb 4–880 |
| Blood group | `A+` `A-` `B+` `B-` `AB+` `AB-` `O+` `O-` `unknown` |
| Personal name | 1–100 after trim |
| Allergy / condition name | 1–100, max 50 items |
| Photo | JPEG / PNG / WebP, ≤ 5 MB |

---

## 14. Error codes you will actually handle

| error_code | Typical screen |
| --- | --- |
| `VALIDATION_ERROR` | Any form — use `details` under fields |
| `AUTH_INVALID_CREDENTIALS` | Login snackbar |
| `AUTH_EMAIL_NOT_VERIFIED` | Login → Verify Email |
| `AUTH_ACCOUNT_EXISTS` | Sign Up |
| `AUTH_CODE_INVALID` / `EXPIRED` / `ATTEMPTS_EXCEEDED` | Verify Email |
| `RATE_LIMITED` | Resend countdown |
| `AUTH_INVALID_CURRENT_PASSWORD` | Change Password field |
| `AUTH_PASSWORD_UNCHANGED` | Change Password field |
| `AUTH_TOKEN_EXPIRED` | Silent refresh |
| `AUTH_SESSION_REVOKED` | Force logout |
| `NOT_FOUND` | Unknown category / concern / tip |

---

## 15. Suggested Flutter wiring

```
lib/
  core/
    api/          Dio, base URL, Bearer interceptor, 401 refresh
    auth/         secure storage for tokens
  features/
    splash/
    onboarding/   local only
    login/
    signup/
    verify_email/
    forgot_password/
    profile_setup/   Save = photo → personal → health → profile_setup_seen
    home/            me + categories + daily tip + unread-count
    categories/
    profile/         get profile, patch personal/health, photo, change password
    chat/            mock until chat API exists
```

Packages: `dio`, `flutter_secure_storage`, `firebase_auth`.

Dio interceptor:

1. Attach `Authorization` from secure storage.
2. On 401 `AUTH_TOKEN_EXPIRED`, refresh once and retry.
3. On 401 `AUTH_SESSION_REVOKED`, clear storage and go to Login.
4. On 422, pass `details` to the form.

---

## 16. AI Chat — contract only, do not call

The AI provider is not chosen. These URLs are **not implemented** (they 404). Build the chat UI on mocks. When the API ships it will be:

**POST `/api/v1/chat/conversations`**

```json
{
  "persona": "cardiologist",
  "concern_id": "chest-pain",
  "health_tip_id": null
}
```

- `persona`: `general` (Home / Chat tab) or a category slug  
- Set `concern_id` or `health_tip_id` when opening from those screens  
- Response will include conversation id, title (`AI Cardiologist` / `AI Health Assistant`), and the opening greeting

**POST `/api/v1/chat/conversations/{id}/messages`**

```json
{
  "client_message_id": "7f3c9a2e-0000-4000-8000-000000000000",
  "text": "When should I worry about chest pain?"
}
```

- `client_message_id` is a UUID you generate. Retry with the same id must not create a second message (your “Not sent · Tap to retry”)
- Reply will stream with Server-Sent Events
- Backend will attach the user’s health profile to the AI context
- Always show: “AI guidance only, not a medical diagnosis.”

**GET `/api/v1/chat/conversations/{id}/messages`** — oldest first, cursor pagination.

Always visible note in the chat header: **AI guidance only, not a medical diagnosis.**

---

## 17. Do not call (still on the server, unused by this design)

| Endpoint | Why |
| --- | --- |
| `POST /auth/google`, `/apple`, `/guest` | Email + password only |
| `POST /auth/reset-password` | Reset is from the email link |
| `POST /auth/send-verification`, `GET /auth/verification-status` | Replaced by the 6-digit code |
| `/profile/medications` | No medications screen |
| `PUT/PATCH/DELETE /profile/allergies/{id}` and `/conditions/{id}` | Use the lists on `/profile/health` |
| Emergency contact fields | No screen collects them |
| `onboarding_completed` | App tracks onboarding locally |
| `DELETE /users/me` | No delete-account screen yet |
| `PUT /profile` (legacy full replace) | Use personal + health PATCH |

---

## 18. Quick smoke test (Postman or the app)

1. `GET /health` → `{ "status": "healthy" }`
2. `POST /api/v1/auth/register` → 201, no tokens, check email / server logs for the 6-digit code
3. `POST /api/v1/auth/verify-email` with that code → `{ "verified": true }`
4. `POST /api/v1/auth/login` → save `data.tokens.id_token`
5. `GET /api/v1/users/me` with Bearer
6. Follow **§7 Save Information**
7. `GET /api/v1/profile/completion` → percentage rises; 6 filled fields = 100%
8. `GET /api/v1/categories` → 17 items
9. `GET /api/v1/categories/cardiologist` → Chest Pain + Heart Health Tips
10. `GET /api/v1/health-tips/daily` with `X-Timezone`

---

## 19. Copy-paste: Profile Setup Save Information

```
if photo picked:
    POST /api/v1/profile/photo          multipart file

PATCH /api/v1/profile/personal
    { name?, date_of_birth?, gender? }

PATCH /api/v1/profile/health
    { height?, weight?, blood_group?, allergies?, conditions? }

PATCH /api/v1/users/me
    { "profile_setup_seen": true }

→ Home Dashboard
```

## 20. Copy-paste: Profile Setup Skip

```
PATCH /api/v1/users/me
    { "profile_setup_seen": true }

→ Home Dashboard
```
