{% macro days_between(later, earlier) %}
  {# Calendar-day span between two timestamps. DuckDB vs BigQuery. #}
  {% if target.type == 'bigquery' %}
    timestamp_diff({{ later }}, {{ earlier }}, day)
  {% else %}
    date_diff('day', {{ earlier }}, {{ later }})
  {% endif %}
{% endmacro %}
