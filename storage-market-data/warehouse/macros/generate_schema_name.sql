{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if target.type == 'duckdb' -%}
        main
    {%- elif custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        storage_market_data_{{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
