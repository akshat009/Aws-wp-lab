# AWS Interview Prep — Why Each Service, and What They'll Ask

Companion to the services map. Same order, but each entry answers three things: **why you'd use it**, **what it costs you**, and **what an interviewer asks**.

Answers here are deliberately short. Thirty seconds each is the right length in an interview.

---

## EC2

**Why:** full control of the server — any PHP version, any nginx config, any extension. Cheaper than managed hosting at scale, and you can resize or rebuild in minutes.

**Trade-off:** you own patching, security, backups and uptime. For one small site, managed hosting is less work.

**Q: Why EC2 instead of managed WordPress hosting?**
Control and cost. On a managed host you accept their PHP versions, their caching and their limits. On EC2 I configure everything and pay only for the instance. The cost is that server maintenance becomes my job.

**Q: How do you pick an instance type?**
Start from the workload. WordPress is mostly memory- and I/O-bound, not CPU-bound, so a general-purpose t3 or m-series fits. t3 is burstable — cheap, but sustained CPU load drains credits and throttles you. For steady traffic I'd move to m-series.

**Q: What happens to data if the instance stops?**
The EBS root volume persists through a stop/start, but the public IP changes unless there's an Elastic IP. Terminate, and the root volume is deleted by default.

---

## EBS

**Why:** persistent disk that survives instance stop/start, can be snapshotted and re-attached.

**Q: gp2 vs gp3?**
gp3 is newer, cheaper, and lets you set IOPS and throughput independently of size. With gp2, performance scales with volume size, so you end up over-provisioning storage just to get IOPS.

**Q: How do you back up an instance?**
EBS snapshots, which are incremental and stored in S3. For a full rebuild, create an AMI so the instance can be relaunched with everything configured.

---

## VPC, subnets, security groups

**Why:** network isolation. Public subnet for the web server, private subnet for the database, so the database has no route from the internet.

**Q: Security group vs NACL?**
Security groups are stateful and attach to resources — return traffic is allowed automatically, and they only have allow rules. NACLs are stateless, attach to subnets, and support deny rules. In practice security groups do the work; NACLs are for broad subnet-level blocks.

**Q: How should a WordPress stack be laid out?**
Web server in a public subnet with 80/443 open and SSH restricted to my IP. Database in a private subnet, port 3306 open only to the web server's security group — not an IP range, the security group itself. If the private subnet needs outbound internet for updates, that's a NAT Gateway.

**Q: Why reference a security group instead of an IP?**
Instances change IPs. Referencing the group means any instance in that group gets access automatically, and scaling doesn't break the rule.

---

## Elastic IP

**Why:** a fixed public address that survives restarts, so DNS keeps working.

**Q: Why not just use the auto-assigned IP?**
It changes every time the instance stops and starts, which breaks DNS and SSL. Also worth noting: an Elastic IP costs money while it isn't attached to a running instance.

---

## RDS

**Why:** automated backups with point-in-time restore, patching, and optional failover. The database survives the web server being destroyed, and multiple web servers can share it.

**Trade-off:** costs more, adds slight network latency, and you can't touch the underlying server.

**Q: Why RDS instead of MySQL on the instance?**
Separation and durability. The database outlives the web server, backups and patching are handled, and I can scale the two independently. For a single low-traffic site, MySQL on the instance is cheaper and perfectly reasonable — it's a cost/uptime trade, not a rule.

**Q: Multi-AZ vs read replica?**
Multi-AZ is for availability: a synchronous standby in another AZ, promoted automatically on failure, and you can't read from it. A read replica is for performance: asynchronous copies you can read from, which means possible replication lag. WordPress needs a plugin or HyperDB-style setup to use replicas.

**Q: How would you migrate a live WordPress database to RDS with minimal downtime?**
Set up replication from the source to RDS, let it catch up, then take a short maintenance window: stop writes, confirm replication has caught up, switch `DB_HOST`, resume. For a small site, a `mysqldump` and import during a low-traffic window is simpler.

---

## S3

**Why:** cheap, effectively unlimited storage with its own URLs, and no server to run. Media stops consuming your disk and stops being tied to one instance.

**Q: Why offload media to S3?**
Two reasons. It keeps the instance disk small and disposable, and it's a prerequisite for running more than one web server — otherwise each server has a different uploads folder.

**Q: Storage classes?**
Standard for active media; Standard-IA or Glacier tiers for archives and backups that are rarely read. Lifecycle rules move objects automatically as they age.

**Q: How do you secure a bucket?**
Block public access at the bucket level, serve through CloudFront with an origin access control, and give the application an IAM role scoped to that one bucket. Public buckets are the most common AWS breach.

---

## CloudFront

**Why:** caches content near users, cuts origin load and latency, terminates SSL, and absorbs traffic spikes.

**Q: How do you cache WordPress behind a CDN without breaking logged-in users?**
Cache anonymous page requests, and bypass the cache when a WordPress login cookie is present. Never cache wp-admin. Static assets get long TTLs with versioned filenames.

**Q: Cache invalidation?**
Invalidations are slow and, past a free allowance, billed. Versioned asset filenames are better — a new file is a new URL, so nothing needs invalidating.

---

## Route 53

**Why:** DNS integrated with AWS, with health checks and routing policies (failover, latency-based, weighted).

**Q: Why use Route 53 over the registrar's DNS?**
Health-check-based failover, alias records that point at AWS resources without an IP, and API/Terraform control. For a single site, a registrar's DNS is fine.

---

## IAM

**Why:** controls who and what can do anything in the account. Every other security control depends on it.

**Q: User vs role?**
A user has long-lived credentials and belongs to a person. A role is assumed temporarily and issues short-lived credentials — used by EC2 instances, Lambda, or people switching accounts. Roles are preferred because there's no key to leak.

**Q: How should an EC2 instance access S3?**
An instance role with a policy scoped to that bucket. The SDK picks the credentials up automatically. Access keys in a config file are the thing to avoid — they leak into Git.

**Q: How is an IAM decision evaluated?**
Deny by default. An explicit allow grants access, and an explicit deny anywhere overrides any allow. Identity policies, resource policies and permission boundaries all get evaluated together.

**Q: What does least privilege mean in practice?**
Grant the specific actions on the specific resources needed, not `s3:*` on `*`. Start narrow and widen when something breaks, not the reverse.

---

## SES

**Why:** reliable transactional email with proper authentication, instead of PHP `mail()` landing in spam.

**Q: How do you stop WordPress email going to spam?**
Send through an authenticated SMTP service, verify the sending domain, and publish SPF, DKIM and DMARC records. Also keep the From address on your own domain.

**Q: What's the SES sandbox?**
New accounts can only send to verified addresses, with a low daily cap, until you request production access.

---

## CloudWatch

**Why:** the only way to know what the server is doing without being logged into it.

**Q: What would you monitor on a WordPress server?**
CPU and burst credits, memory and disk (both need the CloudWatch agent — they aren't there by default), database connections and slow queries, 5xx rates, and an uptime check on the site itself.

---

## Secrets Manager / Parameter Store

**Why:** credentials out of code and out of Git, with rotation and audit.

**Q: Where do you keep the database password?**
Ideally Secrets Manager or Parameter Store, fetched at runtime by the instance's IAM role. Hardcoding it in wp-config.php is the common practice in WordPress, and it's a weakness — anyone with file access has the database.

---

## KMS

**Why:** managed encryption keys for data at rest, with access controlled through IAM.

**Q: What should be encrypted?**
RDS storage, EBS volumes, S3 buckets, and snapshots. It's a checkbox at creation time and hard to add later, so turn it on from the start.

---

## ElastiCache (Redis)

**Why:** a persistent object cache shared across requests and servers, which removes repeated database queries — especially for logged-in users and admin screens, where page caching can't help.

**Q: Object cache vs page cache?**
Page cache stores the finished HTML and skips PHP entirely — great for anonymous visitors. Object cache stores database query results, so PHP still runs but the database is spared. Logged-in traffic benefits from the object cache; anonymous traffic mostly from the page cache. A busy site wants both.

**Q: What does WordPress need to use Redis?**
The php-redis extension on the server, a drop-in plugin that writes `object-cache.php`, and the connection details in wp-config.php. ElastiCache is only reachable inside the VPC, so the security group must allow 6379 from the web server's group.

---

## ALB and Auto Scaling

**Why:** survive instance failure, deploy without downtime, and handle traffic spikes automatically.

**Q: What breaks when you put WordPress on two servers?**
Uploads, because each server has its own disk — solved with S3 offload or EFS. Then the object cache and sessions need to be shared (Redis), and cron should run on one node only. Code must come from deployment, not from editing files on a server.

**Q: How does auto scaling decide?**
A launch template plus a scaling policy, usually on CPU or request count, with a min, max and desired count. Health checks replace instances that fail.

**Q: Sticky sessions?**
Better avoided. Keep the app stateless by putting shared state in Redis and the database, so any server can serve any request.

---

## Deployment and CI/CD

**Q: How do you deploy WordPress code?**
Version-control themes and plugins, not the whole of WordPress or uploads. GitHub Actions runs lint and tests, then deploys the built artifact over SSH to the server. The deploy job depends on the test job, so a failure never ships.

**Q: What if a deploy fails halfway?**
That's the dangerous case — mixed old and new files. The fix is an atomic deploy: rsync into a fresh release directory, then switch a symlink once the transfer is complete. Rollback is switching the symlink back.

**Q: How do you handle secrets in a pipeline?**
Repository secrets or an OIDC role, never committed keys. A deploy key scoped to the one server, not a personal key.

---

## Cost

**Q: What actually drives an AWS bill?**
Anything billed per hour regardless of use: running instances, RDS, ElastiCache, load balancers, NAT gateways, unattached Elastic IPs. Plus data transfer out. Storage is usually small by comparison.

**Q: How do you reduce cost?**
Right-size first — most instances are oversized. Then commit to steady workloads with Savings Plans or Reserved Instances, use Spot for anything interruptible, move cold data to cheaper storage classes, and serve traffic through a CDN so egress is cheaper.

**Q: How do you track it?**
Tag resources by project or environment, use Cost Explorer grouped by tag, and set budgets with alerts.

---

## Professional-level questions (answer conceptually)

These come up in senior conversations. You're not expected to have run them all.

**Q: How would you design WordPress for high availability?**
Multiple instances across at least two Availability Zones behind a load balancer, in an auto scaling group. RDS Multi-AZ for the database. Media on S3 with CloudFront. Redis for shared object cache. Deployments from a pipeline, so no server holds unique state.

**Q: RTO and RPO?**
RTO is how long you can be down; RPO is how much data you can afford to lose. They drive the strategy: backups only, a warm standby, or active-active across regions — increasing in cost at each step.

**Q: How do you handle a traffic spike?**
Page cache and CDN first, since they absorb most anonymous traffic cheaply. Then auto scaling for the web tier and read replicas if the database is the bottleneck. Scaling instances before caching is the expensive way round.

**Q: Multi-account structure?**
Separate accounts per environment under an Organization, with SSO and centralised billing. It gives hard blast-radius boundaries — a mistake in dev can't touch production.

**Q: How do you keep infrastructure reproducible?**
Terraform or CloudFormation in version control, so environments are identical and can be destroyed and recreated. Clicking in the console doesn't survive staff turnover.

---

## How to answer honestly

For anything you've built: describe what you did and what surprised you.

For anything you've only read: *"I haven't run that in production. My understanding is X, and the trade-off is Y."* That answer is respected. Bluffing isn't, and one follow-up question exposes it.

For choices made in a learning project: *"For the lab I used the standard setup since I was learning the services. On a real project I'd choose based on traffic, budget and who maintains it."*
