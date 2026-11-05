# AWS Professional Level — Why Each Topic, and What They'll Ask

Covers both Professional tracks: **Solutions Architect – Professional (SAP-C02)** and **DevOps Engineer – Professional (DOP-C02)**. Same pattern as the associate doc: why it exists, the trade-off, and the questions.

These exams assume years of running production systems. Most of this is answered conceptually, not from a lab — say so when asked.

---

# Part 1 — Solutions Architect Professional

## Multi-account architecture

### AWS Organizations

**What:** a management account with member accounts underneath, grouped into organisational units, with consolidated billing.

**Why:** hard blast-radius boundaries. A mistake in dev cannot touch production, because they're different accounts. Also gives volume pricing across the whole organisation and one place to apply policy.

**Trade-off:** more moving parts — cross-account roles, shared networking and centralised logging all need designing.

**Q: Why separate accounts instead of separate VPCs?**
Isolation strength. A VPC separates network, but IAM, service quotas and blast radius are still shared. Separate accounts give a hard boundary for permissions, limits and billing, and make it possible to hand an account to a team without risking anything else.

**Q: Typical account layout?**
Management account (billing and Organizations only, no workloads), plus separate accounts for security/audit, shared services, logging, and one per environment — dev, staging, production. Production is usually the most locked down.

### SCPs — Service Control Policies

**What:** organisation-level guardrails that cap what any principal in an account may do, including root.

**Why:** they set a ceiling that local admins cannot raise. Useful for "no one may disable CloudTrail" or "only these regions may be used."

**Q: SCP vs IAM policy?**
An SCP doesn't grant anything — it limits the maximum. Effective permission is the intersection of the SCP and the identity policy. If either denies, access is denied.

### Control Tower

**What:** an opinionated setup for a multi-account landing zone — account factory, baseline guardrails, centralised logging.

**Q: When would you use it?**
When an organisation is starting multi-account and wants a standard, compliant baseline quickly instead of building the landing zone by hand.

### Cross-account access

**Q: How do accounts share access safely?**
Roles assumed across accounts, with a trust policy naming the source account, ideally with an external ID and MFA condition. Never long-lived access keys shared between accounts.

**Q: How do you centralise logging?**
CloudTrail and Config from all accounts delivered to a dedicated log-archive account, write-only, with object lock so logs cannot be deleted even by an attacker with admin in the source account.

---

## Hybrid and advanced networking

### Direct Connect

**What:** a dedicated physical circuit from a data centre to AWS.

**Why:** consistent latency and bandwidth, and lower data transfer cost at volume. A VPN over the internet cannot promise either.

**Trade-off:** weeks to provision, ongoing port cost, and a single circuit is a single point of failure — production needs two, ideally at different locations.

**Q: Direct Connect or VPN?**
VPN for quick setup, low cost and modest traffic — it runs over the internet, so latency varies. Direct Connect for predictable performance and large sustained transfer. Common pattern: Direct Connect as primary, VPN as backup.

### Transit Gateway

**What:** a hub that connects many VPCs, VPNs and Direct Connect links.

**Why:** VPC peering doesn't scale — twenty VPCs fully meshed is 190 connections, and peering isn't transitive. Transit Gateway makes it a hub-and-spoke with route tables.

**Q: Peering vs Transit Gateway vs PrivateLink?**
Peering for a couple of VPCs needing full network access, cheapest. Transit Gateway when there are many VPCs or hybrid links, at a per-attachment and per-GB cost. PrivateLink when you only want to expose one service, not join networks — the consumer reaches an endpoint, with no routing between VPCs at all.

**Q: How do you handle overlapping CIDR ranges after an acquisition?**
Networks with the same range can't be routed together. Options are re-addressing one side, or using PrivateLink or NAT to expose only specific services rather than joining the networks.

---

## Migration

### The 7 Rs

Rehost (lift and shift), Replatform (small optimisations in flight), Repurchase (move to SaaS), Refactor (rewrite for cloud), Retire, Retain, Relocate.

**Q: How would you migrate 200 servers?**
Discovery first — dependencies, traffic, ownership. Then group into waves, starting with low-risk systems to build confidence. Rehost most of it, because refactoring everything up front is how migrations stall. Replatform where there's an easy win, such as moving a database to RDS. Retire what nobody uses — usually a surprising share.

**Q: Database migration with minimal downtime?**
DMS with change data capture: full load, then ongoing replication, then a short cutover once lag is near zero. Schema conversion first if the engine is changing.

**Q: Biggest risk in a migration?**
Unknown dependencies. Something always talks to the thing you moved, and nobody documented it. Discovery tooling and a rollback plan for each wave.

---

## Multi-region and disaster recovery

### The four DR patterns

| Pattern | RTO | Cost |
|---|---|---|
| Backup and restore | Hours | Lowest |
| Pilot light | Tens of minutes | Low |
| Warm standby | Minutes | Medium |
| Multi-site active-active | Near zero | Highest |

**Q: How do you choose?**
Start from RTO and RPO agreed with the business, then pick the cheapest pattern that meets them. Most systems don't need active-active, and paying for it without the requirement is a common mistake.

**Q: What makes multi-region hard?**
Data. Compute is easy to duplicate; consistent state across regions is not. Asynchronous replication means data loss on failover; synchronous means latency. Aurora Global Database and DynamoDB global tables solve parts of this with their own trade-offs.

**Q: How does traffic fail over?**
Route 53 health checks with failover routing, or Global Accelerator for faster convergence. Remember DNS TTLs — clients cache, so failover isn't instant.

---

## Security at scale

**Q: How do you manage identity for hundreds of staff?**
Federate with the existing identity provider through IAM Identity Center. No individual IAM users; people assume roles with short-lived credentials, and leavers are removed at the IdP.

**Q: How do you detect and respond to incidents across accounts?**
GuardDuty for threat detection, Security Hub to aggregate findings, Config for compliance drift, CloudTrail to a locked log account. Responses automated with EventBridge to Lambda — for example, quarantine an instance when a finding fires.

**Q: How do you protect against credential leaks?**
Roles over keys everywhere, short session lifetimes, secret scanning in CI, automatic rotation, and SCPs preventing key creation where it isn't needed.

---

## Cost governance at scale

**Q: How do you control cost across many accounts?**
Mandatory tagging enforced through policy, Cost Explorer and Cost and Usage Reports grouped by tag and account, budgets per team with alerts, and a Savings Plan strategy at the organisation level since commitments apply across accounts.

**Q: Savings Plans vs Reserved Instances vs Spot?**
Savings Plans commit to hourly spend and are flexible across instance families and regions. RIs are tied to a specific configuration but can be sold in the marketplace. Spot is spare capacity at a steep discount, interruptible with two minutes' notice — fine for batch, bad for a database.

---

# Part 2 — DevOps Engineer Professional

## Deployment strategies

**Q: Blue/green vs canary vs rolling?**
Blue/green stands up a whole parallel environment and switches traffic at once — instant rollback, but double the resources. Canary shifts a small percentage first and watches metrics before continuing — limits blast radius, and needs good monitoring. Rolling replaces instances in batches — no extra cost, but both versions run together, so the app must tolerate that.

**Q: How do you make deployments safe?**
Automated rollback triggered by alarms, not a human watching a dashboard. Health checks that test the app, not just the port. Database migrations that are backwards compatible so the old version still runs during the rollout.

**Q: How do you handle a database schema change in a zero-downtime deploy?**
Expand and contract. Add the new column, deploy code that writes both and reads the old, backfill, deploy code that reads the new, then remove the old column in a later release. Never a breaking schema change in the same deploy as the code that needs it.

---

## Infrastructure as code

**Q: Terraform or CloudFormation?**
CloudFormation is native, supports StackSets across accounts and drift detection, and needs no state management. Terraform is multi-cloud with a larger module ecosystem and, for most teams, better ergonomics — the cost is managing remote state and locking. Either is fine; not using one is the problem.

**Q: What is drift and why does it matter?**
Someone changed something in the console, so reality no longer matches code. The next deploy either overwrites their fix or fails. Detect it automatically and either codify the change or revert it.

**Q: How do you structure IaC for multiple environments?**
Same modules, different variable files per environment, separate state per environment. Environments differ only in parameters — that's what makes staging meaningful.

---

## Pipelines at scale

**Q: How do you deploy to multiple accounts from one pipeline?**
The pipeline account assumes a deployment role in each target account. Short-lived credentials, no keys, and each target's trust policy names only the pipeline role.

**Q: How do you keep pipelines fast?**
Parallel jobs, cached dependencies, and only building what changed in a monorepo. Run the slow tests after the fast ones so failures come back early.

**Q: What belongs in the pipeline besides tests?**
Linting, dependency and container scanning, secret scanning, IaC policy checks, and a manual approval gate before production.

---

## Observability and incident response

**Q: Metrics, logs, traces — what's each for?**
Metrics tell you something is wrong. Logs tell you what happened. Traces tell you where, across services. You need all three; alerting on metrics alone leaves you guessing.

**Q: What do you alert on?**
Symptoms users feel — error rate, latency, availability — not causes like CPU. Alerts must be actionable; anything that fires and gets ignored should be deleted or fixed.

**Q: How do you automate incident response?**
EventBridge rules on alarms and findings triggering Lambda or Systems Manager runbooks: isolate an instance, roll back a deploy, scale out, open a ticket. The runbook should be code, not a wiki page someone reads at 3am.

---

## Configuration and compliance automation

**Q: How do you patch a fleet?**
Systems Manager Patch Manager with maintenance windows and patch baselines, reporting compliance centrally. Better still, immutable infrastructure: bake a new AMI, roll it out, terminate the old ones — no patching in place at all.

**Q: How do you enforce compliance continuously?**
AWS Config rules for the checks, auto-remediation for the ones that are safe to fix automatically, Security Hub for the overall picture, and SCPs to make the worst actions impossible rather than merely detectable.

**Q: Mutable vs immutable infrastructure?**
Mutable means changing servers in place, which causes drift — servers become unique and unreproducible. Immutable means replacing them from a known image, so every server is identical and rollback is deploying the previous image.

---

## Containers and serverless at scale

**Q: ECS or EKS?**
ECS is simpler, AWS-native, and enough for most teams. EKS is Kubernetes — portable, huge ecosystem, far more operational overhead. Choose EKS if you need Kubernetes specifically, not by default.

**Q: Fargate or EC2 launch type?**
Fargate removes node management and bills per task, which suits spiky or small workloads. EC2 is cheaper at sustained scale and allows GPU or custom kernel needs, at the cost of managing the cluster.

**Q: How do you handle serverless cold starts?**
Provisioned concurrency for latency-sensitive paths, smaller deployment packages, and avoiding VPC attachment where it isn't needed. Also question whether the workload suits serverless at all.

---

## Answering at this level

Most of this you'll be describing rather than recalling. Three phrasings that work:

- *"I haven't run this at scale. The trade-off as I understand it is X versus Y, and I'd choose based on Z."*
- *"I've done the single-account version of this. At scale the difference is X."*
- *"That depends on the RTO and RPO. If they can tolerate an hour, I'd do A; if it's minutes, B, and it costs considerably more."*

Naming the trade-off is what signals seniority. Nobody expects a WordPress developer to have designed a multi-region migration — being able to discuss it sensibly is already more than the role requires.
