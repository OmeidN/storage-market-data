{{ config(materialized='view') }}

{# docs/velocity_definitions.md — typed mirror of Postgres facilities. #}

{% if target.type == 'duckdb' %}
select
    id::integer as id,
    provider::varchar as provider,
    slug::varchar as slug,
    url::varchar as url,
    name::varchar as name,
    address::varchar as address,
    created_at::timestamptz as created_at
from {{ ref('ci_facilities') }}
{% else %}
select
    id,
    provider,
    slug,
    url,
    name,
    address,
    created_at
from {{ source('raw', 'facilities') }}
{% endif %}
