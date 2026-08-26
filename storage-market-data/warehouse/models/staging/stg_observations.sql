{{ config(materialized='view') }}

{# docs/velocity_definitions.md rule 6: price / price_unit /
   price_data_available are the universal asking fields. #}

{% if target.type == 'duckdb' %}
select
    id::integer as id,
    unit_id::integer as unit_id,
    scraped_at::timestamptz as scraped_at,
    price::integer as price,
    price_unit::varchar as price_unit,
    price_data_available::boolean as price_data_available,
    standard_price::integer as standard_price,
    promo_price::integer as promo_price,
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
    price,
    price_unit,
    price_data_available,
    standard_price,
    promo_price,
    availability_status,
    availability_text,
    free_first_month,
    parse_strategy
from {{ source('raw', 'observations') }}
{% endif %}
