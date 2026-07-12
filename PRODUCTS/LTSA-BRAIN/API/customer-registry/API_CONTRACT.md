# BP-005 Customer Registry API Contract

## Module
Customer Registry

## Endpoints

POST /webhook/ltsa/customer/create  
GET /webhook/ltsa/customer/list  
GET /webhook/ltsa/customer/get?id={id}  
PUT /webhook/ltsa/customer/update  
DELETE /webhook/ltsa/customer/delete?id={id}  
GET /webhook/ltsa/customer/by-code?code={customer_code}

`by-code` documented in MWO-P-003 / WP-006: implemented at `BUILD-PACKS/BP-007-AI5R-WORKFLOW-GENERATOR/OUTPUTS/WF-LTSA-CUSTOMER-BY-CODE-001.json`, previously an undocumented orphan artifact (see `IR-002-Workflow-Report.md`). Returns the same record shape as `get`, looked up by `customer_code` instead of `id`.

## Required Fields

- customer_code
- customer_name

## Create Payload

{
  "customer_code": "CUST-001",
  "customer_name": "PT Contoh Industri",
  "customer_type": "company",
  "industry": "Manufacturing",
  "billing_email": "finance@contoh.co.id",
  "phone": "08123456789",
  "city": "Jakarta",
  "province": "DKI Jakarta"
}

## Definition of Done

- Create customer works
- List customer works
- Get customer by id works
- Update customer works
- Delete customer works
- Get customer by code works

