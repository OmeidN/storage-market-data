{{ config(materialized='view') }}

{# docs/velocity_definitions.md rule 5. Seed is keyed by provider+slug. #}

select
    provider,
    slug,
    market_name
from {{ ref('facility_market_map') }}
{% if target.type == 'duckdb' %}
union all
select
    provider,
    slug,
    market_name
from {{ ref('ci_facility_market_map') }}
{% endif %}
