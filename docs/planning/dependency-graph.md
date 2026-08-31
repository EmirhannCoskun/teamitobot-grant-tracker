# Implementation Dependency Graph

Architecture freeze date: 2026-08-31

The `Dependencies` field of each package in the
[Team Implementation Plan](team-implementation-plan.md) is authoritative. The
Mermaid DAG preserves the same ordering but may omit a redundant direct edge
when that prerequisite is already reachable through another dependency path.

## Mermaid DAG

```mermaid
flowchart TD
    FZ[FZ-001 Architecture Freeze]
    DV1[DV-001 Runtime + Fast CI]

    DV2[DV-002 PostgreSQL Harness]
    BL1[BL-001 Provider Baseline]
    BL2[BL-002 Telegram Baseline]
    BL3[BL-003 Persistence Baseline]
    BL4[BL-004 Lifecycle Baseline]
    PK[PK-001 Project Metadata]

    MG[MG-001 Alembic Baseline]
    ID1[ID-001 Identity Contract]
    CF[CF-001 Typed Config]
    TG1[TG-001 Telegram Renderer]

    PV[PV-001 Provider Adapter]
    ID2[ID-002 Identity Migration]
    ID3[ID-003 Occurrence Repository]
    OB1[OB-001 Outbox Migration]

    OB2[OB-002 Claim + Lease Repository]
    OB3[OB-003 Atomic Fan-out Transaction]
    OB4[OB-004 Dispatcher + Retry]
    AP1[AP-001 Collection Use Case]
    AP2[AP-002 Subscription Use Cases]
    TG2[TG-002 Telegram Handlers]

    OB5[OB-005 Crash/Concurrency Tests]
    EX[EX-001 Composition Root]
    OP[OP-001 Logs + Readiness]

    CI[CI-001 Full CI Gates]
    TS[TS-001 Token Replacement]
    DV3[DV-003 Dependency Upgrades]

    RS[RS-001 Repository Consolidation]
    ST1[ST-001 Migration Rehearsal]
    ST2[ST-002 Staging Validation]
    CL[CL-001 Contract Cleanup]

    FZ --> DV1
    DV1 --> DV2
    DV1 --> BL1
    DV1 --> BL2
    DV1 --> BL4
    DV1 --> PK
    DV2 --> BL3

    BL3 --> MG
    BL1 --> ID1
    BL4 --> CF
    BL2 --> TG1

    ID1 --> PV
    ID1 --> ID2
    MG --> ID2
    ID2 --> ID3
    ID2 --> OB1

    OB1 --> OB2
    ID3 --> OB3
    OB1 --> OB3
    BL3 --> OB3
    OB2 --> OB4
    TG1 --> OB4
    BL2 --> OB4

    PV --> AP1
    ID3 --> AP1
    OB3 --> AP1
    BL2 --> AP2
    BL3 --> AP2
    OB1 --> AP2
    AP2 --> TG2
    TG1 --> TG2

    OB2 --> OB5
    OB3 --> OB5
    OB4 --> OB5
    CF --> EX
    AP1 --> EX
    TG2 --> EX
    OB4 --> EX
    EX --> OP
    OB5 --> OP

    DV1 --> CI
    DV2 --> CI
    MG --> CI
    OB1 --> CI
    PK --> CI
    CF --> TS
    BL1 --> DV3
    BL2 --> DV3
    BL3 --> DV3
    CI --> DV3

    TS --> RS
    PK --> RS
    EX --> RS
    CI --> RS

    ID2 --> ST1
    OB1 --> ST1
    OB3 --> ST1
    MG --> ST1

    RS --> ST2
    ST1 --> ST2
    OB5 --> ST2
    OP --> ST2
    CI --> ST2
    DV3 --> ST2
    ST2 --> CL

    classDef contract fill:#ffe0b2,stroke:#e65100,stroke-width:2px;
    classDef parallel fill:#e3f2fd,stroke:#1565c0;
    classDef gate fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px;
    class FZ,DV1,MG,ID1,ID2,OB1 contract;
    class DV2,BL1,BL2,BL3,BL4,PK,CF,TG1,PV,ID3,OB2,OB3,OB4,AP1,AP2,TG2,CI,TS,DV3 parallel;
    class OB5,EX,OP,RS,ST1,ST2,CL gate;
```

## Critical path

```text
FZ-001
-> DV-001
-> DV-002
-> BL-003
-> MG-001
-> ID-002
-> OB-001
-> OB-003
-> AP-001
-> EX-001
-> RS-001
-> ST-002
```

ID-001 must merge before ID-002 and runs through the provider-baseline branch of the graph. OB-002/004/005 form the parallel reliability branch that must also reach ST-002.

## Blocking contracts versus parallel work

| Blocking contract | Why it blocks | Work enabled after merge |
| --- | --- | --- |
| FZ-001 | Prevents incompatible architecture assumptions | All implementation |
| DV-001 | Defines supported runtime and minimum PR checks | All baseline branches |
| MG-001 | Establishes actual migration head/schema truth | Identity/outbox revisions |
| ID-001 | Defines identity normalization/result semantics | Provider adapter, identity schema/repository |
| ID-002 | Defines occurrence/alias persistence and preserves data | Occurrence repo and outbox FK migration |
| OB-001 | Defines payload/state/retry/lease contract | Claim repo, atomic fan-out, subscriptions, CI migration gates |
| CF-001 | Defines canonical secret/settings interface | Composition root and token replacement |
| EX-001 | Defines final process lifecycle/entry point | Operations and repository deployment cutover |
| RS-001 | Defines canonical repository/artifact | Final staging/release validation |

Parallel branches are safe only when they consume merged contracts and avoid the same migration head or high-conflict legacy file. If two packages both need `bot.py`/`database.py`, prefer compatibility modules or sequence the edits even when the logical work is parallel.

## Suggested team lanes

| Lane | Capability | Typical packages |
| --- | --- | --- |
| A | Architecture/Domain | FZ-001, ID-001, CF-001, AP-001, AP-002, EX-001 |
| B | Backend/Persistence | BL-003, MG-001, PV-001, ID-002/003, OB-001/002/003, ST-001, CL-001 |
| C | Integration/Telegram | BL-002, TG-001/002, OB-004, TS-001 |
| D | QA/DevEx | DV-001/002/003, BL-001/004, PK-001, OB-005, OP-001, CI-001, RS-001, ST-002 |

Lanes are capability groupings, not fixed developer assignments. Contract reviews should include at least the upstream contract owner and one downstream implementer.
