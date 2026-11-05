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

## Current phase: 11 (Phase 10 Completed & Verified ✅)

Phase 10 (Codify it — Terraform & Enterprise GitOps) completed and verified:
- **Level 1 (Local Prototyping):** Terraform v1.16.6 installed; `infra/` provisioned `aws_security_group.web` and Ubuntu 24.04 `aws_instance.wp`. Verified live WordPress setup screen (`200 OK`).
- **Level 2 (Enterprise GitOps):**
  - **S3 & DynamoDB Backend:** S3 bucket `wp-lab-tfstate-538820337783` (versioned, SSE-S3 AES256, private) & DynamoDB lock table `wp-lab-tf-locks` provisioned via `bootstrap/main.tf`. Local state migrated cleanly (`terraform init -migrate-state`).
  - **Zero-Trust IAM OIDC:** AWS IAM Identity Provider `token.actions.githubusercontent.com` and IAM Role `GitHubActionsTerraformRole` established passwordless cryptographic authentication scoped to `repo:akshat009/Aws-wp-lab:*`.
  - **GitHub Actions Pipeline:** `.github/workflows/terraform.yml` runs automated `terraform init`, `validate`, `plan`, and `apply` on push/merge to `main` with on-demand `workflow_dispatch` destroy/apply options.
  - **Zero-Trust Enforced:** Deleted static root access key `AKIAX25BR4B3TYTG22TW` from AWS Console.
  - **Definition of Done Lifecycle Test Verified:** Executed `terraform destroy` via GitHub Actions (terminated instance & security group; site completely offline `ERR_CONNECTION_TIMED_OUT`), followed by `terraform apply` (re-provisioned new instance `i-0fca9a4b647516a51` with new IP `35.154.149.207` in 57s; verified live WordPress installer `200 OK`).
- `notes/phase-10.md` comprehensive documentation complete with all architecture diagrams, comparison tables, Gotchas 1–12, and interview Q&As (Q1–Q10).

Next session: Phase 11 (Cost: Cost Explorer shows a breakdown grouped by my tags).

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
