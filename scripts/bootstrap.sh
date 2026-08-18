#!/usr/bin/env bash
#
# Provision and seed a CockroachDB Cloud database using ccloud connection details.
#
#   ccloud auth login
#   export CRDB_SQL_PASSWORD='...'
#   ./scripts/bootstrap.sh
#
# Database creation, schema creation, and seed inserts are guarded for repeated runs.

set -euo pipefail

CLUSTER="${CLUSTER:-ashtray}"
DATABASE="${DATABASE:-omninpc}"
SQL_USER="${SQL_USER:-LesterCrest}"

die() { echo "error: $*" >&2; exit 1; }

command -v ccloud >/dev/null || die "ccloud not installed: brew install cockroachdb/tap/ccloud"
command -v psql   >/dev/null || die "psql not installed: brew install libpq"
[[ -n "${CRDB_SQL_PASSWORD:-}" ]] || die "set CRDB_SQL_PASSWORD to the SQL user's password"

ccloud auth whoami >/dev/null 2>&1 || die "not logged in: run 'ccloud auth login'"
echo "authenticated as: $(ccloud auth whoami 2>/dev/null)"

echo "cluster: $CLUSTER"
ccloud cluster info "$CLUSTER" --quiet 2>/dev/null | sed 's/^/  /'

if ccloud cluster database list "$CLUSTER" --quiet 2>/dev/null | awk '{print $1}' | grep -qx "$DATABASE"; then
    echo "database '$DATABASE' already exists"
else
    echo "creating database '$DATABASE'"
    ccloud cluster database create "$CLUSTER" "$DATABASE" --quiet
fi

# Take the host and TLS parameters from ccloud, then substitute the credentials locally.
TEMPLATE=$(ccloud cluster connection-string "$CLUSTER" \
    --database "$DATABASE" --sql-user "$SQL_USER" --quiet 2>/dev/null \
    | grep '^postgresql://' | head -1)
[[ -n "$TEMPLATE" ]] || die "could not derive a connection string from ccloud"

HOSTPART=${TEMPLATE#*@}
URL="postgresql://${SQL_USER}:${CRDB_SQL_PASSWORD}@${HOSTPART}"
echo "target: ${TEMPLATE//$SQL_USER/<user>}"

echo "applying schema/init.sql"
psql "$URL" -q -v ON_ERROR_STOP=1 -f schema/init.sql
echo "applying schema/seed.sql"
psql "$URL" -q -v ON_ERROR_STOP=1 -f schema/seed.sql

echo
echo "verifying:"
psql "$URL" -X -q -t -A -F' ' -c "
  SELECT 'vector index', count(*) FROM [SHOW INDEXES FROM memory_embeddings]
   WHERE index_name = 'memory_embeddings_vec_idx'
  UNION ALL SELECT 'branches', count(*) FROM branches
  UNION ALL SELECT 'npcs', count(*) FROM npcs
  UNION ALL SELECT 'players', count(*) FROM players;" | sed 's/^/  /'

echo
echo "done. set this in backend/.env (with the password):"
echo "  COCKROACHDB_URL=${TEMPLATE}"
