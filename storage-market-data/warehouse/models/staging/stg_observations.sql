{{ config(materialized='view') }}

{# docs/velocity_definitions.md rule 6: standard_price / promo_price are
   per-unit monthly asking prices (self-storage), not a universal price
   unit. Generalize in Milestone 6. #}

{% if target.type == 'duckdb' %}
select
    id::integer as id,
    unit_id::integer as unit_id,
    scraped_at::timestamptz as scraped_at,
    standard_price::integer as standard_price, -- storage monthly asking (M6)
    promo_price::integer as promo_price,       -- storage monthly asking (M6)
    availability_status::varchar as availability_status,
    availability_text::varchar as availability_text,
    free_first_month::boolean as free_first_month,
    parse_strategy::varchar as parse_strategy
from {{ ref('ci_observations') }}
{% else %}
select
    id,
    unit_id,
    scraped_at,
    standard_price, -- storage monthly asking (M6)
    promo_price,    -- storage monthly asking (M6)
    availability_status,
    availability_text,
    free_first_month,
    parse_strategy
from {{ source('raw', 'observations') }}
{% endif %}
