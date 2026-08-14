# AI5ROS Production Volume Mapping

The canonical compose file owns final runtime volumes through
`AI5R_VOLUME_PREFIX`. Production migration should map existing production
data into these final names, then retire legacy runtime volumes only after
acceptance.

| Service | Canonical volume | Existing production source | Decision |
|---|---|---|---|
| PostgreSQL | `${AI5R_VOLUME_PREFIX}-postgres-data` | Existing production PostgreSQL volume/database | Reuse or migrate after backup. |
| Redis | `${AI5R_VOLUME_PREFIX}-redis-data` | Existing production Redis volume/data | Reuse or migrate after backup. |
| n8n | `${AI5R_VOLUME_PREFIX}-n8n-data` | Existing standalone/legacy n8n volume | Migrate for n8n files/config; internal n8n database tables are in PostgreSQL `AI5R_POSTGRES_DB`. |
| MinIO | `${AI5R_VOLUME_PREFIX}-minio-data` | Existing MinIO data if present | Reuse if live data exists; otherwise initialize canonical volume. |
| Neo4j data | `${AI5R_VOLUME_PREFIX}-neo4j-data` | Existing Neo4j data if present | Retain only when production dependency is confirmed. |
| Neo4j logs | `${AI5R_VOLUME_PREFIX}-neo4j-logs` | Existing Neo4j logs if present | Retain only with Neo4j. |
| Neo4j plugins | `${AI5R_VOLUME_PREFIX}-neo4j-plugins` | Existing Neo4j plugins if present | Retain only with Neo4j. |

## Ownership Rules

- Final owner is always `CORE-SERVICES/RUNTIME/compose.yaml`.
- Legacy volumes are never deleted until backup validation and production
  acceptance are complete.
- Anonymous Docker volumes are inspected and either documented or retired.
- Gotenberg is stateless and owns no persistent volume.