{{ config(materialized='view') }}

{# docs/velocity_definitions.md rule 6: width_ft / length_ft are
   self-storage-specific and must be generalized in Milestone 6. #}

{% if target.type == 'duckdb' %}
select
    id::integer as id,
    facility_id::integer as facility_id,
    identity_key::varchar as identity_key,
    provider_unit_id::varchar as provider_unit_id,
    width_ft::integer as width_ft,   -- storage-specific (M6)
    length_ft::integer as length_ft, -- storage-specific (M6)
    features::varchar as features
from {{ ref('ci_units') }}
{% else %}
select
    id,
    facility_id,
    identity_key,
    provider_unit_id,
    width_ft,   -- storage-specific (M6)
    length_ft, -- storage-specific (M6)
    features
from {{ source('raw', 'units') }}
{% endif %}
