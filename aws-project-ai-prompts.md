# AI Prompt Pack — One Set Per Phase

For use in Claude Code (or any AI) with `aws-wordpress-project-strategy.md` in the same folder.

**The rule:** one phase per session. Never ask for the whole project — if AI writes everything and you accept it, you'll have a repo you can't explain in an interview.

Each phase has the same four prompts: **before** (understand), **during** (debug), **after** (review), **notes** (capture).

---

## Session opener — paste once per session

```
Read aws-wordpress-project-strategy.md in this folder.

I'm on Phase <N>. I'm a WordPress developer learning AWS on a Free-plan
account in ap-south-1 with $100 credits. I tear everything down at the
end of each session.

Help me with Phase <N> only. Don't jump ahead to later phases, and
don't write code for steps I haven't reached yet. When I hit an error,
explain the cause before giving the fix.

Whenever I upload an image or screenshot, automatically save it into
notes/images/<descriptive-name>.png, attach it at the appropriate step
in notes/phase-<N>.md, and confirm the placement with me in your reply.
```

---

# PHASE 1 — WordPress on EC2

**Before**
```
Explain each choice in the EC2 launch wizard and what goes wrong if I
pick it badly: AMI, instance type, key pair, security group rules,
storage type and size. Keep it short.
```

**During (debug)**
```
SSH won't connect. Here's the exact command and error, and my security
group inbound rules:
[paste]
```
```
I get 502 Bad Gateway. Here's my nginx config and the output of
`ls /run/php/`:
[paste]
```
```
This MySQL command failed. Error:
[paste]
```

**After (review)**
```
Here's my nginx config and wp-config.php with passwords removed.
Review for mistakes, bad permissions and security issues before I
move to Phase 2.
[paste]
```

**Notes**
```
I finished Phase 1. What I did: [summary]. What broke: [list].
Write notes/phase-1.md — what EC2 is in one line, why you'd choose it
over managed hosting, what surprised me, what it cost, how to delete it.
```

---

# PHASE 2 — Domain and HTTPS

**Before**
```
Explain what an Elastic IP actually is, why a Lightsail-style static IP
matters for DNS, and why Certbot needs DNS resolving before it can
issue a certificate.
```

**During**
```
`dig lab.asaxenadev.com +short` returns nothing / the wrong IP. Here's
my DNS record in hPanel:
[paste]
```
```
Certbot failed. Here's the full output and my nginx server block:
[paste]
```
```
Site loads over HTTPS but CSS and images are broken / mixed content
warnings. Here's my wp-config WP_HOME and WP_SITEURL:
[paste]
```

**After**
```
Check my nginx config after Certbot modified it. Is the HTTP to HTTPS
redirect correct, and is anything missing for WordPress?
[paste]
```

**Notes**
```
Phase 2 done. Write notes/phase-2.md covering Elastic IP, the DNS
A record, and Let's Encrypt — including why ACM couldn't be used here.
```

---

# PHASE 3 — Deploy pipeline

**Before**
```
Explain the difference between a CI job and a CD job, and why the
deploy job should use `needs:` on the test job. Also explain what a
concurrency group prevents.
```

**During**
```
Write the deploy workflow from Phase 3 of the strategy file. My plugin
lives at wp-content/plugins/<name>, my tests are `composer run phpcs`
and `composer run phpunit`. Use the atomic symlink version.
```
```
The Actions run failed. Here's the log:
[paste]
```
```
rsync says permission denied writing to /var/www/html/wp-content/.
What's the cleanest fix that doesn't make the directory world-writable?
```

**After**
```
Review this workflow for security problems: secret handling, what
gets deployed that shouldn't, and whether a failed deploy could leave
the site broken.
[paste]
```

**Notes**
```
Phase 3 done. Write notes/phase-3.md. Include what happened when I
deliberately failed a test, and explain the atomic deploy in two lines
so I can repeat it in an interview.
```

---

# PHASE 4 — Database to RDS

**Before**
```
Explain why a security group should reference another security group
instead of an IP range, and what actually happens during an RDS
Multi-AZ failover.
```

**During**
```
I can't connect to RDS from the instance. Here's the mysql command,
the error, and both security groups' inbound rules:
[paste]
```
```
The mysqldump import failed. Error:
[paste]
```
```
Site loads but is very slow after moving to RDS. What are the likely
causes and how do I check each?
```

**After**
```
I've moved the database to RDS. What should I check before calling
this done — connection limits, backups, encryption, anything else?
```

**Notes**
```
Phase 4 done. Write notes/phase-4.md: RDS vs local MySQL, when each
is the right call, what Multi-AZ did during my forced failover, and
the exact steps to migrate a WordPress DB.
```

---

# PHASE 5 — S3 and CloudFront

**Before**
```
Explain how an EC2 instance role gives the AWS SDK credentials without
any keys in a file, and why that's better than an access key in
wp-config.php.
```

**During**
```
Write an IAM policy for my S3 bucket <name> that gives the offload
plugin exactly what it needs and nothing more.
```
```
The offload plugin says access denied. Here's my policy and the error:
[paste]
```
```
CloudFront returns 403 for my media. Here's my bucket policy and my
origin access setting:
[paste]
```

**After**
```
Review my bucket configuration: public access settings, bucket policy,
encryption and lifecycle rule. Anything unsafe or missing?
[paste]
```

**Notes**
```
Phase 5 done. Write notes/phase-5.md covering S3 offload, why it's a
prerequisite for multiple web servers, storage classes, and how
CloudFront fronts the bucket.
```

---

# PHASE 6 — Harden it

**Before**
```
Explain IAM policy evaluation: identity policies, resource policies,
explicit deny, and permission boundaries. Use my S3 bucket and instance
role as the example.
```

**During**
```
Show me how to fetch the DB password from Secrets Manager inside
wp-config.php, including caching so it isn't fetched on every request.
```
```
I removed s3:PutObject from the role and got this error on upload.
Explain exactly what the message is telling me:
[paste]
```
```
SSM Session Manager won't connect. Here's the instance role's attached
policies and the agent status:
[paste]
```

**After**
```
Audit my setup for security: instance role permissions, security group
rules, what's encrypted, where secrets live, what's exposed to the
internet. List issues worst-first.
[paste]
```

**Notes**
```
Phase 6 done. Write notes/phase-6.md. Include the exact access-denied
message I got and what it taught me about policy evaluation.
```

---

# PHASE 7 — Email and monitoring

**Before**
```
Explain SPF, DKIM and DMARC in plain terms, and what each one actually
proves to a receiving mail server.
```

**During**
```
SES says my domain isn't verified. Here are the DKIM CNAMEs I added
in hPanel and the dig output:
[paste]
```
```
WordPress test email fails. Here's the WP Mail SMTP error and my
settings (credentials redacted):
[paste]
```
```
CloudWatch shows no memory or disk metrics. What's missing?
```

**After**
```
Suggest which alarms are actually worth having for a small WordPress
site, and which are noise. I want alerts I'd act on, not ones I'd mute.
```

**Notes**
```
Phase 7 done. Write notes/phase-7.md covering SES setup, the sandbox
restriction, and which metrics need the CloudWatch agent.
```

---

# PHASE 8 — Cache

**Before**
```
Explain object cache vs page cache with WordPress specifics: what each
stores, which users benefit, and why a logged-in-heavy site needs the
object cache.
```

**During**
```
redis-cli ping from the instance times out. Here's the ElastiCache
security group and the instance's security group:
[paste]
```
```
The Redis Object Cache plugin says "not connected". Here's my
wp-config Redis constants and `php -m | grep redis`:
[paste]
```

**After**
```
I've got Query Monitor numbers with and without the object cache:
[paste]
Explain what changed and what didn't, and why.
```

**Notes**
```
Phase 8 done. Write notes/phase-8.md: what Redis stores, the three
pieces needed (server, php-redis, drop-in plugin), and when local
Redis beats ElastiCache.
```

---

# PHASE 9 — Scale it

**Before**
```
Explain what breaks when WordPress runs on two servers behind a load
balancer, and how each problem is solved. Cover uploads, object cache,
sessions and cron.
```

**During**
```
My target group shows instances as unhealthy. Here's the health check
config and the security groups:
[paste]
```
```
The site loads through the ALB but logged-in sessions keep dropping.
What's the cause and the correct fix — not sticky sessions?
```
```
Give me the wp-config change to disable WP-Cron and the correct way to
run it from one place instead.
```

**After**
```
Give me a teardown checklist for everything I created in this phase,
in the right order, so nothing is left billing.
```

**Notes**
```
Phase 9 done. Write notes/phase-9.md. Focus on what broke with two
servers — that's the interview answer I want to be able to give.
```

---

# PHASE 10 — Terraform

**Before**
```
Explain Terraform state: what it is, why it can't be committed to Git,
and what happens when someone changes a resource in the console.
```

**During**
```
Write Terraform for what I built in Phases 1-5, following the strategy
file. Split into main.tf, variables.tf, outputs.tf. Include
default_tags for cost tracking, and put the Phase 1 install commands
into install.sh as user data.
```
```
terraform apply failed. Here's the error and the resource block:
[paste]
```
```
I created something in the console earlier and Terraform wants to
destroy it. What are my options?
```

**After**
```
Review my Terraform: hardcoded values that should be variables,
anything insecure, and whether `destroy` would leave anything behind.
[paste]
```

**Notes**
```
Phase 10 done. Write notes/phase-10.md: what IaC solves, state
management, drift, and why this phase made every later session cheaper.
```

---

# PHASE 11 — Cost

**Before**
```
Explain what actually drives an AWS bill, and which of my resources
charge by the hour regardless of traffic.
```

**During**
```
Here's my Cost Explorer breakdown by service for the project so far:
[paste]
Explain what each line is and whether it looks right for what I built.
```
```
Something is still charging me and I thought I deleted everything.
How do I find orphaned resources across the account?
```

**After**
```
Based on my CloudWatch CPU and memory data, was t3.micro the right
size? What would you pick for a real small-business WordPress site,
and why?
[paste]
```

**Notes**
```
Phase 11 done. Write notes/phase-11.md: what my project actually cost,
which service surprised me, and the cost-optimisation levers in order
of impact.
```

---

# PHASE 12 — The leftovers

**Per service**
```
Give me a 30-minute exercise for <service> that shows what it does,
using my existing setup where possible. Then tell me the one thing an
interviewer would ask about it, and the answer.
```

**Wrap-up**
```
Write notes/phase-12.md as a single reference table: service, what it
does in one line, when you'd reach for it, and the WordPress-adjacent
use case if there is one.
```

---

# END OF PROJECT

**README**
```
Write the repo README from my notes/ folder: an architecture summary,
what runs where, the reasoning behind each choice, and how to rebuild
it from the Terraform. Write it for a hiring manager who'll skim it in
90 seconds.
```

**Interview drill**
```
You're interviewing me for a senior WordPress role that lists AWS and
GitHub Actions. Ask me one question at a time based on what's in my
notes/ folder. After each answer, tell me what was weak and what a
strong version would have included.
```

**CV line**
```
Based on notes/ and the README, draft two CV lines about this work.
Claim only what I actually built. No vendor names I haven't used.
```

---

## What not to prompt

- "Build the whole project for me" — you'll accept code you can't explain
- "Give me the full install script" for Phase 1 — run it command by command instead; the breakages are the learning
- Anything with a real password, key or account number pasted in
- "Is this best practice?" — ask "what's the trade-off here?" instead, because that's the question an interviewer will ask
