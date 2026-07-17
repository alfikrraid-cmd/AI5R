# MO-001 — OSA Maintenance v0.1 — Demo Script

For CV Razzan Teknik Mandiri, internal demonstration.

## Prerequisite

Complete `DEPLOYMENT-GUIDE.md` steps 1–2 (database schema applied, n8n workflows imported and active), or run the Basic AI Assistant step (step 5 below) standalone — it requires neither.

## 1. Register a customer

```
curl -X POST http://localhost:5678/webhook/ltsa/customer/create \
  -H "Content-Type: application/json" \
  -d '{"customer_code": "RAZZAN-001", "customer_name": "CV Razzan Teknik Mandiri"}'
```

## 2. Register an asset

```
curl -X POST http://localhost:5678/webhook/ltsa/asset/create \
  -H "Content-Type: application/json" \
  -d '{"asset_code": "TANK-01", "asset_name": "Feedwater Tank", "asset_type": "TANK", "area": "Boiler House"}'
```

## 3. Register a soot blower

```
curl -X POST http://localhost:5678/webhook/ltsa/soot-blower/create \
  -H "Content-Type: application/json" \
  -d '{"soot_blower_code": "SB-01", "soot_blower_name": "Retractable Blower Unit 1", "boiler_area": "Boiler House"}'
```

## 4. Open a Work Order against the soot blower

```
curl -X POST http://localhost:5678/webhook/ltsa/work-order/create \
  -H "Content-Type: application/json" \
  -d '{"work_order_code": "WO-001", "customer_code": "RAZZAN-001", "asset_code": "SB-01", "asset_type": "soot_blower", "description": "High vibration reported on soot blower unit", "priority": "HIGH"}'
```

## 5. Ask the Basic AI Assistant for a recommendation (standalone, no server required)

```
python -c "
from pathlib import Path
import sys
sys.path.insert(0, str(Path('PRODUCTS/LTSA-BRAIN/AI-ASSISTANT')))
from maintenance_assistant import get_maintenance_recommendation
import json
print(json.dumps(get_maintenance_recommendation(
    asset_code='SB-01',
    findings_text='Vibration 11.2 mm/s, bearing temperature 92 C, seal leakage observed',
    vibration=11.2, temperature=92, findings=['seal_leakage', 'bearing'],
), indent=2))
"
```

Expected output shape (this is the actual output captured during manufacturing — see `MO-001-MANUFACTURING-REPORT.md`):
```json
{
  "asset_code": "SB-01",
  "selected_hypothesis": {
    "name": "mechanical_instability",
    "description": "High vibration may indicate imbalance, misalignment, or bearing wear.",
    "confidence": 0.82
  },
  "rationale": "Selected because it has the highest confidence among generated hypotheses.",
  "recommendation": "Execution completed successfully. Current enterprise reasoning is reinforced.",
  "confidence_delta": 0.1,
  "knowledge_update_required": false
}
```

## 6. Log the completed maintenance action

```
curl -X POST http://localhost:5678/webhook/ltsa/maintenance-history/create \
  -H "Content-Type: application/json" \
  -d '{"maintenance_record_code": "MH-001", "work_order_code": "WO-001", "asset_code": "SB-01", "asset_type": "soot_blower", "action_taken": "Replaced worn bearing", "performed_by": "Technician A"}'
```

## 7. Close the Work Order

```
curl -X PUT http://localhost:5678/webhook/ltsa/work-order/update \
  -H "Content-Type: application/json" \
  -d '{"work_order_code": "WO-001", "status": "CLOSED", "closed_at": "2026-07-13T00:00:00Z"}'
```

## 8. View the Dashboard

Open `PRODUCTS/LTSA-BRAIN/BUILD-PACKS/BP-DASHBOARD/dashboard.html` in a browser, point it at the n8n instance, click "Load Summary" — it should now show 1 customer, 1 asset, 1 soot blower, 1 work order, 1 maintenance history record.
