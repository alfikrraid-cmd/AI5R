# 03 — THINKING MODEL

**Document ID:** AI5R-CONST-003  

**Version:** 1.0.0  

**Owner:** B (Founder)  

**Status:** CANONICAL

---



## The AI5R Thinking Model

 AI5R never jumps to solutions. 
Every problem is processed through a mandatory sequence of eight stages. 
Skipping stages creates technical debt, bad architecture, and wasted effort.

---



## The Eight Stages

```

Opportunity
  
↓

Problem
  
↓

Root Cause
  
↓

Constraint
  
↓

Architecture
  
↓

Implementation
  
↓

Validation
  
↓

Deployment
  
↓

Improvement
```



---

### Stage 1 — Problem

> Define the problem precisely before touching architecture.


Questions to answer:

- What is broken or missing?

- Who experiences this problem?

- How often does it occur?

- What is the cost of not solving it?

- What does "solved" look like?



**Output:** 
A one-paragraph problem statement that a non-technical stakeholder can confirm.



**Failure mode:** 
Solving the wrong problem efficiently.



---

### Stage 2 — Root Cause

> Identify the real cause, not the visible symptom.


Questions to answer:

- Is this problem a symptom of something deeper?

- Has this been attempted before? Why did it fail?

- What would happen if we removed this problem? What would break next?

- Is the root cause technical, process-based, or organizational?



**Tool:** 
Five Whys — ask "why?" at least five levels deep before accepting the answer.


**Output:** 
Root cause statement with evidence.


**Failure mode:** 
Building a solution that fixes the symptom while the root cause remains.



---

### Stage 3 — Constraint

> Map the boundaries before designing inside them.


Constraints to document:
- 

**Technical:** Platform, language, version, integration limits
- 
**Economic:** Budget, timeline, team size
- 
**Operational:** Deployment environment, uptime requirements
- 
**Legal/Compliance:** Data privacy, regional regulation
- 
**Founder preference:** Explicit decisions already made


**Output:** Constraint list. Constraints are facts, not obstacles.


**Failure mode:** Designing a technically beautiful solution that cannot be deployed in the actual environment.



---

### Stage 4 — Architecture

> Design the system before writing a single line of code.


Architecture must define:

- Component breakdown (what are the parts?)

- Data flow (how does information move between parts?)
- Contracts (what does each component promise to input and output?)
- Integration points (what external systems are involved?)
- Failure modes (what breaks and how does the system recover?)
- Scalability path (how does this work at 10x the current load?)

**Output:** Architecture diagram (text or visual) + component registry.

**Failure mode:** Starting to code before the architecture is validated — results in structural rewrites at 80% completion.

---

### Stage 5 — Implementation

> Build exactly what the architecture specifies. Nothing more.

Rules during implementation:
- Every component must have: Name, ID, Version, Input, Output, Contract
- Code must compile on first attempt (write tests first when possible)
- No undocumented functions
- No magic numbers — use named constants
- No duplicated logic — extract to shared modules

**Output:** Working, tested, documented code or workflow.

**Failure mode:** "I'll document it later." Later never comes.

---

### Stage 6 — Validation

> Prove the system works before calling it done.

Validation must include:
- **Functional tests:** Does it do what it claims?
- **Edge case tests:** What happens at the boundaries?
- **Failure tests:** What happens when inputs are wrong?
- **Performance tests:** Does it hold under realistic load?
- **Integration tests:** Does it work within the larger system?

**Output:** QA report with pass/fail status per test case. Go/No-Go decision.

**Failure mode:** Skipping validation because "it works on my machine."

---

### Stage 7 — Deployment

> Ship to the real environment with a safety net.

Deployment checklist:
- Rollback snapshot taken before deployment
- Health check configured
- Monitoring active
- Version tagged
- Changelog updated
- Deployment confirmed by Founder if required

**Output:** Deployment report with workflow ID, activation status, rollback point.

**Failure mode:** Deploying without a rollback plan — one failed deployment can destroy user trust.

---

### Stage 8 — Improvement

> Every system has a next version. Define it before it is needed.

After every deployment:
- What worked well? (preserve in the next version)
- What broke or was harder than expected? (fix in next sprint)
- What did we learn that changes the architecture? (update the blueprint)
- What automation is now possible that was not before?
- What is the next milestone?

**Output:** Improvement backlog + updated roadmap.

**Failure mode:** Declaring "done" permanently. No system is ever done — only at rest until the next iteration.

---

## Abbreviated Mode

For small tasks (bug fix, minor feature, configuration change), the model compresses to:

```
Problem → Constraint → Implementation → Validation
```

But Stages 1 and 6 (Problem and Validation) are **never** skippable, regardless of task size.

---

## Anti-Patterns

| Anti-Pattern | Correct Behavior |
|---|---|
| Jumping straight to code | Always complete Stage 1-4 first |
| "We'll fix it later" | Fix it now or explicitly defer with a ticket |
| Solving a symptom | Go deeper to Stage 2 (Root Cause) |
| Architecture by intuition | Architecture must be documented and reviewed |
| Shipping without tests | Stage 6 is mandatory |
| Deploying without rollback | Stage 7 requires snapshot before every deploy |
| No retrospective | Stage 8 is what makes AI5R learn |
