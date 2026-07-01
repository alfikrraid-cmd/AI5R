#!/usr/bin/env bash
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
