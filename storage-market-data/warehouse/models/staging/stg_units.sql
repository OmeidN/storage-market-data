{{ config(materialized='view') }}

{# docs/velocity_definitions.md rule 6: marts use square_footage.
   width_ft / length_ft remain for storage-only debugging. #}

{% if target.type == 'duckdb' %}
select
    id::integer as id,
    facility_id::integer as facility_id,
    identity_key::varchar as identity_key,
    provider_unit_id::varchar as provider_unit_id,
    square_footage::integer as square_footage,
    width_ft::integer as width_ft,
    length_ft::integer as length_ft,
    features::varchar as features,
    attributes::varchar as attributes,
    price_data_available::boolean as price_data_available
from {{ ref('ci_units') }}
{% else %}
select
    id,
    facility_id,
    identity_key,
    provider_unit_id,
    square_footage,
    width_ft,
    length_ft,
    features,
    attributes,
    price_data_available
from {{ source('raw', 'units') }}
{% endif %}
