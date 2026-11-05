# AWS — Foundational to Professional, in One Place

Everything in one file, in learning order. Each entry: **what it is**, **why you'd use it**, **the trade-off**, **how it maps to your WordPress stack**, and **the interview questions**.

Account: `akshat-wp-lab` · Mumbai `ap-south-1` · Free plan, $100 credits
Session rule: spin up → learn → note it down → delete → check Billing.

---

# LEVEL 1 — FOUNDATIONAL

The vocabulary. Nothing to build; know these before anything else.

**What AWS is:** Amazon rents out slices of its data centres by the second — a slice of a server (EC2), of disk (EBS), of storage (S3), of a database engine (RDS). Everything else is a variation on that.

**Region:** a geographic location, e.g. `ap-south-1` (Mumbai). Resources live in one region; pick the one nearest your users.

**Availability Zone (AZ):** separate data centres within a region. Spreading across two means one can fail without taking you down.

**Edge location:** hundreds of smaller sites worldwide used by CloudFront for caching.

**Shared responsibility model:** AWS secures the cloud (hardware, hypervisor, physical sites); you secure what's in it (your OS patches, your data, your IAM, your firewall rules). Nearly every AWS breach is on the customer side.

**Pricing models:** on-demand (pay per hour, no commitment), Reserved/Savings Plans (commit 1–3 years for a big discount), Spot (spare capacity at up to 90% off, can be reclaimed with two minutes' notice).

**The Well-Architected Framework:** six pillars — operational excellence, security, reliability, performance efficiency, cost optimisation, sustainability. The entire certification path is built on these.

**Q: Region vs AZ vs edge location?**
A region is a geography; AZs are isolated data centres inside it, close enough for fast replication; edge locations are CDN caches near users, not places you run servers.

**Q: What's the shared responsibility model?**
AWS is responsible for the infrastructure; I'm responsible for configuration, data and access. AWS securing the data centre doesn't stop me making a bucket public.

---

# LEVEL 2 — ASSOCIATE

## 2.1 The stack your site runs on

### EC2 — virtual servers

**Why:** full control — any PHP version, any nginx config. Resize or rebuild in minutes.
**Trade-off:** patching, backups and uptime become your job.
**Your stack:** the box running nginx, PHP and WordPress.
**Session:** Ubuntu 24.04, t3.micro, SSH with the .pem, install LEMP + WordPress. ~$8–10/month running; stop it when done.

**Q: Why EC2 over managed hosting?** Control and cost — I choose the stack and pay only for the instance, but maintenance is mine.
**Q: How do you pick an instance type?** From the workload. WordPress is memory/IO-bound, so general-purpose t3 or m-series. t3 is burstable — sustained load drains credits and throttles.
**Q: What happens when you stop an instance?** The EBS root volume survives; the public IP changes unless there's an Elastic IP. Terminating deletes the root volume by default.

### EBS — disks

**Why:** persistent storage that survives stop/start, snapshotable.
**Your stack:** the 20 GB root volume.
**Watch out:** extra volumes and snapshots keep billing after the instance is gone.

**Q: gp2 vs gp3?** gp3 is cheaper and lets you set IOPS and throughput independently of size; with gp2 performance scales with size, so you over-provision.
**Q: How do you back up an instance?** EBS snapshots (incremental), or an AMI to relaunch the whole configured machine.

### VPC, subnets, security groups

**Why:** network isolation — web server public, database private.
**Your stack:** SSH limited to your IP; 80/443 open; database reachable only from the web server.
**Cost:** free. NAT Gateway is not — ~$30/month, delete the same day.

**Q: Security group vs NACL?** Security groups are stateful, attach to resources, allow-only. NACLs are stateless, attach to subnets, support deny. Security groups do the day-to-day work.
**Q: Why reference a security group instead of an IP?** Instances change IPs; group references keep working as things scale.

### Elastic IP

**Why:** a fixed public address so DNS and SSL keep working across restarts.
**Watch out:** billed while unattached.

### RDS — managed MySQL

**Why:** automatic backups with point-in-time restore, patching, optional failover; the database outlives the web server and can be shared by several.
**Trade-off:** ~$10/month more, slight network latency, no server access.
**Your stack:** move the WordPress database off the instance — one line, `DB_HOST`.

**Q: Why RDS over MySQL on the instance?** Durability and separation. For one small site, local MySQL is cheaper and fine — it's a cost/uptime trade, not a rule.
**Q: Multi-AZ vs read replica?** Multi-AZ is availability — synchronous standby, automatic failover, not readable. Read replicas are performance — asynchronous, readable, may lag.
**Q: Migrating a live database with minimal downtime?** Replicate, let it catch up, short window to stop writes and switch `DB_HOST`. For a small site, `mysqldump` during quiet hours.

### S3 — object storage

**Why:** cheap, unlimited, no server; media stops filling your disk and stops being tied to one instance.
**Your stack:** media library offloaded via WP Offload Media Lite.

**Q: Why offload media?** Keeps the instance disposable, and it's a prerequisite for more than one web server.
**Q: Storage classes?** Standard for active media, Standard-IA or Glacier for archives, moved automatically by lifecycle rules.
**Q: How do you secure a bucket?** Block public access, serve via CloudFront with origin access control, give the app an IAM role scoped to that one bucket.

### CloudFront — CDN

**Why:** caches near users, cuts origin load and latency, terminates SSL, absorbs spikes.

**Q: How do you cache WordPress without breaking logged-in users?** Cache anonymous requests, bypass when a login cookie is present, never cache wp-admin, long TTLs on versioned assets.
**Q: Invalidation?** Slow and billed past a free allowance — version filenames instead.

### Route 53 — DNS

**Why:** health checks, failover and latency routing, alias records to AWS resources, API control.
**Your stack:** optional; the A record can stay at Hostinger.

### ACM — certificates

Free SSL, but only for AWS services like CloudFront and load balancers. On the EC2 box itself, use Certbot.

### IAM — permissions

**Why:** everything else depends on it. Free to practise, and 30% of the exam.
**Your stack:** give the instance a **role** scoped to your bucket instead of pasting keys into wp-config.php.

**Q: User vs role?** A user has long-lived credentials; a role is assumed and issues short-lived ones. Roles are preferred — no key to leak.
**Q: How is a decision evaluated?** Deny by default; explicit allow grants; explicit deny always wins.
**Q: Least privilege in practice?** Specific actions on specific resources, not `s3:*` on `*`. Start narrow, widen when something breaks.

### SES — email

**Why:** authenticated transactional email instead of PHP `mail()` in spam.

**Q: How do you stop WordPress email going to spam?** Authenticated SMTP, verified domain, SPF + DKIM + DMARC, From address on your own domain.
**Q: The sandbox?** New accounts can only send to verified addresses until production access is granted.

### CloudWatch — monitoring

**Q: What would you monitor on a WordPress server?** CPU and burst credits, memory and disk (need the agent — not there by default), DB connections and slow queries, 5xx rate, and an external uptime check.

## 2.2 Hardening the same site

### Secrets Manager / Parameter Store
**Q: Where does the DB password live?** Ideally fetched at runtime via the instance role. Hardcoding in wp-config.php is normal in WordPress and is a weakness.

### KMS
**Q: What should be encrypted?** RDS storage, EBS volumes, S3 buckets, snapshots. Set at creation — hard to add later.

### WAF
Rate-limit `wp-login.php`, block common attack patterns, sits in front of CloudFront or a load balancer.

### Systems Manager (SSM)
Session Manager gives browser shell access without opening port 22 at all.

## 2.3 Scaling the same site

### ElastiCache (Redis)

**Your stack:** `php-redis` on the server, Redis Object Cache plugin, `WP_REDIS_HOST` in wp-config.php, security group allowing 6379 from the web server's group.

**Q: Object cache vs page cache?** Page cache stores finished HTML and skips PHP — best for anonymous traffic. Object cache stores query results — helps logged-in users and admin, where page caching can't. A busy site wants both.

### ALB + Auto Scaling

**Q: What breaks when WordPress runs on two servers?** Uploads (each disk differs) — fix with S3 or EFS. Then shared object cache and sessions in Redis, cron on one node only, and code from deployment rather than edited on a server.
**Q: How does auto scaling decide?** Launch template plus a policy on CPU or request count, with min/max/desired; health checks replace failures.
**Q: Sticky sessions?** Avoid — keep the app stateless so any server can serve any request.

### EFS
Shared filesystem for `wp-content/uploads` across instances — the alternative to S3 offload.

### AMIs and snapshots
Image the configured instance so the whole site relaunches in two minutes. Also saves credits.

## 2.4 Deployment

**Q: How do you deploy WordPress code?** Version-control themes and plugins only. Actions runs lint and tests, then deploys over SSH; the deploy job `needs:` the test job so failures never ship.
**Q: What if a deploy fails halfway?** Mixed old and new files — the dangerous case. Atomic deploy: rsync into a new release directory, switch a symlink when complete. Rollback is switching it back.
**Q: Secrets in a pipeline?** Repository secrets or an OIDC role, and a deploy key scoped to one server.

## 2.5 Cost

**Q: What drives the bill?** Per-hour resources regardless of use — running instances, RDS, ElastiCache, load balancers, NAT gateways, unattached Elastic IPs — plus data transfer out.
**Q: How do you reduce it?** Right-size first, then commit with Savings Plans for steady load, Spot for interruptible work, cheaper storage classes for cold data, CDN to cut egress.
**Q: How do you track it?** Tags, Cost Explorer grouped by tag, budgets with alerts.

## 2.6 Breadth — one hour each

| Service | What it is | Exercise |
|---|---|---|
| Lambda | Function, no server | Resize an image on S3 upload |
| EventBridge | Event bus and scheduler | Run a Lambda every 5 minutes |
| SQS | Queue | Send and consume a message |
| SNS | Pub/sub | Email from a CloudWatch alarm |
| DynamoDB | NoSQL | Create a table, write and query |
| ECS/Fargate | Containers | Deploy hello-world |
| Athena | SQL over S3 files | Query a CSV |

---

# LEVEL 3 — PROFESSIONAL

Two tracks. Assumes years of production experience — answer these conceptually and say so.

## 3.1 Solutions Architect Professional

### Multi-account: Organizations, SCPs, Control Tower

**Why:** hard blast-radius boundaries, consolidated billing, policy in one place.

**Q: Why separate accounts instead of separate VPCs?** A VPC separates network only; IAM, quotas and blast radius stay shared. Accounts give a hard boundary.
**Q: Typical layout?** Management account (billing only), plus security/audit, shared services, logging, and one per environment.
**Q: SCP vs IAM policy?** An SCP grants nothing — it caps the maximum, including root. Effective permission is the intersection.
**Q: How do you centralise logging?** CloudTrail and Config from every account into a locked log-archive account, write-only, with object lock so logs can't be deleted.
**Q: Cross-account access?** Assumed roles with a trust policy naming the source account, external ID and MFA conditions. Never shared keys.

### Hybrid networking

**Q: Direct Connect or VPN?** VPN is quick, cheap, over the internet, so variable latency. Direct Connect gives predictable performance and cheaper egress at volume, but takes weeks and needs redundancy. Common pattern: DX primary, VPN backup.
**Q: Peering vs Transit Gateway vs PrivateLink?** Peering for a couple of VPCs, cheapest, not transitive. Transit Gateway for many VPCs or hybrid links, hub-and-spoke, per-attachment cost. PrivateLink to expose one service without joining networks.
**Q: Overlapping CIDRs after an acquisition?** Can't route together — re-address one side, or expose services via PrivateLink/NAT instead of joining networks.

### Migration

The 7 Rs: rehost, replatform, repurchase, refactor, retire, retain, relocate.

**Q: How would you migrate 200 servers?** Discovery first for dependencies and ownership, then waves starting with low-risk systems. Rehost most; replatform easy wins like a database to RDS; retire what nobody uses. Refactoring everything up front is how migrations stall.
**Q: Database migration with minimal downtime?** DMS with change data capture — full load, ongoing replication, short cutover at near-zero lag. Schema conversion first if the engine changes.
**Q: Biggest risk?** Undocumented dependencies. Hence discovery tooling and a rollback plan per wave.

### Multi-region and DR

| Pattern | RTO | Cost |
|---|---|---|
| Backup and restore | Hours | Lowest |
| Pilot light | Tens of minutes | Low |
| Warm standby | Minutes | Medium |
| Active-active | Near zero | Highest |

**Q: How do you choose?** From RTO and RPO agreed with the business, then the cheapest pattern that meets them. Most systems don't need active-active.
**Q: What makes multi-region hard?** Data. Async replication risks loss on failover; sync costs latency. Aurora Global Database and DynamoDB global tables help, with their own trade-offs.
**Q: How does traffic fail over?** Route 53 health checks with failover routing, or Global Accelerator for faster convergence. DNS TTLs mean failover isn't instant.

### Security and cost at scale

**Q: Identity for hundreds of staff?** Federate the existing IdP through IAM Identity Center; no individual IAM users, short-lived role sessions, leavers removed at the IdP.
**Q: Detection and response across accounts?** GuardDuty, Security Hub to aggregate, Config for drift, CloudTrail to a locked account, responses automated via EventBridge → Lambda.
**Q: Cost control across accounts?** Enforced tagging, Cost Explorer and CUR by tag and account, per-team budgets, org-level Savings Plans since commitments apply across accounts.
**Q: Savings Plans vs RIs vs Spot?** Savings Plans commit hourly spend, flexible across families. RIs are tied to a configuration, sellable. Spot is interruptible spare capacity — batch yes, database no.

## 3.2 DevOps Engineer Professional

### Deployment strategies

**Q: Blue/green vs canary vs rolling?** Blue/green: parallel environment, instant rollback, double resources. Canary: small percentage first with metrics watched, limits blast radius, needs good monitoring. Rolling: batches, no extra cost, both versions run together.
**Q: How do you make deploys safe?** Automated rollback on alarms rather than a human watching, health checks that test the app, and backwards-compatible database migrations.
**Q: Zero-downtime schema change?** Expand and contract — add the column, write both and read old, backfill, read new, drop old in a later release. Never a breaking change in the same deploy as the code needing it.

### Infrastructure as code

**Q: Terraform or CloudFormation?** CloudFormation is native with StackSets and drift detection and no state to manage. Terraform is multi-cloud with better ergonomics, at the cost of remote state and locking. Not using either is the real problem.
**Q: What is drift?** Reality no longer matches code because someone changed the console. The next deploy overwrites their fix or fails. Detect automatically, then codify or revert.
**Q: Multiple environments?** Same modules, different variables, separate state. Environments differing only in parameters is what makes staging meaningful.

### Pipelines, observability, compliance

**Q: Deploying to many accounts from one pipeline?** The pipeline account assumes a deployment role in each target; short-lived credentials, trust policies naming only that role.
**Q: Metrics, logs, traces?** Metrics say something is wrong, logs say what happened, traces say where across services. All three.
**Q: What do you alert on?** Symptoms users feel — error rate, latency, availability — not causes like CPU. Anything that fires and gets ignored should be deleted or fixed.
**Q: How do you automate incident response?** EventBridge on alarms triggering Lambda or SSM runbooks: isolate an instance, roll back, scale out, open a ticket. The runbook is code, not a wiki page read at 3am.
**Q: How do you patch a fleet?** SSM Patch Manager with baselines and maintenance windows — or better, immutable infrastructure: bake a new AMI, roll it out, terminate the old.
**Q: Mutable vs immutable?** Mutable drifts and servers become unreproducible. Immutable replaces from a known image, so rollback is redeploying the previous one.
**Q: ECS or EKS?** ECS is simpler and enough for most teams. EKS is Kubernetes — portable, huge ecosystem, far more operational overhead. Pick it only if you need Kubernetes specifically.
**Q: Fargate or EC2 launch type?** Fargate removes node management, bills per task, suits spiky workloads. EC2 is cheaper at sustained scale and allows custom needs.

---

# LEVEL 4 — SPECIALTY

The top tier alongside Professional, but narrow instead of broad. AWS has been retiring these: Machine Learning – Specialty has closed, Advanced Networking – Specialty retires at the end of 2026, leaving **Security – Specialty** as the only one.

## 4.1 Security — Specialty

Deepest level of the security material. Five domains: incident response, logging and monitoring, infrastructure protection, identity and access management, data protection.

### Incident response

**Q: An EC2 instance is confirmed compromised. What do you do?**
Isolate, don't terminate — evidence lives in memory and on disk. Replace its security group with one that allows nothing, detach it from any auto scaling group so it isn't replaced mid-investigation, snapshot the EBS volumes, and capture memory if tooling allows. Then revoke the instance role's sessions, because the attacker may already hold temporary credentials. Investigate from the snapshots, never the live host.

**Q: An access key has leaked to a public repo. What's the order?**
Deactivate the key immediately, don't wait to assess. Then CloudTrail to see what it did and from where, rotate anything it could reach, and check for persistence — new users, new keys, changed trust policies. Finally, fix the cause: roles instead of keys, secret scanning in CI.

**Q: How do you revoke temporary credentials?**
You can't delete a session, but you can attach a policy denying all actions where `aws:TokenIssueTime` is earlier than now. That's the standard "revoke active sessions" pattern.

### Logging and monitoring

**Q: What must be logged in a regulated environment?**
CloudTrail for every API call across all regions and accounts, Config for resource state and change history, VPC Flow Logs for network, S3 access logs, ALB and CloudFront logs, and the application's own logs. Delivered to a separate log-archive account, write-only, with object lock and MFA delete.

**Q: How do you protect logs from an attacker with admin?**
Cross-account delivery plus S3 Object Lock in compliance mode, so even the root user of the source account can't delete them. CloudTrail log file validation detects tampering.

**Q: GuardDuty, Inspector, Macie, Detective, Security Hub — which does what?**
GuardDuty detects threats from logs and DNS. Inspector scans workloads for vulnerabilities and bad configurations. Macie finds sensitive data in S3. Detective builds an investigation graph from findings. Security Hub aggregates all of them against standards like CIS.

### Infrastructure protection

**Q: How do you design network layers for defence in depth?**
Public subnets for load balancers only, private for application, isolated for data with no route out. Security groups referencing each other rather than IP ranges, NACLs for coarse subnet-level denies, WAF at the edge, Shield Advanced where DDoS is a real risk, and VPC endpoints so traffic to S3 and other services never leaves the AWS network.

**Q: How do you keep instances off the internet entirely?**
No public IPs, no internet gateway route. Outbound updates through a NAT gateway or, better, VPC endpoints plus a patching service. Access via SSM Session Manager rather than SSH, so port 22 is never open.

### Identity and access management (deep)

**Q: How does a permissions decision actually resolve?**
Explicit deny anywhere wins. Otherwise the request must be allowed by the identity policy, and if there's a resource policy, by that too (except same-account cases where either can grant). SCPs, permission boundaries and session policies each cap the maximum. Effective access is the intersection of all of them, minus any deny.

**Q: What is a permission boundary for?**
Safe delegation. You let a team lead create roles, but a boundary means the roles they create can never exceed the permissions you set — so delegation doesn't become privilege escalation.

**Q: Name a common privilege escalation path.**
`iam:PassRole` combined with a service that assumes roles. A user who can launch an EC2 instance and pass an admin role effectively has admin. Restrict PassRole to specific roles, always.

**Q: How do you secure cross-account access to a third party?**
A role with an external ID in the trust policy, which prevents the confused-deputy problem where the vendor is tricked into using your role on someone else's behalf.

### Data protection

**Q: KMS key types?**
AWS-managed (free, rotated automatically, little control), customer-managed (your policy, your rotation, auditable, small monthly cost), and imported or CloudHSM-backed for key material you must control.

**Q: How does envelope encryption work?**
KMS doesn't encrypt your data directly. It issues a data key, which encrypts the data locally; the data key itself is stored encrypted alongside. Decryption means asking KMS to unwrap the data key first. It's why KMS scales to large objects.

**Q: How do you enforce encryption?**
Bucket policies denying uploads without encryption headers, SCPs denying unencrypted volume or database creation, and Config rules flagging anything non-compliant.

**Q: How do you rotate a database credential without downtime?**
Secrets Manager rotation with the alternating-users strategy — two users, one active while the other is rotated, so no window exists where the application holds an invalid password.

## 4.2 Advanced Networking — Specialty (retiring end of 2026)

Still useful knowledge even without the exam: Direct Connect virtual interfaces and BGP, Transit Gateway route tables and segmentation, hybrid DNS resolution with Route 53 Resolver endpoints, multicast, Global Accelerator, and network performance tuning such as jumbo frames and placement groups.

**Q: How does DNS work between on-premises and a VPC?**
Route 53 Resolver inbound endpoints let on-premises resolve AWS private zones; outbound endpoints with forwarding rules let AWS resolve on-premises names. Without them, neither side sees the other's private DNS.

## 4.3 Relevance to you

Security – Specialty content is the only part of this tier worth reading for a WordPress role, and only the IAM and data-protection parts. The rest is for dedicated cloud security engineers. Read it for understanding; don't claim it.

---

# HOW TO ANSWER HONESTLY

- **Built it:** describe what you did and what surprised you — the permission or security group that blocked you is the best material.
- **Only read it:** *"I haven't run that in production. My understanding is X, and the trade-off is Y."*
- **Lab choices:** *"For the lab I used the standard setup since I was learning the services. On a real project I'd choose based on traffic, budget and who maintains it."*
- **Scale questions:** *"That depends on the RTO and RPO. An hour's tolerance means A; minutes means B, and it costs considerably more."*

Naming the trade-off is what signals seniority. Nobody expects a WordPress developer to have designed a multi-region migration — discussing it sensibly already exceeds the role.
