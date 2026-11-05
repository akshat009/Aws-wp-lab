# Project context

I'm a WordPress developer learning AWS through one project: a WordPress
site on AWS, built up phase by phase.

**Strategy:** `aws-wordpress-project-strategy.md` — every phase, with console
steps and commands
**Prompts:** `aws-project-ai-prompts.md` — per-phase prompts for before,
during, after and notes

**Setup:** AWS Free plan account, region `ap-south-1` (Mumbai), $100 credits.
Everything is torn down at the end of each session.

---

## Rules for AI Assistants

- One phase per session. Never jump ahead to later phases.
- Explain the cause before giving a fix.
- Don't write full scripts for Phase 1 — I run commands one by one, because
  the breakages are the learning.
- Never put real credentials, keys or account numbers in any file.
- After each phase, help me write `notes/phase-N.md`.
- When I confirm a phase's "done when" check has passed, write
  `notes/phase-N.md` and update the **Current phase** line in this file
  yourself — don't wait to be asked.
- When I ask "is this best practice?", answer with the trade-off instead —
  that's what an interviewer will ask.
- **Target Environment & Command Labeling Rule:** Always explicitly check and specify WHERE, ON WHICH INSTANCE, and AS WHOM a command must be executed before providing it. Clearly label:
  - **Environment & Instance:** `[Local Windows PowerShell]` vs `[Remote Ubuntu EC2: wp-lab (Session Manager)]`
  - **Target Linux User & Shell State:** Explicitly specify the required user privilege (e.g., `User: root — run 'sudo su -' first if prompt shows '$'`).
  Never give remote Linux commands without first confirming the user has connected to the remote Linux shell and has elevated to the required user privilege level.
- **No Manual ID / Policy Guessing Rule (Native AWS Copy Rule):** Never manually transcribe, construct, or guess auto-generated resource IDs, ARNs, Account Numbers, or bucket policies from screenshots or images (which risks optical/typo mismatches like 5 vs S, O vs 0, 1 vs 3). Always directly instruct the user to use AWS's native built-in "Copy" buttons (e.g., CloudFront's "Copy policy" banner, copy ARN icons) or paste directly from the console so zero ARN mismatch errors happen from the start.
- **Image & Screenshot Automation:** Whenever the user uploads a screenshot or image in the chat:
  1. Automatically save/copy the image to `notes/images/<descriptive-name>.png`.
  2. Automatically embed the image in the appropriate step or gotcha section in `notes/phase-N.md`.
  3. In your response, explicitly inform the user where the image was placed and ask for confirmation: *"I have attached this image at [Section/Step] in notes/phase-N.md — does this placement look right, or would you like to move it?"*

---

## Current phase: 10 (In Progress — Level 1 Done, Level 2 Ready for Tomorrow)

Phase 10 Level 1 (Local Prototyping & Bootstrap) completed and verified:
- Terraform v1.16.6 installed locally on Windows.
- Infrastructure workspace `infra/` authored: `main.tf`, `variables.tf`, `outputs.tf`, `install.sh`.
- Terraform core workflow validated (`init`, `validate`, `plan`).
- `terraform apply` provisioned `aws_security_group.web` (`sg-035e7f0d68fe6d4dd`) and Ubuntu 24.04 instance `aws_instance.wp` (`i-0af3a3266517a12c6`, Dynamic IP `35.154.176.166`).
- Live WordPress setup screen verified at `http://35.154.176.166/wp-admin/install.php` (`200 OK`).
- `notes/phase-10.md` fully rewritten with comprehensive architecture diagrams, comparison tables, Gotchas 1–5, and interview Q&As.

Next session: Phase 10 Level 2 (Enterprise GitOps with OIDC & Remote Backend — S3 State Bucket, DynamoDB Lock, State Migration, IAM OIDC Role, and GitHub Actions CI/CD Pipeline).

---

### 📋 Tomorrow Session Startup Checklist (Phase 10 Level 2: Enterprise GitOps)

#### Startup Checklist for Tomorrow:
- [ ] **Step 1: Check AWS Cloud Resources:**
  - Verify if EC2 instances are in `Stopped` state.
  - If starting instances: EC2 Dashboard ➔ select `wp-lab` ➔ Instance state ➔ Start.
- [ ] **Step 2: Resume Phase 10 at Level 2 - Step 5:**
  - Open AWS Management Console ➔ Navigate to **Amazon S3**.
  - Create Remote State Bucket: `wp-lab-tfstate-538820337783` (Region: `ap-south-1`, Versioning: **Enable**, Block Public Access: **On**).
- [ ] **Step 3: Level 2 - Step 6 (DynamoDB State Lock):**
  - Navigate to **DynamoDB** ➔ Create table `wp-lab-tf-locks` (Partition key: `LockID` [String]).
- [ ] **Step 4: Level 2 - Step 7 (Migrate State):**
  - Add `backend "s3"` block to `infra/main.tf`.
  - Run `terraform init -migrate-state` in local terminal to push local state to S3.
- [ ] **Step 5: Level 2 - Steps 8–10 (OIDC & GitHub Actions Pipeline):**
  - Configure IAM Identity Provider (`token.actions.githubusercontent.com`) and GitHub Actions Role.
  - Setup `.github/workflows/terraform.yml`.
- [ ] **Step 6: Phase 10 Definition of Done:**
  - Execute `terraform destroy` ➔ Verify 100% clean teardown.
  - Execute `terraform apply` ➔ Verify clean automated rebuild from code.

---

## Definition of done

A phase is finished when **both** the check passes **and** `notes/phase-N.md`
is written. Without the notes the phase is incomplete — the notes are what
I revise from before an interview, not the running site.

| Phase | What it is | Done when |
|---|---|---|
| 1 | WordPress on EC2 | `http://<IP>` shows the WordPress dashboard and I can log in |
| 2 | Domain + HTTPS | `https://lab.asaxenadev.com` loads with a padlock, no mixed-content warnings |
| 3 | Deploy pipeline | Push → Actions green → file changed on the server. Failing test → deploy job never runs |
| 4 | Database to RDS | Local MySQL stopped, site still works |
| 5 | Media to S3 + CDN | New upload's URL points at S3/CloudFront, file is not on the instance |
| 6 | Harden it | Port 22 closed, Session Manager works, no passwords in wp-config.php |
| 7 | Email + monitoring | Test email lands in the inbox (not spam); memory and disk graphs visible in CloudWatch |
| 8 | Cache | Redis Object Cache says "Connected"; Query Monitor shows fewer queries |
| 9 | Scale it | Terminate one instance — ALB URL still serves, replacement launches automatically |
| 10 | Codify it | `terraform destroy` then `terraform apply` brings the site back |
| 11 | Cost | Cost Explorer shows a breakdown grouped by my tags |
| 12 | Odds and ends | Each service has one working example, then deleted |
| *Bonus 1* | *Docker & Containers* | *(Post-Phase 12)* Containerize the decoupled, stateless WordPress stack into a Dockerfile and deploy to AWS ECS/Fargate |
| *Bonus 2* | *Kubernetes (EKS)* | *(Post-Phase 12)* Orchestrate stateless WordPress on Amazon EKS with Ingress ALB, HPA, and IRSA |
| *Bonus 3* | *Cloudflare & R2 Zero-Egress Lab* | *(Post-Phase 12 + K8s)* Implement Phase 5 Step 4C (Cloudflare Free Tier + S3) and Step 4D (Cloudflare R2 Zero-Egress) alternatives |

> **Note on Docker & Kubernetes:** Containers and Kubernetes are intentionally placed after Phase 12. In Phases 4–9, we decouple the WordPress stack (RDS for DB, S3 for media, Redis for cache, ALB for traffic) making the web tier 100% stateless. A stateless web app is the exact prerequisite for running cleanly in Docker and Kubernetes without complex, slow shared NFS/EFS persistent volumes. Learning AWS infrastructure first avoids dual-debugging confusion (AWS VPC vs Docker/K8s networking).

---

## Notes template

Each `notes/phase-N.md` should answer:

- **What it does** — one line, my own words
- **Why choose it** — over the alternative
- **Trade-off** — what it costs me
- **What surprised me** — the error, the permission, the thing no tutorial mentioned
- **Cost** — what it billed, and how I deleted it
- **Commands/config** — what I actually ran

---

## End-of-session checklist

- [ ] Terminate EC2 instances
- [ ] Delete RDS, ElastiCache, ALBs, NAT gateways
- [ ] Release unattached Elastic IPs
- [ ] Delete stray EBS volumes, snapshots, AMIs
- [ ] Billing → Bills → Charges by service
- [ ] Commit notes and config

After Phase 10 this is one `terraform destroy`.
