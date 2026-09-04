# MWO-LTSA-TAP-GROUP-AGENT-001 Phase 2B-1 -- isolated container for the
# TAP LTSA WhatsApp Group Agent transport. Entirely separate image/process
# from ai5r/api -- no shared base layer content, no shared runtime.
FROM node:20-alpine
WORKDIR /app
COPY CORE-SERVICES/TAP-LTSA-GROUP-AGENT/package.json CORE-SERVICES/TAP-LTSA-GROUP-AGENT/package-lock.json ./
RUN npm ci --omit=dev
COPY CORE-SERVICES/TAP-LTSA-GROUP-AGENT/src ./src
CMD ["node", "src/index.js"]
