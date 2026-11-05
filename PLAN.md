# AWS WordPress Lab — Master Execution Plan (Target: Sunday Finish)

> **Goal:** Complete the entire AWS Cloud Architecture roadmap (Phases 6–12 + Docker + Kubernetes + $40 AWS Credits) by Sunday with 100% verified Definition of Done and revision-ready notes.

---

## 📊 Current Status Overview

| Status | Phases Completed | Remaining | Active Phase |
| :---: | :---: | :---: | :---: |
| **45% Complete** | **Phases 1, 2, 3, 4, 5** (EC2, HTTPS, CI/CD, RDS MySQL, S3 Media) | **Phases 6–12 + Docker + K8s** | **Phase 6: Harden it** |

---

## 🗓️ Day-by-Day Phase Execution Schedule

```text
Thursday (Day 1)   ──► Dual-CDN Testing + Phase 6 (Security) + Phase 7 (SES Email & Monitoring)
Friday (Day 2)     ──► Phase 8 (Redis Cache) + Phase 9 (ALB & Auto Scaling Group)
Saturday (Day 3)   ──► Phase 10 (Terraform IaC) + Bonus 1 (Docker & AWS ECS Fargate)
Sunday (Day 4)     ──► Phase 11 (FinOps) + Phase 12 (Serverless Lambda + $40 Credits) + Bonus 2 (Kubernetes EKS)
```

---

### 📅 Thursday (Day 1) — Dual-CDN, Security Hardening & Monitoring
**Estimated Time:** ~2.5 to 3 Hours  
**Phases to Complete:** Pre-Phase 6 + Phase 6 + Phase 7

- [ ] **Task 0: Dual-CDN Live Testing (Pre-Phase 6)**
  - Test Cloudflare Free Tier setup (`cdn.asaxenadev.com` CNAME ➔ S3 bucket + Transform Rule).
  - Test AWS CloudFront + OAC if AWS Support case has cleared.
- [ ] **Phase 6: Harden it**
  - Attach `AmazonSSMManagedInstanceCore` to IAM Role `wp-lab-s3-role`.
  - Connect via AWS Systems Manager Session Manager browser shell.
  - Delete Port 22 (SSH) from Security Group inbound rules (100% closed to internet).
  - Offload database password from `wp-config.php` to AWS Systems Manager Parameter Store.
  - **Done when:** Port 22 closed, Session Manager connects, zero passwords in `wp-config.php`.
- [ ] **Phase 7: Email & Monitoring**
  - Verify domain in Amazon SES and add 3 DKIM + 1 SPF + 1 DMARC records in Hostinger DNS.
  - Configure SMTP in WordPress (WP Mail SMTP) and send verified test email.
  - Install Amazon CloudWatch Agent on EC2 to graph RAM and Disk utilization.
  - **Done when:** Test email lands in inbox (not spam); memory/disk graphs visible in CloudWatch.

---

### 📅 Friday (Day 2) — In-Memory Caching & High-Availability Auto Scaling
**Estimated Time:** ~2.5 to 3 Hours  
**Phases to Complete:** Phase 8 + Phase 9

- [ ] **Phase 8: In-Memory Caching (Redis / Valkey)**
  - Provision Amazon ElastiCache Redis cluster (`cache.t3.micro`).
  - Whitelist Port 6379 from EC2 security group.
  - Install Redis Object Cache in WordPress; verify query reduction in Query Monitor.
  - **Done when:** Redis Object Cache says "Connected"; MySQL query count significantly drops.
- [ ] **Phase 9: Scale it (Horizontal Auto Scaling & ALB)**
  - Create Golden AMI (`wp-lab-golden-v1`) from stateless EC2 instance.
  - Create EC2 Launch Template with IAM role and User Data.
  - Create Application Load Balancer (ALB) across 2 Availability Zones (`ap-south-1a`, `ap-south-1b`).
  - Create Auto Scaling Group (ASG) with min: 2 instances.
  - **Chaos Test:** Terminate 1 EC2 instance manually — site stays up, ASG replaces it automatically.
  - **Done when:** Terminate one instance — ALB URL still serves, replacement launches automatically.

---

### 📅 Saturday (Day 3) — Infrastructure as Code & Docker Containerization
**Estimated Time:** ~2.5 to 3 Hours  
**Phases to Complete:** Phase 10 + Bonus Phase 1 (Docker)

- [ ] **Phase 10: Codify it (Terraform / OpenTofu)**
  - Write modular Terraform HCL code (VPC, Subnets, SG, IAM, S3, RDS, ALB, ASG).
  - Setup remote state in Amazon S3 with DynamoDB state locking.
  - Run `terraform plan` and `terraform apply`.
  - **Done when:** `terraform destroy` wipes infrastructure, and `terraform apply` recreates it cleanly.
- [ ] **Bonus 1: Docker Containerization (AWS ECR & ECS Fargate)**
  - Build multi-service Dockerfile (Nginx + PHP 8.3-FPM + Supervisord).
  - Test locally with `docker-compose.yml`.
  - Push image to Amazon ECR private repository.
  - Deploy serverless ECS Task on AWS Fargate behind Application Load Balancer.
  - **Done when:** Stateless WordPress container serves traffic on ECS Fargate without EC2 instances.

---

### 📅 Sunday (Day 4) — FinOps, Serverless, Free Credits & Kubernetes EKS
**Estimated Time:** ~3 Hours  
**Phases to Complete:** Phase 11 + Phase 12 + Bonus Phase 2 (Kubernetes) + Final Review

- [ ] **Phase 11: Cost Optimization & FinOps Governance**
  - Implement tagging strategy (`Project = aws-learning`, `Environment = lab`).
  - Activate Cost Allocation Tags in Billing Console.
  - Create AWS Monthly Budget Alert ($10 limit with 80% email trigger).
  - Inspect spend breakdown in AWS Cost Explorer.
  - **Done when:** Cost Explorer shows breakdown grouped by tags; Budget alert active.
- [ ] **Phase 12: Modern Cloud, Serverless & $40 AWS Credits Claim**
  - Deploy Python Lambda function triggered automatically by S3 image uploads (`s3:ObjectCreated:*`).
  - Create Amazon EventBridge scheduled cron rule.
  - **Claim $20 AWS Credit:** Complete "Create a web app using AWS Lambda" activity.
  - **Claim $20 AWS Credit:** Complete "Use a foundation model in Amazon Bedrock playground" activity.
  - **Done when:** Lambda logs in CloudWatch; EventBridge triggers; $40 extra AWS credits secured.
- [ ] **Bonus 2: Enterprise Kubernetes on Amazon EKS**
  - Apply Kubernetes manifests (`deployment.yaml`, `service.yaml`, `ingress.yaml`, `hpa.yaml`).
  - Route traffic via AWS Load Balancer Controller.
  - Verify Horizontal Pod Autoscaler (HPA) auto-scaling based on CPU load.
  - Configure IAM Roles for Service Accounts (IRSA) for Pod-level S3 access.
  - **Done when:** WordPress runs on Amazon EKS with auto-scaling pods and zero shared disk storage.
- [ ] **Final Clean Teardown:**
  - Execute final cleanup checklist to ensure ₹0 lingering billing after Sunday.

---

## 💡 Daily Rule of Thumb: Cost Control
At the end of **every day's session**:
1. **EC2 / ASG:** Stop or scale down to 0 to prevent compute hour drainage.
2. **ALB / ElastiCache / RDS:** Stop or destroy when not in use.
3. S3 bucket, IAM roles, and Parameter Store carry zero/negligible idle costs.

