# Storage Market Data Collection Platform — Project Plan

## 1. Project Overview

Build a scalable data-collection platform for collecting and maintaining historical self-storage facility information across regional and eventually nationwide markets.

The platform should collect publicly accessible information such as:

- Facility information
- Unit sizes
- Unit characteristics
- Advertised monthly prices
- Online/web prices
- Promotional pricing
- Displayed availability
- Availability-related text
- Collection timestamps
- Provider metadata

The long-term objective is not simply to build web scrapers.

The system should function as a **reliable storage-market data pipeline** capable of:

1. Discovering facilities.
2. Scheduling collection jobs.
3. Collecting data through the most appropriate permitted method.
4. Preserving source data when appropriate.
5. Parsing provider-specific formats.
6. Normalizing data into a common schema.
7. Validating observations.
8. Detecting abnormal or potentially incorrect data.
9. Maintaining historical observations.
10. Measuring collection health and coverage.
11. Recovering gracefully from failures.
12. Scaling horizontally as coverage increases.
13. Supporting analytics, APIs, and dashboards later.

The architecture should prioritize:

- Reliability
- Data quality
- Maintainability
- Observability
- Reproducibility
- Provider isolation
- Scalability
- Responsible collection behavior
- Testing
- Historical data integrity

---

# 2. Core Engineering Philosophy

The project should be built **vertically before horizontally**.

Do not begin by attempting nationwide collection.

Initial development progression:

```text
1 provider
    ↓
1 facility
    ↓
10 facilities
    ↓
100 facilities
    ↓
regional pilot
    ↓
second provider
    ↓
multiple providers
    ↓
distributed workers
    ↓
larger geographic coverage
    ↓
nationwide collection
```

The first major objective is to prove that one complete pipeline works reliably:

```text
Website
    ↓
Collector
    ↓
Raw response
    ↓
Parser
    ↓
Normalizer
    ↓
Validator
    ↓
Database
    ↓
Historical observation
    ↓
Metrics
```

Infrastructure complexity should only be added when the current architecture demonstrates a real need for it.

---

# 3. High-Level Architecture

Target architecture:

```text
                        SCHEDULER
                            │
                            ↓
                     PROVIDER POLICY
                            │
                            ↓
                        JOB QUEUE
                            │
             ┌──────────────┼──────────────┐
             ↓              ↓              ↓
          Worker          Worker          Worker
             │              │              │
             └──────────────┼──────────────┘
                            ↓
                     PROVIDER ADAPTER
                            │
                  ┌─────────┴─────────┐
                  ↓                   ↓
            HTTP COLLECTOR       PLAYWRIGHT
                  │                   │
                  └─────────┬─────────┘
                            ↓
                   RESPONSE INSPECTOR
                            │
             ┌──────────────┴──────────────┐
             ↓                             ↓
          NORMAL                      ABNORMAL
             │                             │
             ↓                             ↓
       RAW DATA STORAGE              Failure Handler
             │                             │
             ↓                        Backoff/Pause
          PARSER                           │
             │                       Circuit Breaker
             ↓
        NORMALIZER
             ↓
         VALIDATOR
             ↓
      DATA QUALITY CHECKS
             ↓
        POSTGRESQL
             │
       ┌─────┼─────────────┐
       ↓     ↓             ↓
    Metrics API         Analytics
                         │
                         ↓
                      Dashboard
```

Not every component needs to exist in V1.

The architecture should make it possible to introduce these components without rewriting the scraper framework.

---

# 4. Technology Stack

## Primary Language

**Python**

Reasons:

- Strong scraping ecosystem
- Excellent HTTP libraries
- Official Playwright support
- Strong data-processing ecosystem
- PostgreSQL support
- Background-worker ecosystem
- Analytics ecosystem
- Easy testing
- FastAPI support
- Good fit for data engineering

---

# 5. Initial Python Libraries

## Browser Automation

```text
playwright
```

Use Playwright when browser execution is genuinely necessary.

Do not use Selenium in V1.

Selenium may later be introduced for benchmarking or research comparisons, but it should not duplicate Playwright's production responsibilities.

---

## HTTP

```text
httpx
```

Use HTTP collection whenever a suitable public-facing endpoint or ordinary HTTP response provides the required data and its use is appropriate.

Collection preference:

```text
HTTP
 ↓
if browser execution is required
 ↓
Playwright
```

Do not unnecessarily launch browsers.

---

## HTML Parsing

```text
BeautifulSoup
lxml
```

Use only when HTML parsing is required.

JSON should generally be processed directly rather than converted into HTML workflows.

---

## Data Validation

```text
Pydantic
```

All provider output should pass through normalized Pydantic models before database insertion.

---

## Database

```text
PostgreSQL
```

PostgreSQL will be the authoritative structured datastore.

---

## ORM

```text
SQLAlchemy
```

---

## Database Migrations

```text
Alembic
```

All schema modifications must occur through migrations.

Never manually modify production schemas without corresponding migrations.

---

## Testing

```text
pytest
pytest-asyncio
```

Additional testing libraries may be introduced when justified.

---

## API — Later Phase

```text
FastAPI
```

Not required for initial collection.

---

## Queue — Later Phase

Potential options:

```text
Redis + Dramatiq
Redis + RQ
Redis + Celery
```

Do not introduce a distributed queue until local/regional collection demonstrates the need.

The application architecture should nevertheless make scrape jobs independently executable from the beginning.

---

## Containers

```text
Docker
Docker Compose
```

Introduce after the basic pipeline is stable.

---

## Analytics

Initially:

```text
SQL
Pandas
```

Later:

```text
FastAPI
dashboard/frontend
geospatial analysis
```

---

# 6. Proposed Repository Structure

```text
storage-market-data/
│
├── app/
│   │
│   ├── main.py
│   │
│   ├── config.py
│   │
│   ├── logging.py
│   │
│   ├── constants.py
│   │
│   │
│   ├── collectors/
│   │   ├── base.py
│   │   ├── http.py
│   │   └── playwright.py
│   │
│   ├── providers/
│   │   │
│   │   ├── base.py
│   │   │
│   │   ├── registry.py
│   │   │
│   │   ├── provider_a/
│   │   │   ├── config.py
│   │   │   ├── collector.py
│   │   │   ├── discovery.py
│   │   │   ├── parser.py
│   │   │   └── fixtures/
│   │   │
│   │   └── provider_b/
│   │       ├── config.py
│   │       ├── collector.py
│   │       ├── discovery.py
│   │       ├── parser.py
│   │       └── fixtures/
│   │
│   ├── models/
│   │   ├── facility.py
│   │   ├── unit.py
│   │   ├── observation.py
│   │   ├── scrape.py
│   │   └── enums.py
│   │
│   ├── parsers/
│   │   └── utilities.py
│   │
│   ├── normalization/
│   │   ├── address.py
│   │   ├── dimensions.py
│   │   ├── money.py
│   │   └── units.py
│   │
│   ├── validation/
│   │   ├── observations.py
│   │   ├── anomalies.py
│   │   └── schemas.py
│   │
│   ├── database/
│   │   ├── engine.py
│   │   ├── session.py
│   │   ├── models.py
│   │   └── repositories/
│   │       ├── facilities.py
│   │       ├── units.py
│   │       ├── observations.py
│   │       ├── scrape_runs.py
│   │       └── raw_scrapes.py
│   │
│   ├── pipelines/
│   │   ├── facility_discovery.py
│   │   └── facility_scrape.py
│   │
│   ├── scheduler/
│   │   ├── scheduler.py
│   │   ├── priority.py
│   │   └── policies.py
│   │
│   ├── jobs/
│   │   ├── models.py
│   │   ├── executor.py
│   │   └── retry.py
│   │
│   ├── resilience/
│   │   ├── rate_limit.py
│   │   ├── backoff.py
│   │   ├── circuit_breaker.py
│   │   ├── response_classifier.py
│   │   └── provider_health.py
│   │
│   ├── metrics/
│   │   ├── collector.py
│   │   └── calculations.py
│   │
│   ├── storage/
│   │   ├── raw.py
│   │   └── retention.py
│   │
│   └── services/
│
├── tests/
│   │
│   ├── unit/
│   ├── integration/
│   ├── fixtures/
│   ├── providers/
│   └── resilience/
│
├── scripts/
│   ├── scrape_facility.py
│   ├── discover_facilities.py
│   ├── benchmark.py
│   └── health_report.py
│
├── migrations/
│
├── data/
│   └── raw/
│
├── docker/
│
├── docs/
│   ├── providers/
│   ├── architecture.md
│   └── data_dictionary.md
│
├── .env.example
├── .gitignore
├── docker-compose.yml
├── pyproject.toml
├── README.md
└── planning.md
```

This structure can evolve.

Avoid creating empty abstractions simply because they appear in this plan. Add modules when their responsibility actually exists.

---

# 7. Provider Adapter Architecture

Each storage company should be isolated behind a provider adapter.

The rest of the application should not know the internal structure of individual storage websites.

Conceptual interface:

```python
class StorageProvider:

    def discover_facilities(self, region):
        ...

    def collect_facility(self, facility):
        ...

    def parse_facility(self, raw_response):
        ...
```

Provider-specific code belongs inside:

```text
providers/<provider>/
```

Do not build large blocks such as:

```python
if provider == "provider_a":
    ...
elif provider == "provider_b":
    ...
```

The provider registry should map providers to implementations.

---

# 8. Separate Collection From Parsing

Collectors retrieve information.

Parsers interpret information.

Never combine these responsibilities unnecessarily.

Correct:

```text
Collector
    ↓
Raw Response
    ↓
Parser
    ↓
Provider Data
    ↓
Normalizer
```

Incorrect:

```text
Open browser
↓
parse HTML
↓
normalize price
↓
insert database
↓
calculate analytics
```

inside one function.

This separation enables:

- Parser testing without network access
- Raw response replay
- Easier debugging
- Provider isolation
- Parser versioning
- Reprocessing historical data

---

# 9. Collection Strategy

Each provider should define a preferred collection method.

Example:

```yaml
preferred_collector: http
fallback_collector: playwright
```

The system should not automatically assume that fallback is always appropriate.

Fallback behavior should be explicitly defined per provider.

---

# 10. Playwright Responsibilities

Playwright should be used for:

- Browser-required workflows
- JavaScript-rendered content
- Facility discovery where browser interaction is required
- Understanding page behavior during provider onboarding
- Inspecting browser network requests
- Reproducing browser-dependent problems
- Capturing diagnostics when browser jobs fail

Playwright should NOT become a universal default if ordinary HTTP collection is sufficient.

---

# 11. Selenium

Do not include Selenium in the initial production stack.

Potential future use:

```text
Playwright vs Selenium benchmarking
```

Metrics could include:

- Runtime
- Memory
- CPU
- Success rate
- Browser startup cost
- Failure rate
- Throughput

---

# 12. Facility Discovery

Facility discovery and inventory collection are separate problems.

## Discovery

Answers:

> What facilities exist?

Potential inputs:

```text
ZIP
city
metro
state
geographic grid
provider facility directory
```

Output:

```text
provider
external_facility_id
name
address
city
state
zip
latitude
longitude
```

Discovery should run less frequently than pricing collection.

Possible future schedule:

```text
facility discovery → weekly

inventory collection → daily
```

Do not perform unnecessary ZIP searches every time an already-known facility is scraped.

---

# 13. Geographic Discovery Risks

Search results may:

- Return only the closest N facilities
- Overlap between ZIP codes
- Exclude distant facilities
- Depend on coordinates
- Change ordering
- Include duplicate facilities

Discovery must deduplicate facilities.

Overlapping geographic searches may eventually be required.

Coverage should be measured independently from collection success.

---

# 14. Facility Identity

A physical facility should have its own internal database identity.

Primary matching should use:

```text
provider
+
provider external facility ID
```

when stable IDs exist.

Fallback identity signals may include:

- Normalized address
- Latitude/longitude
- Phone number if publicly available and useful
- Facility name
- Geographic proximity

Do not rely on facility name alone.

---

# 15. Provider Ownership vs Physical Facility

Long-term architecture should allow a physical facility to change operators.

Example:

```text
Physical Facility #1832

2026:
Provider A

2028:
Provider B
```

Do not assume operator identity and physical facility identity must always be the same entity forever.

This becomes important for acquisitions and rebrands.

---

# 16. Facility Lifecycle

Potential states:

```text
ACTIVE

TEMPORARILY_UNAVAILABLE

CLOSED

UNKNOWN
```

Never delete historical facility records merely because a facility disappears from current discovery results.

---

# 17. Unit Product Identity

Do not treat all units with identical dimensions as identical products.

Potential differentiators:

```text
width
length
climate controlled
floor
drive-up
indoor/outdoor
door type
access type
vehicle storage
other features
```

Conceptual hierarchy:

```text
PHYSICAL FACILITY
       ↓
UNIT PRODUCT
       ↓
OBSERVATION
```

---

# 18. Normalized Data Models

## Facility

Potential fields:

```text
id

provider_id
external_facility_id

name

address_line_1
address_line_2

city
state
postal_code
country

latitude
longitude
timezone

status

created_at
updated_at
last_discovered_at
```

---

# 19. Unit Product

Potential fields:

```text
id

facility_id
external_unit_id

width_ft
length_ft

square_feet

climate_controlled
floor
drive_up
indoor

features

first_seen_at
last_seen_at
```

Provider-specific fields can be retained separately where necessary.

---

# 20. Observation

Potential fields:

```text
id

unit_product_id

scraped_at

standard_price
online_price
promo_price

promotion_text

availability_status
availability_text

parser_version

scrape_run_id
```

---

# 21. Pricing Model

Do not use one generic `price` field when multiple price concepts exist.

Separate:

```text
standard_price

online_price

promo_price

promotion_text
```

Examples of problematic marketing:

```text
First month $1

50% off first two months

Starting at $89

Web rate $129

Regular rate $159
```

Preserve enough information to distinguish these.

---

# 22. Availability Semantics

Do not describe collected availability as literal physical vacancy unless the source actually provides that information.

A safer interpretation:

> The provider website advertised this unit product as available for online rental at the time of observation.

Possible normalized states:

```text
AVAILABLE

UNAVAILABLE

LIMITED

NOT_OBSERVED

UNKNOWN
```

---

# 23. Critical Rule: Absence Is Not Unavailability

If yesterday:

```text
10x10
AVAILABLE
```

and today the scraper does not see the product, do NOT automatically write:

```text
UNAVAILABLE
```

It could mean:

- Product sold out
- Product renamed
- API changed
- Partial response
- Parser failure
- Website redesign
- Temporary website issue

Use:

```text
NOT_OBSERVED
```

or equivalent logic until enough evidence exists to infer something stronger.

---

# 24. Raw Response Storage

Preserve raw source responses where practical.

Benefits:

- Debugging
- Parser development
- Historical correction
- Reprocessing
- Data lineage
- Site-change investigation

Example metadata:

```text
provider

facility_id

scraped_at

collector_type

URL or request identifier

HTTP status

content_type

raw_payload

parser_version
```

PostgreSQL JSONB may be used for smaller structured payloads.

Larger HTML/JSON artifacts may eventually move to object storage.

---

# 25. Raw Storage Retention

Raw data can become expensive.

Do not assume every successful HTML response must remain in the primary database forever.

Future retention policy might resemble:

```text
Failures:
retain longer

Successful responses:
retain recent data

Older successful responses:
compress/archive/sample
```

Historical structured observations should have a different retention policy from raw source artifacts.

---

# 26. Parser Versioning

Each provider parser should have an explicit version.

Example:

```text
provider_a_v1

provider_a_v2
```

Each observation should be traceable to the parser version that generated it.

This allows investigation of historical parsing errors.

---

# 27. Reprocessing

Raw responses should be capable of being replayed through parsers.

Conceptually:

```text
stored raw response
        ↓
new parser
        ↓
normalized records
```

Parser development should not require hitting provider websites repeatedly.

---

# 28. PostgreSQL Core Tables

Initial expected tables:

```text
providers

physical_facilities

provider_facilities

unit_products

observations

raw_scrapes

scrape_runs
```

Potential later tables:

```text
scrape_jobs

provider_health

provider_incidents

discovery_runs

markets

facility_market_membership
```

Exact schema should be designed before implementation.

---

# 29. Observation Volume

Plan for observations to eventually become the largest table.

Example:

```text
20,000 facilities
×
15 products
×
365 days
=
109,500,000 observations/year
```

Do not prematurely optimize for this scale, but avoid architectural choices that make growth impossible.

Possible future improvements:

- Table partitioning
- Time-based partitioning
- Batch inserts
- Optimized indexes
- Archival
- Change-based storage
- Analytical replicas

---

# 30. Snapshot vs Change-Based History

Initially favor correctness and simplicity.

Daily snapshots provide clear evidence that something was observed.

Later evaluate whether unchanged observations can be compressed into intervals.

Never optimize storage in a way that destroys the ability to determine what was observed at a given time.

---

# 31. Idempotency

Every scrape job must be safe to retry.

A retry must not accidentally create duplicate:

- Facilities
- Unit products
- Scrape jobs
- Observations where duplicates are not intended

Use database constraints and stable external identifiers wherever possible.

---

# 32. Validation Layer

All parsed data must be validated before becoming trusted observations.

Examples:

```text
price >= 0

width > 0

length > 0

provider exists

facility exists

scraped_at exists
```

Validation should also enforce reasonable types and formats.

---

# 33. Data Quality / Anomaly Detection

Schema validation alone is insufficient.

Example:

```text
Yesterday:
$149

Today:
$14,900
```

Both are technically valid numbers.

The second should be flagged as suspicious.

Future anomaly rules may examine:

- Extreme price changes
- Impossible dimensions
- Sudden facility inventory collapse
- Sudden provider-wide price changes
- Unexpected null rates
- Abnormally low unit counts
- Abnormally high unit counts
- Provider-wide field disappearance

---

# 34. Three Health Layers

Never use one "success rate" to describe the whole platform.

Track separately:

## System Health

Did infrastructure operate correctly?

Examples:

```text
worker uptime
database availability
queue health
scheduler health
```

## Collection Health

Did we retrieve the expected provider response?

Examples:

```text
HTTP success
browser success
timeouts
403
429
challenge pages
```

## Data Health

Does the resulting information appear valid?

Examples:

```text
parser success
validation success
expected field coverage
anomaly rate
facility coverage
```

Example report:

```text
System uptime:               99.9%

Collection success:          98.4%

Valid observation rate:      97.9%

Estimated facility coverage: 92.1%
```

---

# 35. Structured Logging

Avoid logs such as:

```text
something broke
```

Prefer structured context:

```text
timestamp
provider
facility_id
job_id
collector
parser_version
status
duration_ms
error_type
```

Example:

```text
provider=provider_a
facility=38291
collector=http
status=success
units=14
duration_ms=823
```

---

# 36. Scrape Run Metrics

Every run should record:

```text
job_id

provider

facility_id

collector_type

started_at

finished_at

duration_ms

status

HTTP_status

records_found

bytes_downloaded

retry_count

error_type
```

---

# 37. Benchmark Metrics

Track:

```text
jobs attempted

jobs successful

success rate

failure rate

P50 latency

P95 latency

P99 latency

facilities/hour

units/hour

records/hour

retry rate

HTTP usage %

Playwright usage %

CPU usage

RAM usage

network usage
```

Later:

```text
cost / 1,000 facilities
```

---

# 38. Job States

Use explicit job states:

```text
PENDING

RUNNING

SUCCESS

RETRY

FAILED

DEAD_LETTER
```

---

# 39. Failure Categories

At minimum:

```text
TIMEOUT

NETWORK_ERROR

HTTP_403

HTTP_429

HTTP_5XX

ACCESS_DENIED

CHALLENGE_PRESENT

PARSER_ERROR

VALIDATION_ERROR

SITE_CHANGE_SUSPECTED

NO_INVENTORY

INVALID_FACILITY

DATABASE_ERROR

UNKNOWN
```

---

# 40. Partial Success

A facility scrape may return:

```text
14 products
```

while one malformed product fails parsing.

The system should have an explicit policy for:

```text
13 valid
1 invalid
```

Do not silently discard the entire response without recording why.

Potential approach:

```text
scrape status = PARTIAL_SUCCESS

valid products stored

invalid record quarantined

validation error recorded
```

---

# 41. Retry Strategy

Retry transient failures only.

Examples likely worth retrying:

```text
network timeout

temporary connection failure

some HTTP 5xx responses
```

Rate-limited requests require backoff rather than aggressive retries.

Permanent failures should not loop indefinitely.

Examples:

```text
invalid facility

broken parser

unsupported schema
```

---

# 42. Exponential Backoff With Jitter

Conceptually:

```text
attempt 1
↓
failure

wait

attempt 2
↓
failure

wait longer

attempt 3
↓
failure

stop / dead letter
```

Add jitter so multiple workers do not retry simultaneously.

---

# 43. Retry Storm Protection

Suppose:

```text
10,000 jobs fail
```

and each automatically retries three times.

Without protection:

```text
10,000 failures
→ potentially 30,000 additional attempts
```

Provider-level circuit breakers must prevent this.

---

# 44. Provider Circuit Breaker

Monitor provider-wide health.

Example:

```text
Normal success:
98%

Suddenly:
35%
```

Possible provider states:

```text
HEALTHY

DEGRADED

RATE_LIMITED

BLOCKED

PARSER_BROKEN

PAUSED
```

When severe abnormal behavior occurs:

```text
failure threshold exceeded
        ↓
circuit breaker opens
        ↓
new jobs paused
        ↓
other providers continue
```

This prevents one provider from destabilizing the platform.

---

# 45. Response Classification

Responses must be inspected before parsing.

Examples:

```text
HTTP 429
→ RATE_LIMITED

HTTP 403
→ ACCESS_DENIED

challenge/CAPTCHA page
→ CHALLENGE_PRESENT

expected JSON structure missing
→ SITE_CHANGE_SUSPECTED

normal inventory response
→ NORMAL
```

Never feed obvious error/challenge pages into ordinary parsers.

---

# 46. Bot Detection and Access Controls

The system should be resilient to sites that resist automation without making circumvention the foundation of the project.

Do not architect the system around:

- CAPTCHA bypass
- Fingerprint spoofing
- Stealth plugins
- Aggressive proxy rotation
- Defeating access controls

Instead:

```text
detect
↓
classify
↓
back off
↓
pause when necessary
↓
record incident
↓
investigate
```

---

# 47. Provider Rate Limits

Rate limiting should be provider-specific.

Configuration may eventually include:

```yaml
max_concurrency: 2
minimum_delay_seconds: 3
```

Do not create one global rate limit for every website.

Provider limits should be determined through responsible testing and relevant provider policies.

---

# 48. Provider Onboarding Policy

Before production collection from a provider:

```text
Review robots.txt

Review relevant terms/policies

Identify whether an official API/feed exists

Understand publicly exposed data

Understand collection workflow

Determine suitable collection frequency

Determine collection method

Define provider rate limit

Define failure behavior

Define parser version

Create fixtures

Create tests

Run small pilot
```

Provider policy reviews should be repeatable because websites and policies change.

---

# 49. Security and Secrets

Never commit secrets.

`.env` must be excluded from Git.

Provide:

```text
.env.example
```

Potential secrets:

```text
DATABASE_URL

Redis credentials

cloud credentials

API keys

monitoring credentials
```

Production secrets should eventually use the cloud platform's secret-management solution.

---

# 50. Database Security

Production PostgreSQL should:

- Require authentication
- Not be publicly exposed unnecessarily
- Use encrypted connections where appropriate
- Use least-privilege credentials
- Separate application credentials from administrator credentials
- Be backed up automatically

---

# 51. Input Safety

Treat provider responses as untrusted input.

Never execute returned HTML or JSON as code.

Validate:

- URLs
- Numeric values
- Strings
- JSON structures
- External IDs

Avoid unsafe dynamic SQL.

Use SQLAlchemy parameterization.

---

# 52. Raw Artifact Safety

Raw HTML may contain scripts or malicious content.

Treat raw responses as data, not executable content.

If raw responses are later displayed in an admin dashboard, escape/sanitize them appropriately.

---

# 53. Browser Isolation

Playwright jobs should use isolated browser contexts as appropriate.

Workers must reliably close:

```text
pages
contexts
browsers
```

even after exceptions.

Use `try/finally` or equivalent cleanup.

---

# 54. Browser Resource Leaks

Monitor:

```text
RAM
CPU
open browser count
open page count
worker lifetime
```

Consider periodically recycling workers instead of allowing browser processes to live indefinitely.

---

# 55. Zombie Process Handling

Browser crashes must not leave unlimited Chrome/Chromium processes running.

Worker shutdown and failure handling must clean resources.

---

# 56. Scheduler

Initial scheduler should remain simple.

Facility fields:

```text
last_scraped_at

next_scrape_at

scrape_priority
```

The scheduler determines which facilities are due.

Do not add Redis merely to schedule the first 20 facilities.

---

# 57. Scheduling Jitter

Do not schedule every facility at exactly midnight.

Bad:

```text
00:00
50,000 jobs become due
```

Better:

```text
jobs distributed across collection window
```

Use scheduling jitter to avoid a thundering herd.

---

# 58. Future Adaptive Scheduling

Potential tiers:

```text
Tier 1
important/high-change markets
more frequent

Tier 2
normal markets
daily

Tier 3
low-change markets
less frequent
```

Do not implement until historical data supports it.

---

# 59. Queue Architecture

When needed:

```text
Scheduler
    ↓
Queue
    ↓
Worker A
Worker B
Worker C
Worker D
```

Workers should remain stateless whenever practical.

Adding workers should increase throughput without changing provider logic.

---

# 60. Poison Jobs

A malformed facility should not retry forever.

After the configured maximum retries:

```text
DEAD_LETTER
```

Store enough information to reproduce and investigate the failure.

---

# 61. Provider Isolation

A failure at Provider A must not prevent Provider B from running.

Provider-specific:

```text
rate limits

circuit breakers

health metrics

parsers

collectors

configuration
```

should remain isolated.

---

# 62. Time Handling

Store canonical timestamps in UTC.

Also retain facility timezone.

This allows later questions such as:

> What was the advertised price at 9 AM local time?

Never rely on naive timestamps for nationwide collection.

---

# 63. Consistent Observation Windows

If comparing facilities nationally, collection time may matter.

Consider eventually collecting markets within consistent local-time windows.

Do not assume a price observed at:

```text
1 AM Pacific
```

is directly equivalent to:

```text
5 PM Eastern
```

without considering provider behavior.

---

# 64. Address Normalization

Normalize addresses for matching while retaining original source values.

Examples:

```text
123 Main Street

123 Main St.

123 MAIN ST
```

may refer to the same facility.

Do not destroy original provider-provided addresses.

Store:

```text
source address
+
normalized address
```

where appropriate.

---

# 65. Geocoding

If geocoding is introduced:

- Retain source address
- Store geocoder source
- Store geocoding confidence where possible
- Detect suspicious coordinates
- Do not blindly trust geocoding output

---

# 66. A/B Tests and Site Variants

Providers may return multiple layouts or schemas.

Raw responses and fixtures should help identify:

```text
layout A

layout B
```

Parsers may need to support multiple known variants simultaneously.

---

# 67. Session State

Provider behavior may depend on:

```text
cookies

navigation history

session identifiers

location settings
```

Define session behavior explicitly per provider.

Do not accidentally let one facility's browser state contaminate another facility's collection.

---

# 68. Schema Drift

Provider JSON may change:

```text
price: 149
```

to:

```json
{
  "price": {
    "amount": 149
  }
}
```

Pydantic validation should surface this.

Provider-wide spikes in parser errors should trigger:

```text
SITE_CHANGE_SUSPECTED
```

and potentially the circuit breaker.

---

# 69. Silent Parser Degradation

The most dangerous parser is not necessarily one that crashes.

It is one that continues returning incorrect information.

Monitor distributions such as:

```text
average price

median price

products per facility

null percentage

availability percentage

promo percentage
```

Sudden shifts should create data-quality alerts.

---

# 70. Coverage Metrics

Collection success is not market coverage.

Track:

```text
known facilities

expected facilities if estimable

facilities discovered

facilities successfully scraped

facilities overdue
```

Example:

```text
Collection success:
99%

Estimated coverage:
87%
```

The second number may reveal a much larger problem.

---

# 71. Raw Diagnostic Artifacts

For abnormal failures, capture enough information to reproduce the issue.

Potential HTTP diagnostics:

```text
URL/request identifier
status
headers where appropriate
response body
timestamp
```

Potential Playwright diagnostics:

```text
screenshot
page HTML
network metadata
trace
```

Do not capture unnecessary sensitive information.

---

# 72. Testing Strategy

Testing must be a first-class part of development.

Layers:

```text
unit tests

parser fixture tests

database tests

pipeline integration tests

resilience tests

small live smoke tests

benchmark tests
```

---

# 73. Parser Fixture Tests

Store representative provider responses.

Example:

```text
tests/fixtures/provider_a/
```

Tests should verify:

```text
facility identity

number of units

dimensions

prices

availability

promotions
```

Parser tests should not require internet access.

---

# 74. Failure Simulation

Create fixtures/mocks for:

```text
normal HTTP 200

403

429

500

timeout

empty response

malformed JSON

challenge page

changed HTML

changed JSON schema

zero units

partial inventory
```

Verify correct classification and response.

---

# 75. Database Tests

Test:

```text
insert

update

upsert

constraints

foreign keys

deduplication

idempotency
```

Running:

```text
alembic upgrade head
```

against a fresh database must create the complete expected schema.

---

# 76. End-to-End Tests

Initial E2E target:

```text
known facility
    ↓
collector
    ↓
raw response
    ↓
parser
    ↓
validation
    ↓
database
```

Manually verify results against the source during early development.

---

# 77. Benchmark Testing

Test increasing concurrency:

```text
1

2

4

8

16
```

Measure:

```text
throughput

latency

RAM

CPU

failure rate

rate limiting
```

Never assume increasing concurrency improves performance.

---

# 78. Cost Measurement

Eventually track:

```text
compute cost

database cost

raw storage cost

logging cost

network cost

monitoring cost
```

Calculate:

```text
cost per 1,000 facilities collected
```

This becomes important before nationwide scaling.

---

# 79. Backups

Historical data will eventually be more valuable than the scraper code.

Production PostgreSQL must have automated backups.

Backups are not sufficient unless restore procedures are tested.

Periodically verify:

```text
backup
↓
restore
↓
database works
```

---

# 80. Implementation Roadmap

## Phase 1 — Foundation

Implement:

```text
Python project

dependencies

configuration

logging

Playwright test

HTTP test

pytest
```

Success:

A simple browser and HTTP request work correctly.

---

## Phase 2 — Provider Investigation

Select one provider.

Manually understand:

```text
facility search

facility IDs

inventory retrieval

pricing

availability

network requests
```

Document findings under:

```text
docs/providers/
```

---

## Phase 3 — Normalized Models

Create Pydantic:

```text
Facility

UnitProduct

Observation
```

Add validation tests.

---

## Phase 4 — First Collector

Implement the simplest suitable collector for one provider.

Input:

```text
facility
```

Output:

```text
raw response
```

Nothing else.

---

## Phase 5 — Raw Storage

Save representative responses.

Develop against saved responses rather than repeatedly hitting live sites.

---

## Phase 6 — Parser

Implement:

```text
raw response
↓
provider parser
↓
normalized models
```

Create fixture tests.

---

## Phase 7 — PostgreSQL

Implement:

```text
SQLAlchemy

Alembic

core tables

repositories
```

Verify database can be recreated from migrations.

---

## Phase 8 — First E2E Pipeline

Implement:

```text
scrape_facility()
```

Test approximately 10 facilities.

This is **Milestone 1**.

---

## Phase 9 — Idempotency

Run jobs multiple times.

Verify:

```text
no duplicate facilities

no unintended duplicate units

correct observation behavior
```

---

## Phase 10 — Scrape Tracking

Implement:

```text
scrape_runs

statuses

error categories

metrics
```

---

## Phase 11 — Resilience Layer

Before meaningful scale, implement:

```text
response classification

rate limiting

retry policy

exponential backoff

jitter

provider health

circuit breaker

challenge detection

failure diagnostics
```

---

## Phase 12 — Failure Tests

Simulate:

```text
403

429

500

timeout

challenge

parser failure

database failure

malformed responses
```

Ensure failures never become false market observations.

---

## Phase 13 — Facility Discovery

Automate facility discovery.

Test overlapping geographic searches and deduplication.

---

## Phase 14 — Separate Job Types

Separate:

```text
DISCOVERY JOB

FACILITY SCRAPE JOB
```

---

## Phase 15 — Scheduler

Implement database-backed scheduling.

Do not add distributed infrastructure yet.

---

## Phase 16 — Small Regional Pilot

Run:

```text
1 provider

50–200 facilities

1 metro
```

Run repeatedly.

Measure:

```text
success

coverage

data quality

latency

failures

resource usage
```

---

## Phase 17 — Benchmarking

Generate benchmark reports.

Determine:

```text
HTTP vs browser usage

optimal local concurrency

resource requirements

failure patterns
```

---

## Phase 18 — Second Provider

Add Provider #2.

This is the major architecture test.

Ideally only provider-specific:

```text
collector

parser

discovery

configuration
```

should be required.

If major shared components must be rewritten, fix architecture before continuing.

---

## Phase 19 — Local Concurrency

Increase worker concurrency gradually.

Benchmark each configuration.

---

## Phase 20 — Distributed Queue

Only after demonstrated need:

```text
Redis

worker framework
```

Test worker crashes and job recovery.

---

## Phase 21 — Docker

Containerize:

```text
application

workers

PostgreSQL

Redis
```

Use Docker Compose locally.

---

## Phase 22 — Cloud Pilot

Deploy small infrastructure.

Goal:

> Can the collector operate for seven days unattended?

Do not immediately scale nationally.

---

## Phase 23 — Monitoring

Implement dashboards/alerts for:

```text
provider health

collection health

data health

queue health

worker health

coverage

errors
```

---

## Phase 24 — Geographic Scaling

Scale one dimension at a time:

```text
metro

state

region

multiple regions

nationwide
```

Do not simultaneously add many providers and dramatically increase geography.

---

## Phase 25 — Provider Scaling

Add additional providers using the established adapter interface.

---

## Phase 26 — Analytics/API

Only once meaningful historical data exists:

```text
FastAPI

analytics

dashboard

maps

historical charts
```

---

# 81. Major Milestones

## Milestone 1

```text
1 provider
1 facility
real data extracted
```

## Milestone 2

```text
1 provider
10 facilities
PostgreSQL pipeline
tests
```

## Milestone 3

```text
1 provider
100+ facilities
scheduled collection
resilience layer
```

## Milestone 4

```text
2 providers
same shared architecture
no major rewrite
```

## Milestone 5

```text
regional deployment
hundreds/thousands of facilities
metrics
monitoring
```

## Milestone 6

```text
distributed workers
```

## Milestone 7

```text
multiple regions
multiple providers
```

## Milestone 8

```text
nationwide collection
```

## Milestone 9

```text
analytics
API
dashboard
```

---

# 82. Cursor Implementation Rules

When Cursor is eventually asked to implement this project, it should follow these principles.

### Do not build everything at once.

Implement one milestone at a time.

### Before coding a phase:

1. Explain what will be implemented.
2. Identify files that will be created/modified.
3. Identify assumptions.
4. Identify tests required.
5. Avoid unrelated refactors.

### After coding a phase:

1. Run tests.
2. Fix failures.
3. Explain implementation.
4. Explain how to manually verify it.
5. Stop before proceeding to the next major phase unless explicitly instructed.

---

# 83. Cursor Architecture Rules

Cursor should:

- Prefer simple implementations first.
- Avoid premature distributed architecture.
- Keep provider logic isolated.
- Keep collection separate from parsing.
- Keep parsing separate from persistence.
- Validate before persistence.
- Preserve data lineage.
- Make jobs idempotent.
- Write tests alongside provider parsers.
- Avoid hardcoded secrets.
- Avoid hardcoded provider-specific logic in shared modules.
- Use type hints.
- Use structured logging.
- Use database migrations.
- Handle cleanup reliably.
- Document unusual provider behavior.
- Avoid adding dependencies without justification.

---

# 84. Things Cursor Should NOT Do Without Explicit Approval

Do not automatically:

```text
introduce Kubernetes

introduce microservices

introduce multiple databases

add MongoDB

add Kafka

add Elasticsearch

add Selenium

add proxy-rotation systems

add CAPTCHA-solving systems

add browser-stealth systems

deploy infrastructure

mass-collect nationwide data

rewrite working architecture

change database technologies
```

These require an identified need and explicit architectural decision.

---

# 85. Definition of a Production-Ready Provider

A provider is not considered production-ready merely because one scrape succeeds.

A provider should have:

```text
documented discovery method

documented collection method

normalized parser

fixture tests

validation

rate policy

failure classification

retry policy

circuit breaker integration

raw diagnostic support

parser version

small-scale benchmark

regional pilot results

coverage measurement

site-policy review
```

Only then should geographic scale increase substantially.

---

# 86. Definition of Successful Collection

A successful network request is not automatically a successful scrape.

Conceptually:

```text
NETWORK SUCCESS
      ↓
EXPECTED RESPONSE
      ↓
PARSER SUCCESS
      ↓
VALIDATION SUCCESS
      ↓
DATA QUALITY SUCCESS
      ↓
DATABASE COMMIT
```

Only then should the job be considered fully successful.

---

# 87. Primary Risks

The project should continuously account for:

```text
bot detection

rate limiting

site redesigns

schema drift

A/B tests

incorrect promotional pricing

availability ambiguity

duplicate facilities

unit identity drift

coverage gaps

provider acquisitions

facility closures

address inconsistencies

timezone inconsistencies

browser memory leaks

worker crashes

retry storms

poison jobs

database bottlenecks

raw-storage growth

silent parser degradation

data corruption

backup failure

cloud cost growth

policy changes
```

---

# 88. Most Important Data Integrity Rules

These rules should be treated as architectural invariants.

### Rule 1

Never convert a failed scrape into an unavailable unit.

### Rule 2

Never assume missing inventory means sold out.

### Rule 3

Never overwrite historical observations.

Corrections should remain traceable.

### Rule 4

Never silently merge uncertain unit identities.

### Rule 5

Never discard provider source information required to understand pricing semantics.

### Rule 6

Never trust provider responses without validation.

### Rule 7

Never use collection success alone as proof of data quality.

### Rule 8

Never allow one provider failure to stop the entire platform.

### Rule 9

Never retry indefinitely.

### Rule 10

Never scale a provider substantially before its small pilot is stable.

---

# 89. Long-Term Analytics Possibilities

Once sufficient history exists, the dataset could support:

```text
average storage price by city

average price by ZIP

price per square foot

price by unit size

price by provider

price by facility

price change over time

provider comparison

market comparison

availability trends

advertised availability index

promotion frequency

price volatility

seasonality

market heat maps

facility-level price histories

regional pricing trends
```

Potential future research:

```text
relationship between advertised availability and pricing

price response to inventory changes

regional storage demand proxies

provider pricing strategies

promotion behavior

seasonal pricing patterns
```

These should remain downstream consumers of the collection platform rather than becoming tightly coupled to scraper logic.

---

# 90. Final Architecture Principle

The project should always maintain the following separation:

```text
DISCOVERY
    ↓
SCHEDULING
    ↓
COLLECTION
    ↓
SOURCE PRESERVATION
    ↓
PARSING
    ↓
NORMALIZATION
    ↓
VALIDATION
    ↓
DATA QUALITY
    ↓
PERSISTENCE
    ↓
METRICS
    ↓
ANALYTICS
```

Each stage should have a clearly defined responsibility.

The long-term goal is not:

> Build a scraper that works today.

The long-term goal is:

> Build a maintainable market-data collection system that can detect when it is wrong, explain why it failed, recover safely, preserve historical integrity, and scale from a handful of facilities to regional or nationwide coverage without requiring a fundamental rewrite.