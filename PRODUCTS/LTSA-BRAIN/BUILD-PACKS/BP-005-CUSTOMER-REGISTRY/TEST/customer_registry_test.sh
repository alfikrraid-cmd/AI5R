#!/usr/bin/env bash
# DEPRECATED (MWO-P-003 / WP-001): superseded by the per-operation functional
# tests in this directory (customer_create_test.sh, customer_detail_test.sh,
# customer_list_test.sh, customer_update_test.sh, customer_delete_test.sh,
# customer_by_code_test.sh), which assert real DB state against a controllable
# PostgreSQL instance instead of an unassorted curl call against an external,
# unverifiable host. See MWO-P-001-LTSA-Product-Audit.md backlog item 009.
# Kept only for historical reference; not part of this MWO's required tests.
set -e

BASE_URL="https://n8n.osa-system.com/webhook"

curl -X POST "$BASE_URL/ltsa/customer/create" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_code":"CUST-001",
    "customer_name":"PT TEST CUSTOMER",
    "customer_type":"company",
    "industry":"Power Plant",
    "billing_email":"finance@test.com",
    "phone":"08123456789",
    "city":"Jakarta",
    "province":"DKI Jakarta"
  }'

echo
echo "Customer Registry test executed"
