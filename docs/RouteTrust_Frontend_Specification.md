# RouteTrust — Frontend Specification & Design System Architecture

**Document Version:** 1.0.0  
**Target Audience:** Frontend Engineers, UI/UX Designers, Product Architects  
**Scope:** RouteTrust Responsive Web Application (Streamlit / Modern Web SPA Client), API Gateway Integration, Design System Tokens & Component Specifications  
**Author:** Senior UI/UX Designer & Frontend Architect  

---

## 1. Executive Summary & Design Vision

RouteTrust is a probabilistic transit reliability and decision-support engine. Unlike legacy transit applications (Google Maps, Citymapper, Transit) that provide deterministic departure estimates and obscure delay uncertainty, RouteTrust models the full conditional delay distribution ($Q_{0.10}, Q_{0.50}, Q_{0.90}$) to answer the rider's fundamental question: **"What time must I leave to arrive on schedule, with a stated level of confidence?"**

### 1.1 Core UI/UX Objectives
1. **Uncompromising Cognitive Clarity:** A commuter under time pressure requires an instant, unambiguous answer. The "Leave-By Time" must command the visual hierarchy, supported by clear plain-language confidence framing.
2. **Honest Calibration & Transparency:** Uncertainty is not hidden behind a spinner or fine print. Reliability grades ($A$ through $F$), early-departure guards, and historical weather fallbacks are displayed inline as primary interface elements.
3. **Ergonomic Speed & Frictionless Input:** Fast route selection, predictive time pickers, and intuitive risk tolerance steppers allow commuters to compute decisions in fewer than 3 taps/clicks.
4. **Resilient State Presentation:** Seamlessly communicate network anomalies, fallback modes, and low-sample warnings without jarring layout shifts or obscure technical jargon.

---

## 2. Design System Tokens & Foundations

### 2.1 Color Palette & Semantic Tokens

The color system is calibrated for high accessibility (WCAG 2.1 Level AAA compliance for text contrast) across both light and dark operational contexts, evoking precision, transit reliability, and safety.

```
+-----------------------------------------------------------------------------------------+
|                                    COLOR TOKEN MATRIX                                   |
+-------------------+--------------------+------------------------+-----------------------+
|  Primary Brand    |  Slate Neutral     |  Reliability Grades    |  System Alerts        |
|  Navy: #0F172A    |  Surface: #F8FAFC  |  Grade A: #059669 (95%)|  Success: #10B981     |
|  Blue: #2563EB    |  Border:  #E2E8F0  |  Grade B: #2563EB (90%)|  Warning: #F59E0B     |
|  Cyan: #0EA5E9    |  Muted:   #64748B  |  Grade C: #D97706 (80%)|  Danger:  #EF4444     |
|  Teal: #0D9488    |  Text:    #0F172A  |  Grade D: #EA580C (70%)|  Info:    #3B82F6     |
|                   |                    |  Grade F: #DC2626 (<60%)                       |
+-------------------+--------------------+------------------------+-----------------------+
```

#### Complete Palette Specification
| Category | Token Name | Hex Code | RGB | Contrast Ratio (vs White) | Purpose / Usage |
|---|---|---|---|---|---|
| **Primary Brand** | `--color-brand-primary` | `#2563EB` | `37, 99, 235` | 4.6:1 (AA) | Primary CTA buttons, active state indicators, branding |
| | `--color-brand-hover` | `#1D4ED8` | `29, 78, 216` | 6.2:1 (AAA Large) | Button hover states, focused outlines |
| | `--color-brand-active` | `#1E40AF` | `30, 64, 175` | 8.3:1 (AAA) | Button active/pressed states |
| | `--color-brand-subtle` | `#EFF6FF` | `239, 246, 255`| 1.1:1 | Active selection backgrounds, pill badge tints |
| **Dark Accents** | `--color-slate-900` | `#0F172A` | `15, 23, 42` | 16.1:1 (AAA) | Primary headlines, hero decision text, dark badges |
| | `--color-slate-800` | `#1E293B` | `30, 41, 59` | 13.2:1 (AAA) | High-emphasis body text, dark card containers |
| | `--color-slate-700` | `#334155` | `51, 65, 85` | 9.6:1 (AAA) | Secondary headings, card titles, icon fills |
| **Neutral Grays** | `--color-slate-500` | `#64748B` | `100, 116, 139`| 4.6:1 (AA) | Secondary subtitles, helper text, input labels |
| | `--color-slate-400` | `#94A3B8` | `148, 163, 184`| 2.6:1 | Placeholder text, disabled icon fills |
| | `--color-slate-300` | `#CBD5E1` | `203, 213, 225`| 1.6:1 | Default input borders, subtle divider rules |
| | `--color-slate-200` | `#E2E8F0` | `226, 232, 240`| 1.3:1 | Card borders, secondary button borders, grid lines |
| | `--color-slate-100` | `#F1F5F9` | `241, 245, 249`| 1.1:1 | Input background default, hover card fills |
| | `--color-slate-50` | `#F8FAFC` | `248, 250, 252`| 1.0:1 | Primary page canvas background |
| **Reliability Grades** | `--color-grade-a` | `#059669` | `5, 150, 105` | 4.8:1 (AA) | Grade A (Spread $\le 0.15$), ultra-reliable status |
| | `--color-grade-b` | `#2563EB` | `37, 99, 235` | 4.6:1 (AA) | Grade B (Spread $0.15-0.30$), highly predictable |
| | `--color-grade-c` | `#D97706` | `217, 119, 6` | 4.5:1 (AA) | Grade C (Spread $0.30-0.50$), moderate variance |
| | `--color-grade-d` | `#EA580C` | `234, 88, 12` | 4.5:1 (AA) | Grade D (Spread $0.50-0.75$), high volatility |
| | `--color-grade-f` | `#DC2626` | `220, 38, 38` | 4.7:1 (AA) | Grade F (Spread $> 0.75$), extreme unreliability |
| **System States** | `--color-status-success`| `#10B981` | `16, 185, 129` | 4.5:1 (AA) | Normal timing, guard verified, model online |
| | `--color-status-warning`| `#F59E0B` | `245, 158, 11` | 4.5:1 (AA) | Weather fallback active, low-sample flag ($N<30$) |
| | `--color-status-danger` | `#EF4444` | `239, 68, 68` | 4.5:1 (AA) | Past arrival time, network timeout, 5xx failures |
| | `--color-status-info` | `#3B82F6` | `59, 130, 246` | 4.5:1 (AA) | Early departure guard advisory notification |

---

### 2.2 Typography Scale & Rules

RouteTrust relies on modern, geometric, yet highly legible sans-serif typography designed for screen interfaces and tabular data rendering.

* **Primary Font Family:** `Inter`, `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`
* **Monospace / Numerical Family:** `JetBrains Mono`, `SF Mono`, `Menlo`, monospace (used for arrival/departure timestamps, confidence intervals, and metrics)

```
Scale Ladder:
[Display]  36px / 44px - Bold (700)      --> Hero Leave-By Time
[H1]       28px / 36px - Bold (700)      --> Page Header & View Titles
[H2]       20px / 28px - SemiBold (600)  --> Card Section Titles & Modals
[H3]       16px / 24px - SemiBold (600)  --> Subsection Headings, Fieldsets
[Body-Lg]  16px / 24px - Regular (400)   --> Hero Descriptions, Primary Inputs
[Body-Md]  14px / 20px - Regular (400)   --> Standard Body, Dropdown Selections
[Body-Sm]  12px / 16px - Medium (500)    --> Labels, Tooltips, Metric Badges
[Micro]    11px / 14px - Regular (400)   --> Legal Disclaimer, Timestamp Audit
```

#### Detailed Typography Spec Table
| Style | Size (px/rem) | Line Height | Weight | Letter Spacing | Target Usage |
|---|---|---|---|---|---|
| `display-hero` | `36px` / `2.25rem` | `44px` (1.22) | 700 (Bold) | `-0.025em` | Hero Leave-By Departure Recommendation |
| `display-lg` | `30px` / `1.875rem` | `38px` (1.26) | 700 (Bold) | `-0.02em` | Reliability Grade Hero Letter (`A` - `F`) |
| `heading-1` | `24px` / `1.5rem` | `32px` (1.33) | 700 (Bold) | `-0.015em` | Main View Heading ("Plan Commute", "Diagnostics") |
| `heading-2` | `20px` / `1.25rem` | `28px` (1.40) | 600 (SemiBold) | `-0.01em` | Card Titles ("Journey Risk Profile", "Model Calibration") |
| `heading-3` | `16px` / `1.0rem` | `24px` (1.50) | 600 (SemiBold) | `0em` | Form Fieldset Titles, Component Group Labels |
| `body-default` | `14px` / `0.875rem` | `20px` (1.43) | 400 (Regular) | `0em` | Form inputs, standard body paragraphs, table text |
| `body-medium` | `14px` / `0.875rem` | `20px` (1.43) | 500 (Medium) | `0em` | Selectable list items, tab headers, interactive text |
| `caption` | `12px` / `0.75rem` | `16px` (1.33) | 500 (Medium) | `+0.01em` | Form labels, input helper text, status badges |
| `mono-numbers` | `14px` / `0.875rem` | `20px` (1.43) | 500 (Medium) | `+0.02em` | Delay seconds ($+480s$), confidence intervals, clock times |

---

### 2.3 Spacing, Grid & Elevation Rules

The design system operates on an **8-point spatial grid system**, ensuring consistent rhythm, vertical cadence, and responsive predictability.

```
Spacing Scale:
4px (xxs) | 8px (xs) | 12px (sm) | 16px (md) | 24px (lg) | 32px (xl) | 48px (2xl) | 64px (3xl)
```

#### Spacing Tokens Table
| Token | Pixel Value | Typical Application |
|---|---|---|
| `--space-xxs` | `4px` | Icon-to-text inline gap, input internal border padding |
| `--space-xs` | `8px` | Gap between label and input, badge internal padding, tag spacing |
| `--space-sm` | `12px` | Compact table cell padding, input vertical padding, sub-card gap |
| `--space-md` | `16px` | Standard card internal padding, form row spacing, button padding |
| `--space-lg` | `24px` | Card-to-card margin, modal header-to-body spacing, grid column gutter |
| `--space-xl` | `32px` | Section-to-section layout gap, hero module margin |
| `--space-2xl` | `48px` | Major viewport container padding, desktop header vertical gap |
| `--space-3xl` | `64px` | Empty state vertical spacing, outer hero layout padding |

#### Elevation & Shadows
* **`--shadow-none`:** `none` (flat borders, inputs)
* **`--shadow-sm`:** `0 1px 2px 0 rgba(15, 23, 42, 0.05)` (subtle buttons, interactive tags)
* **`--shadow-md`:** `0 4px 6px -1px rgba(15, 23, 42, 0.08), 0 2px 4px -2px rgba(15, 23, 42, 0.05)` (cards, dropdown lists)
* **`--shadow-lg`:** `0 10px 15px -3px rgba(15, 23, 42, 0.10), 0 4px 6px -4px rgba(15, 23, 42, 0.05)` (hero decision cards, floating bottom bar)
* **`--shadow-modal`:** `0 20px 25px -5px rgba(15, 23, 42, 0.15), 0 8px 10px -6px rgba(15, 23, 42, 0.10)` (modal dialogs, alerts)

#### Border Radius Scale
* **`--radius-sm` (`4px`):** Inline tags, table row highlights, micro tooltips
* **`--radius-md` (`8px`):** Input fields, standard buttons, select dropdowns
* **`--radius-lg` (`12px`):** Cards, diagnostic graphs, modal dialogs
* **`--radius-pill` (`9999px`):** Status pills, reliability grade badges, segmented tabs

---

## 3. UI Component Style Guide & States

### 3.1 Buttons (`<Button>`)

Buttons trigger calculations, open diagnostic inspectors, or toggle parameter states.

```
+-----------------------------------------------------------------------------------------+
|                                    BUTTON STATES SPEC                                   |
+-------------------+--------------------+------------------------+-----------------------+
|  Primary (Default)|  Primary (Hover)   |  Primary (Active)      |  Disabled             |
|  BG: #2563EB      |  BG: #1D4ED8       |  BG: #1E40AF           |  BG: #E2E8F0          |
|  Text: #FFFFFF    |  Text: #FFFFFF     |  Text: #FFFFFF         |  Text: #94A3B8        |
|  Shadow: sm       |  Shadow: md        |  Shadow: none          |  Cursor: not-allowed  |
+-------------------+--------------------+------------------------+-----------------------+
```

* **Primary Button:**
  * Background: `#2563EB` | Text: `#FFFFFF` | Font: `14px`, 600 weight
  * Padding: `10px 20px` (`--space-sm` / `--space-md`) | Radius: `8px` (`--radius-md`)
  * Hover: Background `#1D4ED8`, subtle upward translation (`transform: translateY(-1px)`)
  * Focus: `outline: 2px solid #2563EB; outline-offset: 2px;`
  * Active: Background `#1E40AF`, `transform: translateY(0)`
  * Disabled: Background `#E2E8F0`, Text `#94A3B8`, Cursor `not-allowed`

* **Secondary / Outline Button:**
  * Background: `#FFFFFF` | Border: `1px solid #CBD5E1` | Text: `#1E293B`
  * Hover: Background `#F8FAFC`, Border `#94A3B8`
  * Focus: `outline: 2px solid #2563EB; outline-offset: 2px;`

* **Ghost / Subdued Button (Diagnostics / Inspect):**
  * Background: `transparent` | Border: `none` | Text: `#2563EB`
  * Hover: Background `#EFF6FF`, Text `#1D4ED8`

* **Loading / Spinner Button:**
  * Pointer-events disabled. Label hidden or paired with a 16px CSS rotating spinner (`border: 2px solid #FFFFFF; border-top-color: transparent; border-radius: 50%; animation: spin 0.8s linear infinite;`).

---

### 3.2 Form Inputs & Interactive Controls

#### Text & Select Inputs (`<Input>`, `<Select>`)
* **Height:** `44px` (touch-friendly standard)
* **Base Styles:**
  * Background: `#FFFFFF`
  * Border: `1px solid #CBD5E1`
  * Border Radius: `8px`
  * Typography: `14px`, Regular (400), Text `#0F172A`
  * Padding: `0 14px`
* **Focus State:**
  * Border: `1px solid #2563EB`
  * Box Shadow: `0 0 0 3px rgba(37, 99, 235, 0.15)`
* **Invalid State (e.g., Target arrival in past):**
  * Border: `1px solid #EF4444`
  * Box Shadow: `0 0 0 3px rgba(239, 68, 68, 0.15)`
  * Micro-copy: Displayed immediately below input in `#EF4444` (`12px`, Medium) with warning exclamation icon.

#### Risk Tolerance Segmented Control (Alpha Selection)
Commuters choose risk tolerance via a 3-option segmented toggle rather than an ambiguous continuous slider.
* **Options:**
  1. **"High Reliability"** ($lpha = 0.05$) — "Late $\le 1$ in 20 times (5% risk)"
  2. **"Standard Commute"** ($lpha = 0.10$) — "Late $\le 1$ in 10 times (10% risk)" *(Default)*
  3. **"Aggressive / Fast"** ($lpha = 0.20$) — "Late $\le 1$ in 5 times (20% risk)"
* **Container Styling:** Background `#F1F5F9`, border radius `10px`, padding `4px`.
* **Active Segment:** Background `#FFFFFF`, box shadow `0 2px 4px rgba(0,0,0,0.06)`, text `#0F172A` (SemiBold).
* **Inactive Segment:** Text `#64748B`, transparent background, hover text `#0F172A`.

---

### 3.3 Cards & Container Surfaces (`<Card>`)

RouteTrust uses modular cards to distinguish between control inputs, primary decision outputs, and system telemetry.

```
+-----------------------------------------------------------------------------------------+
|                              DECISION HERO CARD ARCHITECTURE                            |
+-----------------------------------------------------------------------------------------+
|  [Route Badge: M15-SBS]              [Status Badges: Live Weather | Guard Verified]    |
|                                                                                         |
|  RECOMMENDED LEAVE-BY TIME:                                                             |
|  ===========================================                                            |
|   08:14 AM                                  [ GRADE A ]                                 |
|  ===========================================  (High Predictability - Spread: 4.2 min)   |
|                                                                                         |
|  Target Arrival: 08:45 AM    Scheduled Travel: 23 min    Risk Buffer: +8 min (q90)      |
|  -------------------------------------------------------------------------------------  |
|  (!) Low Sample Route Alert (If active) / Historical Weather Estimation Flag            |
+-----------------------------------------------------------------------------------------+
```

* **Default Content Card:**
  * Background: `#FFFFFF` | Border: `1px solid #E2E8F0` | Border Radius: `12px`
  * Padding: `24px` | Shadow: `0 1px 3px rgba(0,0,0,0.05)`
* **Hero Decision Card (Active Recommendation):**
  * Background: Gradient `#FFFFFF` to `#F8FAFC`
  * Border: `1px solid #CBD5E1` with accent border top (`4px solid #2563EB`)
  * Padding: `28px` | Shadow: `0 10px 15px -3px rgba(15, 23, 42, 0.08)`
* **Warning Card / Banner (Fallback Weather or Low Samples):**
  * Background: `#FFFBEB` | Border: `1px solid #FDE68A` | Border Radius: `8px`
  * Text: `#92400E` | Icon: Amber warning triangle | Padding: `12px 16px`

---

### 3.4 Reliability Grade Badges

Reliability grades represent normalized interquantile variance: $	ext{Spread} = rac{\hat{Q}_{0.90} - \hat{Q}_{0.10}}{\hat{Q}_{0.50}}$.

| Grade | Metric Definition | Background Fill | Border Color | Text Color | Plain-Language Meaning |
|:---:|:---:|:---:|:---:|:---:|:---|
| **A** | $	ext{Spread} \le 0.15$ | `#ECFDF5` | `#A7F3D0` | `#065F46` | **Ultra-Reliable:** Minimal delay variance. Departure times are highly predictable. |
| **B** | $0.15 < 	ext{Spread} \le 0.30$ | `#EFF6FF` | `#BFDBFE` | `#1E40AF` | **Reliable:** Typical urban commuter baseline. Small buffer required. |
| **C** | $0.30 < 	ext{Spread} \le 0.50$ | `#FFFBEB` | `#FDE68A` | `#92400E` | **Moderate Variance:** Noticeable delay risk. Buffer expands under precipitation. |
| **D** | $0.50 < 	ext{Spread} \le 0.75$ | `#FFF7ED` | `#FED7AA` | `#9A3412` | **High Volatility:** Unstable route schedule. Leave early to ensure arrival. |
| **F** | $	ext{Spread} > 0.75$ | `#FEF2F2` | `#FECACA` | `#991B1B` | **Severe Risk:** Unpredictable bottleneck segment. Consider alternate transit. |

*Badge Structure:* Height `32px`, padding `0 14px`, pill radius (`9999px`), bold font weight (`700`), displaying the grade letter alongside a compact subtitle.

---

### 3.5 Modals & Overlay Dialogs (`<Modal>`)

Used for technical diagnostics, model calibration inspection, and error resolution.

* **Backdrop Scrim:**
  * Background: `rgba(15, 23, 42, 0.60)` (`--color-slate-900` at 60% opacity)
  * Backdrop filter: `blur(4px)`
* **Modal Dialog Window:**
  * Width: Desktop `640px` (max-width `90vw`), Mobile `100vw` (drawer bottom-sheet style)
  * Background: `#FFFFFF` | Border Radius: `16px` | Shadow: `--shadow-modal`
  * Padding: `24px` header, `24px` body scroll container, `16px 24px` action footer
* **Close Interaction:**
  * Accessible `ESC` keydown listener, backdrop click-to-dismiss, and explicit top-right "X" icon button (`#64748B`, hover `#0F172A`).

---

## 4. Responsive Layout & Viewport Rules

RouteTrust is designed "mobile-first" because $>75\%$ of transit queries originate on mobile devices while walking or commuting.

```
Viewport Breakpoints:
+-----------------------------------------------------------------------------------------+
| Mobile (<640px)          | Tablet (640px - 1024px)       | Desktop (>1024px)            |
| 1 Column Linear Flow     | 2 Column Balanced Grid        | Asymmetric 2-Column Split    |
| Full-width controls      | Stacked sidebars              | Sticky Inputs / Main Canvas  |
| 16px page margins        | 24px page margins             | 32px page margins            |
+-----------------------------------------------------------------------------------------+
```

### 4.1 Layout Grid Rules
* **Mobile (< 640px):**
  * Grid: 4 columns, `16px` gutters, `16px` outer margin.
  * Inputs and action buttons expand to `width: 100%`.
  * Results hero card stays fixed at the top after computation.
* **Tablet (640px – 1023px):**
  * Grid: 8 columns, `20px` gutters, `24px` outer margin.
  * Inputs grouped in pairs (Route + Stop in row 1, Arrival Time + Risk in row 2).
* **Desktop (1024px+):**
  * Grid: 12 columns, `24px` gutters, max-width `1200px` centered.
  * **Layout Split:**
    * Left Column (5 columns): Sticky Commute Parameters Card (Input controls, alpha stepper, CTA).
    * Right Column (7 columns): Hero Decision Card, Risk Buffer Decomposition, and Expandable Diagnostics Accordion.

---

## 5. Frontend-to-Backend API Specification

RouteTrust frontend interfaces directly with the FastAPI backend engine. All JSON payloads strictly adhere to Pydantic v2 schemas.

```
+-------------------+                                  +---------------------+
|                   |  POST /api/v1/optimize-decision  |                     |
|                   | -------------------------------->|                     |
|                   |  <HTTP 200 OK: Decision Object>  |                     |
|  RouteTrust Web   | <--------------------------------|   FastAPI Backend   |
|  Frontend Client  |                                  |   (Port 8000)       |
|  (Streamlit / UI) |  GET /api/v1/routes-stops        |                     |
|                   | -------------------------------->|                     |
|                   |  GET /api/v1/diagnostics/model   |                     |
|                   | -------------------------------->|                     |
+-------------------+                                  +---------------------+
```

---

### Endpoint 1: Route & Stop Catalog Ingestion
* **Endpoint:** `GET /api/v1/routes-stops`
* **Purpose:** Populates the dynamic route and stop dropdown selectors on initial client boot.
* **Authentication:** None (Public)
* **Headers:**
  ```http
  Accept: application/json
  ```
* **Request Query Parameters:**
  * `active_only` (boolean, optional, default: `true`): Filter to active service segments.

* **Response Payload (`200 OK`):**
```json
{
  "total_count": 4,
  "items": [
    {
      "id": 101,
      "route_id": "M15-SBS",
      "stop_id": "401923",
      "route_short_name": "M15-SBS Southbound",
      "stop_name": "2nd Ave & E 34th St",
      "scheduled_travel_time_sec": 1380,
      "sample_count": 1420,
      "is_low_sample": false
    },
    {
      "id": 102,
      "route_id": "B63",
      "stop_id": "308211",
      "route_short_name": "B63 Westbound",
      "stop_name": "5th Ave & 9th St",
      "scheduled_travel_time_sec": 960,
      "sample_count": 22,
      "is_low_sample": true
    }
  ]
}
```

---

### Endpoint 2: Leave-By Decision Optimization Engine
* **Endpoint:** `POST /api/v1/optimize-decision`
* **Purpose:** Primary computation engine. Evaluates quantiles, applies monotonic sort, evaluates early departure guard, and returns the actionable leave-by recommendation.
* **Authentication:** None (Public, IP rate-limited to 60 req/min)
* **Headers:**
  ```http
  Content-Type: application/json
  Accept: application/json
  X-Client-Request-ID: e62a6b29-4561-41e7-814d-1768c07e2c94
  ```

* **Request Payload (`POST` Body):**
```json
{
  "route_stop_id": 101,
  "required_arrival_time": "2026-09-11T09:00:00Z",
  "alpha": 0.10
}
```
*Field Validation Rules:*
* `route_stop_id`: Integer, must exist in `routes_stops`.
* `required_arrival_time`: ISO-8601 UTC timestamp. Must be at least 5 minutes in the future relative to server time.
* `alpha`: Float, restricted to set `[0.20, 0.10, 0.05]`.

* **Success Response Payload (`200 OK`):**
```json
{
  "request_uuid": "e62a6b29-4561-41e7-814d-1768c07e2c94",
  "route_stop_id": 101,
  "route_short_name": "M15-SBS Southbound",
  "stop_name": "2nd Ave & E 34th St",
  "required_arrival_time": "2026-09-11T09:00:00Z",
  "alpha": 0.10,
  "predictions": {
    "q10_delay_sec": -60.0,
    "q50_delay_sec": 180.0,
    "q90_delay_sec": 540.0,
    "selected_quantile_delay_sec": 540.0,
    "interquantile_spread_sec": 600.0
  },
  "decision": {
    "recommended_leave_by": "2026-09-11T08:28:00Z",
    "scheduled_travel_time_sec": 1380,
    "risk_buffer_applied_sec": 540,
    "total_transit_allocation_sec": 1920,
    "reliability_grade": "B",
    "guard_triggered": false
  },
  "telemetry": {
    "weather_source": "live",
    "weather_condition": {
      "precipitation_mm": 0.0,
      "apparent_temperature_c": 21.4,
      "wind_speed_kmh": 12.1
    },
    "low_confidence_flag": false,
    "latency_ms": 42.8
  }
}
```

* **Error Response Matrix:**
  * **`422 Unprocessable Entity` (Past Arrival Time):**
    ```json
    {
      "error_code": "INVALID_ARRIVAL_TIME",
      "message": "Target arrival time must be in the future. Received: 2026-09-11T08:00:00Z."
    }
    ```
  * **`429 Too Many Requests` (Rate limit exceeded):**
    ```json
    {
      "error_code": "RATE_LIMIT_EXCEEDED",
      "message": "Too many requests. Please wait 60 seconds before calculating another route."
    }
    ```
  * **`503 Service Unavailable` (Missing Model Artifacts):**
    ```json
    {
      "error_code": "MODEL_OFFLINE",
      "message": "The prediction engine is temporarily undergoing maintenance. Please check back shortly."
    }
    ```

---

### Endpoint 3: Diagnostics & Model Calibration Telemetry
* **Endpoint:** `GET /api/v1/diagnostics/model`
* **Purpose:** Feeds the Technical Auditor / Diagnostics Screen with holdout loss metrics, feature importances, and quantile calibration curves.
* **Authentication:** Bearer Token required for detailed telemetry (`Authorization: Bearer <ADMIN_API_KEY>`)
* **Headers:**
  ```http
  Authorization: Bearer admin_live_9f83a2c0192e4
  Accept: application/json
  ```

* **Response Payload (`200 OK`):**
```json
{
  "model_version": "1.2.0-lightgbm",
  "training_timestamp": "2026-09-01T12:00:00Z",
  "train_test_split_strategy": "chronological_holdout_non_shuffled",
  "metrics": {
    "pinball_loss": {
      "model_loss": 28.4,
      "baseline_groupby_median_loss": 33.1,
      "improvement_percentage": 14.19
    },
    "coverage_calibration": {
      "q10": { "target": 0.10, "empirical": 0.108, "status": "calibrated" },
      "q50": { "target": 0.50, "empirical": 0.512, "status": "calibrated" },
      "q90": { "target": 0.90, "empirical": 0.894, "status": "calibrated" }
    }
  },
  "feature_importance": [
    { "feature": "scheduled_travel_time_sec", "importance_score": 0.38 },
    { "feature": "hour_of_day", "importance_score": 0.24 },
    { "feature": "precipitation_mm", "importance_score": 0.18 },
    { "feature": "day_of_week", "importance_score": 0.12 },
    { "feature": "apparent_temperature_c", "importance_score": 0.08 }
  ],
  "provenance": {
    "source_archive": "traines.eu GTFS-RT Archive",
    "weather_archive": "Open-Meteo Historical Weather",
    "known_limitations": "Direct route segments only. Transfers and detours excluded."
  }
}
```

---

## 6. Third-Party Integrations & External Service Specs

RouteTrust v1 connects to targeted external cloud services to power weather ingestion, open schedule datasets, and containerized deployment.

```
+-----------------------------------------------------------------------------------------+
|                               THIRD-PARTY INTEGRATION MAP                               |
+-----------------------------------------------------------------------------------------+
|                                                                                         |
|   +--------------------------+       +-------------------------+                        |
|   |  Open-Meteo Weather API  |       |  GTFS-RT / TransXChange |                        |
|   |  - Live weather forecast |       |  - Historical delay log |                        |
|   |  - 2.0s strict timeout   |       |  - Schedule baselines   |                        |
|   +--------------------------+       +-------------------------+                        |
|                 ^                                 ^                                     |
|                 | (Async Ingest)                  | (Static Seed)                       |
|                 +----------------+  +-------------+                                     |
|                                  |  |                                                   |
|                        +---------v--v---------+                                         |
|                        |   RouteTrust Backend |                                         |
|                        |   FastAPI + SQLite   |                                         |
|                        +----------------------+                                         |
|                                   |                                                     |
|                                   v (Port 7860 Gateway)                                 |
|                        +----------------------+                                         |
|                        | Hugging Face Spaces  |                                         |
|                        | Docker Container     |                                         |
|                        +----------------------+                                         |
+-----------------------------------------------------------------------------------------+
```

### 6.1 Open-Meteo Weather API Integration
* **Service Role:** Provides real-time atmospheric measurements (rain, temperature, wind speed) used as critical feature inputs into LightGBM inference.
* **Service Provider:** Open-Meteo GmbH (Open-source weather API).
* **Endpoint URL:** `https://api.open-meteo.com/v1/forecast`
* **HTTP Method:** `GET`
* **Authentication:** Open access / Free tier (No API key required in header).
* **Outgoing Parameters:**
  * `latitude` (float, e.g., `40.7128`): Latitude of transit origin/stop.
  * `longitude` (float, e.g., `-74.0060`): Longitude of transit origin/stop.
  * `hourly` (comma-separated string): `precipitation,apparent_temperature,wind_speed_10m`
  * `timezone` (string): `auto` or local transit authority timezone.
* **Execution Guardrails:**
  * Strict client-side connection timeout: `2.0 seconds` (via `httpx.AsyncClient(timeout=2.0)`).
  * In the event of a connection timeout, HTTP 429 rate limit, or HTTP 500 error:
    1. The API call is aborted without blocking user flow.
    2. The backend queries SQLite table `weather_fallbacks` matching `(route_stop_id, current_month, current_hour)`.
    3. Response tag is set to `weather_source = "historical_fallback"`.
    4. Frontend displays the inline notification: *"Weather estimated from historical medians."*

---

### 6.2 Transit Schedule & GTFS-RT Data Archives
* **Service Role:** Provides historical vehicle positional records, delay timestamps, and canonical stop timetables.
* **Primary Source:** `traines.eu` open transit archive (Secondary Fallback: Transport for NSW / Mobility Database).
* **Ingestion Method:** Offline Parquet extraction pipeline (`data/raw/gtfs_rt_archive.parquet`).
* **Runtime Usage:** Data is pre-aggregated at deployment into `routes_stops` SQLite tables. The frontend never queries raw Parquet archives directly; all queries flow through the `/api/v1/routes-stops` API layer.

---

### 6.3 Hugging Face Spaces (Container Hosting & Reverse Proxy)
* **Service Role:** Ephemeral container host and SSL termination gateway.
* **Base Image:** Debian/Ubuntu Linux running Python 3.11.
* **Exposed Port:** `7860` (Hugging Face default ingress port).
* **Internal Loopback:** FastAPI binds internally to `127.0.0.1:8000`. Streamlit binds to `0.0.0.0:7860` and proxies prediction requests over internal loopback HTTP to avoid public internet round-trips.

---

## 7. Frontend State Management & Failure Resilience

### 7.1 State Machine Architecture
The frontend operates on a deterministic finite state machine (FSM) to prevent conflicting visual cues.

```
       [IDLE / READY]
             |
             | User triggers "Calculate Leave-By"
             v
       [VALIDATING] ----(Target arrival in past)----> [INPUT_ERROR]
             |                                              |
             | (Valid parameters)                   (Fixes timestamp)
             v                                              |
       [FETCHING / INFERENCE] <-----------------------------+
             |
             +----(Backend 200 OK)--------> [DECISION_RENDERED]
             |                                    |
             |                                    +--(Toggle details)--> [DIAGNOSTICS_OPEN]
             |
             +----(Backend 429/500/503)---> [NETWORK_ERROR]
```

### 7.2 UI Resilience Patterns
1. **Pessimistic Departure Clamping:** If the model predicts negative delay (vehicle running ahead of schedule), the UI highlights the **Early Departure Guard**:
   * *UI Copy:* `"Early Departure Guard Applied: Recommended departure was clamped to ensure you don't miss an early-running vehicle."*
2. **Low-Sample Route Confidence Tag:**
   * If `low_confidence_flag == true` ($N < 30$), the decision card renders an amber indicator:
   * *UI Copy:* `"Limited Historical Data: This route segment has fewer than 30 logged trips. Buffer recommendations are conservative."*
3. **Fallback Weather Notification:**
   * If `weather_source == "historical_fallback"`, an inline pill displays:
   * *UI Copy:* `"Historical Weather Estimate: Live weather API was unavailable; using 5-year September median conditions."*

---

## 8. Developer Implementation Checklist

- [ ] **Design Tokens Setup:** Define CSS Custom Properties (`:root { ... }`) matching the color, typography, spacing, and elevation tokens in Section 2.
- [ ] **Component Library Construction:**
  - [ ] Implement `<Button>` variants (Primary, Secondary, Ghost, Loading).
  - [ ] Build `<Select>` and `<Input>` with floating label and error validation microcopy.
  - [ ] Create the 3-state Segmented Alpha Control (`0.05`, `0.10`, `0.20`).
  - [ ] Build `<HeroDecisionCard>` displaying display-size leave-by time and reliability badge.
  - [ ] Build `<ReliabilityGradeBadge>` with dynamic color mapping (A–F).
- [ ] **API Client Implementation:**
  - [ ] Create HTTP client with auto-injected `X-Client-Request-ID` UUID headers.
  - [ ] Connect `GET /api/v1/routes-stops` to route dropdown selectors.
  - [ ] Wire `POST /api/v1/optimize-decision` to form submit action.
  - [ ] Implement client-side input guard (block submissions where arrival time $\le$ now).
- [ ] **Resilience Testing:**
  - [ ] Simulate Open-Meteo timeout and confirm fallback banner appears in UI.
  - [ ] Simulate low-sample route ($N=22$) and verify amber confidence warning renders.
  - [ ] Verify accessibility keyboard navigation (`Tab`, `Enter`, `Space`) across all interactive elements.

---
*End of Document. Maintain this document alongside the RouteTrust Technical Architecture and PRD.*
