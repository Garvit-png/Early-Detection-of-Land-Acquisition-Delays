# SIH Feature Mapping

Maps project features to their interpretation/relevance for land-acquisition delay risk. Use as model/context documentation.

| Mapping_ID | Feature | Rationale | Model_Use | Evidence_Strength | Prototype_Action |
| --- | --- | --- | --- | --- | --- |
| FM-01 | Compensation_Paid_Percent | Low compensation completion is a direct operational warning signal supported by audit evidence. | Delay probability + recommendation | High | Escalate payment blockers; check funding and notice delivery. |
| FM-02 | RR_Completion_Percent | R&R is a defined part of the land-acquisition framework and can remain incomplete even while acquisition progresses. | Stage risk + recommendation | High | Prioritize pending R&R actions and affected-family follow-up. |
| FM-03 | Legal_Cases | Disputes can block compensation and acquisition progress. | Delay probability + legal risk | High | Track unresolved dispute count and age; legal review/escalation. |
| FM-04 | Ownership_Conflicts | Ownership/record issues can complicate compensation and future transfer. | Delay probability + documentation risk | High | Verify records, mutation status, and affected-interest mapping. |
| FM-05 | Documentation_Percent | Audit evidence shows record, survey, notice and asset-data deficiencies. | Delay probability + data-quality risk | High | Trigger document/survey validation before next milestone. |
| FM-06 | Stakeholder_Response_Percent | Objections, resistance and communication gaps can create delay. | Delay probability + stakeholder risk | Medium-High | Increase engagement, resolve objections, improve notice tracking. |
| FM-07 | Current_Stage | Risk drivers differ by lifecycle stage. | Stage-wise risk | High | Use stage-specific thresholds/models rather than one global checklist. |
| FM-08 | Affected_Families | Larger affected populations can increase coordination and R&R complexity; use cautiously as one factor. | Prediction feature | Medium | Combine with R&R progress and stakeholder indicators. |
| FM-09 | Land_Extent_Hectares | Large acquisition footprints can increase operational complexity; use cautiously as contextual feature. | Prediction feature | Medium | Combine with stage, records, and milestone delays. |
| FM-10 | Possession_Date | Possession/hand-over is a critical milestone connected to compensation and project execution. | Stage dependency | High | Flag missing/overdue handover milestone. |
| FM-11 | Milestone_Delay_Days | Government audit examples show concrete delays at award/payment/requisition milestones. | Prediction + monitoring | High | Calculate elapsed days against project milestone targets. |
| FM-12 | Funding_Readiness | CAG identifies non-receipt of funds as a cause of compensation non-disbursement. | Production feature | High | Add requiring-body funding readiness to production data model. |
| FM-13 | Notice_Delivery_Percent | Incomplete notice delivery can lead to grievances and delayed processing. | Production feature | Medium-High | Monitor undelivered notices and affected-person coverage. |
| FM-14 | Mutation_Completion_Percent | Delayed ownership transfer can create legal risk after acquisition. | Production feature | Medium | Track record mutation/ownership transfer after acquisition. |
