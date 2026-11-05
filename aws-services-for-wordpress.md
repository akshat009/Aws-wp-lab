# AWS Services Map — Foundational to Associate, Applied to a WordPress Stack

Account: `akshat-wp-lab` · Region: Asia Pacific (Mumbai) `ap-south-1` · Free plan, $100 credits

**Rule for every session:** spin up → learn → note it down → delete. Check Billing → Bills at the end of each session.

---

## Tier 1 — The stack your site runs on

These are the services your WordPress site actually uses. Spend the most time here.

### EC2 — Elastic Compute Cloud
A virtual server rented by the hour. Ubuntu, nothing pre-installed.

**In your setup:** the box running nginx, PHP and WordPress.
**Session:** launch Ubuntu 24.04 t3.micro, SSH in with the .pem key, install the LEMP stack, install WordPress.
**Cost:** ~$8–10/month if left running. Stop it when done — you then pay only for the disk.
**Delete:** terminate the instance.

### EBS — Elastic Block Store
The virtual hard disk attached to an EC2 instance.

**In your setup:** the 20 GB root volume holding your site files.
**Session:** take a snapshot, then restore it to a new volume. Compare gp2 and gp3 pricing.
**Watch out:** extra volumes and snapshots survive instance termination and keep billing.

### VPC, subnets, security groups, route tables
Your private network inside AWS. Security groups are the firewall around each resource.

**In your setup:** the network your instance sits in. SSH restricted to your own IP; ports 80 and 443 open to everyone.
**Session:** create a VPC by hand with a public and a private subnet, and place the database in the private one.
**Cost:** free (a NAT Gateway is not — ~$30/month, delete same day).

### Elastic IP
A fixed public IP address that survives instance restarts.

**In your setup:** the address your subdomain's A record points to.
**Watch out:** billed while unattached. Release it when you delete the instance.

### RDS — Relational Database Service
Managed MySQL. AWS handles patching, backups and failover.

**In your setup:** move the WordPress database off the EC2 box. Change `DB_HOST` in wp-config.php.
**Session:** db.t3.micro MySQL, private subnet, security group allowing 3306 only from the EC2 security group. `mysqldump` the local DB and import it.
**Later:** turn on Multi-AZ, force a failover, watch it recover. Add a read replica.
**Cost:** ~$10/month running. Delete when done (skip the final snapshot).

### S3 — Simple Storage Service
Object storage. Files with URLs, no server.

**In your setup:** the media library. Offload uploads with WP Offload Media Lite or Media Cloud.
**Session:** create a bucket, set a bucket policy, connect the plugin, then try storage classes and a lifecycle rule that moves old files to cheaper storage.
**Cost:** pennies at your volume.

### CloudFront
CDN. Caches your content in data centres worldwide.

**In your setup:** sits in front of the S3 bucket for media, or in front of the whole site.
**Session:** create a distribution, set cache behaviours, test a cache hit vs miss, invalidate the cache.
**Watch out:** distributions take ~15 minutes to deploy and to delete.

### Route 53
DNS. Can host your domain's records instead of Hostinger.

**In your setup:** optional — your A record can stay at Hostinger. Worth doing once to see hosted zones, record types and health checks.
**Cost:** ~$0.50 per hosted zone per month.

### ACM — Certificate Manager
Free SSL certificates, but only usable with AWS services like CloudFront and load balancers.

**In your setup:** for the EC2 instance itself, use Certbot/Let's Encrypt instead. ACM is for the CloudFront distribution.

### IAM — Identity and Access Management
Users, roles, policies. Who can do what.

**In your setup:** the biggest security win — give the EC2 instance an IAM **role** with access to only your S3 bucket, instead of putting an access key in wp-config.php.
**Session:** create a user with a least-privilege policy, then an instance role, then break something deliberately and read the access-denied message.
**Cost:** free. This is 30% of the syllabus and costs nothing to practise.

### SES — Simple Email Service
Transactional email sending.

**In your setup:** WordPress email (password resets, order mails) sent through SES via SMTP instead of PHP mail.
**Session:** verify a domain, add DKIM records, send a test. Note you start in a sandbox that only sends to verified addresses.

### CloudWatch
Logs, metrics, alarms.

**In your setup:** ship nginx and PHP error logs, set an alarm for high CPU or low disk.
**Session:** create an alarm that emails you, then trigger it.

---

## Tier 2 — Hardening and scaling the same site

### Secrets Manager / Parameter Store
Stores passwords and keys outside your code.

**In your setup:** keep the RDS password here and have wp-config.php fetch it.
**Note:** Parameter Store has a free tier; Secrets Manager charges per secret per month.

### KMS — Key Management Service
Encryption keys.

**In your setup:** enable encryption at rest on the RDS instance, the EBS volume and the S3 bucket.

### ElastiCache (Redis)
Managed Redis, used as a persistent object cache.

**In your setup:** install `php-redis` on the instance, add the Redis Object Cache plugin, point `WP_REDIS_HOST` at the cluster endpoint. Security group must allow 6379 from the EC2 security group.
**Note:** object cache (database queries), not page cache. Delete after the session — it bills per hour.

### ALB — Application Load Balancer
Distributes traffic across multiple instances.

**In your setup:** not needed for one site. Build it for one hour to see two instances serving the same site.
**Cost:** ~$16–20/month. Delete the same day.

### Auto Scaling Group
Adds and removes instances automatically.

**In your setup:** create a launch template from your AMI, set min 1 / max 2, terminate an instance and watch a replacement appear.
**Note:** with multiple servers, WordPress uploads break unless media is on S3 or EFS — that is the point of the exercise.

### EFS — Elastic File System
A shared filesystem several instances can mount.

**In your setup:** the alternative to S3 offload for a shared `wp-content/uploads`. One hour is enough.

### AMI + snapshots
Images of a configured instance.

**In your setup:** after WordPress is installed and tuned, create an AMI. You can then relaunch the whole site in two minutes, which also saves credits.

### WAF
Web application firewall in front of CloudFront or an ALB.

**In your setup:** rate-limit `wp-login.php` and block common attack patterns.

### Systems Manager (SSM)
Remote command execution and patching, plus Session Manager for browser-based shell access without SSH keys.

**In your setup:** connect to the instance without opening port 22 at all.

---

## Tier 3 — One hour each, just to know what they are

Not part of a WordPress stack. Build a trivial example, note what it does, delete it.

| Service | What it is | One-hour exercise |
|---|---|---|
| Lambda | Run a function, no server | Resize an image when it lands in S3 |
| EventBridge | Event bus and scheduler | Run a Lambda every 5 minutes |
| SQS | Message queue | Send and consume a message |
| SNS | Pub/sub notifications | Email yourself from a CloudWatch alarm |
| DynamoDB | NoSQL database | Create a table, write and query an item |
| ECS / Fargate | Run containers | Deploy a hello-world container |
| Athena | SQL over files in S3 | Query a CSV in a bucket |
| Cost Explorer | Spend analysis | Tag your resources, then group costs by tag |

---

## Suggested order

1. **Build:** EC2 + WordPress → Elastic IP + DNS + HTTPS → RDS → S3 + CloudFront → GitHub Actions deploy
2. **Secure:** IAM roles, private subnet, security groups, Secrets Manager, KMS, WAF
3. **Scale:** ElastiCache, ALB + Auto Scaling, EFS, read replicas, AMIs
4. **Control cost:** pricing models, tagging, Cost Explorer, right-sizing
5. **Breadth:** the Tier 3 table, one hour each

---

## Cost discipline

**Charges by the hour whether you use it or not:** EC2 (running), RDS, ElastiCache, ALB, NAT Gateway, unattached Elastic IPs.

**Effectively free:** IAM, VPC, security groups, S3 at small volume, Lambda, CloudWatch at low volume.

**End-of-session checklist:**
- [ ] Terminate EC2 instances
- [ ] Delete RDS instances, ElastiCache clusters, load balancers, NAT gateways
- [ ] Release unattached Elastic IPs
- [ ] Delete unused EBS volumes and snapshots
- [ ] Check Billing → Bills → Charges by service

Learn Terraform early; `terraform destroy` does the whole checklist in one command.
