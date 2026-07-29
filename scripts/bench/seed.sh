#!/usr/bin/env bash
# doubles rows in plays/requests (INSERT ... SELECT with fresh UUIDs) until each
# table reaches TRACKIFY_BENCH_TARGET rows.
set -euo pipefail
: "${DB_NAME:?}" "${MYSQL:?}"

target="${TRACKIFY_BENCH_TARGET:-500000}"

tables="plays:id,time_started,time_ended,user_id,track_id,device_id,context_uri,volume_percent
requests:id,time_added,ip,url,headers,request_data,form,referrer,access_route,user_id"

while IFS= read -r table_cols; do
  table="${table_cols%%:*}"
  cols="${table_cols#*:}"
  select_cols=$(echo "$cols" | sed 's/^id,/UUID(),/')

  count=$($MYSQL -N -e "SELECT COUNT(*) FROM $DB_NAME.$table;")
  if [ "$count" -eq 0 ]; then
    echo "$table is empty, skipping (clone a dataset into it first)"
    continue
  fi

  echo "growing $table from $count to >= $target rows ..."
  while [ "$count" -lt "$target" ]; do
    $MYSQL -e "INSERT INTO $DB_NAME.$table ($cols) SELECT $select_cols FROM $DB_NAME.$table;"
    count=$($MYSQL -N -e "SELECT COUNT(*) FROM $DB_NAME.$table;")
    echo "  $table: $count rows"
  done
done <<< "$tables"
