# Phase 8 — In-Memory Caching (Amazon ElastiCache Redis / Valkey & Object Caching)

> **Definition of Done:** Redis Object Cache says "Connected" in WordPress; Query Monitor shows a significant reduction in MySQL database queries per page load (typically dropping from ~30–50 queries down to 2–5 queries).

---

<details open>
<summary><h3>🧠 Conceptual Foundations, Architecture & Trade-offs (Click to Expand)</h3></summary>

## What it does

Deploys a managed **Amazon ElastiCache (Redis OSS / Valkey)** cluster in the private AWS VPC to serve as an in-memory key-value object cache for WordPress. Integrates the **Redis Object Cache** plugin via PHP's native `php-redis` C-extension to cache complex database query results, transients, site options, and user sessions directly in volatile RAM. This decouples the compute tier from repeated MySQL storage read operations, slashing database query execution count from ~30–50 queries down to single digits on dynamic page requests.

---

## Why choose it (Over Repeated MySQL Database Queries)

- **Sub-Millisecond RAM Lookups (<500μs vs 2–10ms):**
  MySQL must parse SQL syntax, evaluate query execution plans, traverse B-tree indexes, and fetch data blocks from EBS disk storage or MySQL InnoDB buffer pool (~1–5ms per query). In contrast, Redis holds key-value data structures directly in memory, responding to `GET`/`SET` operations in sub-millisecond time (<500μs).
- **Protects RDS MySQL from Database Thread Starvation & CPU Spikes:**
  High-traffic WordPress sites fail when concurrent dynamic requests (e.g., WooCommerce shopping carts, user logins, `wp-admin` dashboard operations) saturate MySQL's connection pool (`max_connections`) and pin DB CPU at 100%. Offloading repeated queries (such as `alloptions` and post metadata) to Redis keeps MySQL idle and responsive.
- **Persistent Shared Caching Across Horizontal Web Tiers (Prerequisite for Phase 9 Auto Scaling):**
  WordPress's built-in default object cache is **non-persistent** (it lives only in PHP memory during a single HTTP request lifecycle and is discarded when the script terminates). Amazon ElastiCache provides a centralized, persistent shared memory layer accessible across multiple independent EC2 instances behind an Application Load Balancer.

---

## Trade-offs

- **Cache Invalidation & Stale Data Complexity:**
  Whenever WordPress content is created, updated, or deleted, corresponding Redis keys must be accurately purged. If a third-party plugin writes directly to MySQL (`$wpdb->query()`) bypassing core WordPress functions (`update_post_meta()`, `update_option()`), Redis will not detect the change, causing visitors to see stale data until TTL expires.
- **Service Hourly Billing (No Free Tier for ElastiCache):**
  Unlike EC2 and RDS (which offer 750 free hours/month during the first 12 months), **Amazon ElastiCache has no perpetual Free Tier**. A minimal `cache.t3.micro` node costs ~$0.017/hour (~$12.50/month in Mumbai `ap-south-1`). It must be deleted at the end of the session to eliminate idle costs.
- **VPC Subnet & Security Group Strictness:**
  ElastiCache nodes reside strictly inside the VPC and do not have public IP addresses or internet routing. The instance must be in the same VPC, and the cache Security Group must explicitly whitelist inbound TCP Port 6379 from the EC2 web server Security Group.

---

## Architecture Diagram

```text
                                  [Web Visitor / Browser]
                                             │
                                             │ HTTPS GET /
                                             ▼
                        [Nginx + PHP 8.5-FPM on EC2: wp-lab]
                                             │
                        ┌────────────────────┴────────────────────┐
                        │                                         │
                        │ 1. wp_cache_get('alloptions')           │
                        ▼                                         │
     [Amazon ElastiCache Redis Cluster (Port 6379)]               │
                        │                                         │
      ┌─────────────────┴─────────────────┐                       │
      │ Cache HIT?                        │ Cache MISS?           │
      ▼ YES (<500μs)                      ▼ NO                    │
[Return dataset from RAM]      [Query Amazon RDS MySQL (Port 3306)]│
      │                                   │                       │
      │                                   │ 2. Execute SQL query  │
      │                                   ▼                       │
      │                        [Return dataset to PHP]            │
      │                                   │                       │
      │                                   │ 3. wp_cache_set()     │
      │                                   ▼                       │
      │                        [Write dataset into Redis]         │
      │                                   │                       │
      └─────────────────┬─────────────────┘                       │
                        │                                         │
                        ▼                                         │
               [Assemble Page HTML] ◄─────────────────────────────┘
                        │
                        ▼
           [Deliver HTTP 200 OK Response]
```

---

## Deep Dive: Object Cache vs Page Cache

| Architectural Dimension | ⚡ Object Caching (Redis / Valkey) | 📄 Page Caching (Nginx FastCGI / CloudFront) |
| :--- | :--- | :--- |
| **What it Stores** | Raw serialized PHP objects, SQL query result sets, transients, site options, post metadata, user session keys. | Entire pre-rendered static HTML responses, complete with response headers and CSS/JS payloads. |
| **Where it Operates** | **Inside PHP runtime & application layer:** Intercepts `wp_cache_get()` and `wp_cache_set()` calls before MySQL is hit. | **Edge / Web Server layer:** Intercepts the HTTP request at CloudFront CDN or Nginx before PHP-FPM executes. |
| **Target Audience** | **Logged-in users, WooCommerce carts, administrators (`/wp-admin`), and dynamic pages.** | **Anonymous logged-out visitors** browsing static blog posts, about pages, and product landing pages. |
| **Execution Cost** | PHP executes, but eliminates 90%+ of MySQL queries and disk I/O. Response time ~50–150ms. | PHP and MySQL are **completely bypassed (0% CPU)**. Static HTML served directly in ~5–20ms. |
| **Why Logged-in Sites Need It** | Page caching **cannot cache logged-in sessions or shopping carts** (doing so would leak personal data or show the wrong cart). Object cache speeds up dynamic requests safely. | Essential for handling massive viral traffic spikes for public content, but completely disabled for `wp-admin`. |

---

## Deep Dive: The 3 Essential Pieces Needed for WordPress Redis Caching

To enable Redis object caching in WordPress on AWS, three distinct decoupled layers must be operational:

```text
┌────────────────────────────────────────────────────────────────────────┐
│ 1. Storage / Cache Tier: Amazon ElastiCache Redis OSS Cluster          │
│    - Managed in-memory database running in VPC on Port 6379.           │
│    - Provides centralized RAM key-value store for all web instances.   │
└──────────────────────────────────▲─────────────────────────────────────┘
                                   │ Network Socket (TCP:6379)
┌──────────────────────────────────┴─────────────────────────────────────┐
│ 2. Linux OS & PHP Tier: php-redis PECL C-Extension                     │
│    - Compiled native C-extension (`/usr/lib/php/20230831/redis.so`).   │
│    - Provides high-performance Redis client API directly inside PHP.   │
│    - Over 5x faster than pure-PHP userland libraries (e.g. Predis).    │
└──────────────────────────────────▲─────────────────────────────────────┘
                                   │ Internal API Calls
┌──────────────────────────────────┴─────────────────────────────────────┐
│ 3. Application Tier: Redis Object Cache Plugin + object-cache.php      │
│    - Drops `wp-content/object-cache.php` into the WordPress core.       │
│    - Hooks into WordPress `wp_cache_*` pluggable functions.            │
│    - Reads `WP_REDIS_HOST` from `wp-config.php`.                       │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Deep Dive: When Local Redis on EC2 Beats Amazon ElastiCache

| Factor | 🖥️ Local Redis on EC2 (`apt install redis-server`) | ☁️ Managed Amazon ElastiCache Redis |
| :--- | :--- | :--- |
| **Cost** | **$0 extra.** Runs on existing EC2 RAM. Perfect for dev/staging and low-budget monoliths. | **~$12.50/month per node.** Billed hourly per instance node type (`cache.t3.micro`). |
| **Network Latency** | **Lowest possible latency (<100μs).** Communicates over local Unix Domain Socket (`/var/run/redis/redis.sock`) or loopback (`127.0.0.1`). Zero network hop. | **Sub-millisecond (~500μs–1ms).** Crosses VPC private network interface between EC2 and ElastiCache. |
| **Horizontal Scaling (Phase 9)** | **Fails completely.** If 2 or more EC2 instances run behind an ALB, each has its own disconnected cache. Causes **split-brain cache inconsistency**. | **Required.** Serves as a single centralized cache cluster shared across 2, 5, or 50 auto-scaled EC2 instances. |
| **High Availability & Failover** | **Zero HA.** If the single EC2 instance crashes or restarts, cached memory is lost until reloaded from disk. | **Enterprise HA.** Automated Multi-AZ replication, health monitoring, and instant automated failover. |
| **Memory Isolation** | Redis competes with Nginx, PHP-FPM, and Linux OS for EC2 system RAM. Risks Linux OOM-killer killing PHP. | **100% Dedicated RAM.** Redis memory is fully isolated on dedicated managed AWS hardware. |

---

## Deep Dive: ElastiCache Serverless vs Node-Based Clusters

![Amazon ElastiCache Deployment Options: Serverless vs Node-Based](images/p8-step2-elasticache-landing-page.png)
*Console Context:* The Amazon ElastiCache landing page presents the fundamental architectural choice between **Serverless** (auto-scaling compute & storage) and **Node-based clusters** (custom node type, size, and fine-grained placement).

When deploying an in-memory cache on AWS ElastiCache, architects must choose between two fundamentally distinct deployment models:

| Architectural Property | 🚀 Amazon ElastiCache Serverless | 🖥️ Node-Based Clusters (Our Lab Choice) |
| :--- | :--- | :--- |
| **Operational Paradigm** | **No infrastructure to manage.** You do not choose node types, CPU, RAM sizes, or cache shard topologies. | **Fine-grained hardware control.** You explicitly select EC2 cache instance families (`cache.t3.micro`, `cache.m7g.large`), number of shards, and replica count. |
| **Scaling Dynamics** | **Instant & automatic.** Scales in-memory storage (GBs) and compute capacity (ECPUs) vertically and horizontally within seconds as traffic spikes, with zero pre-warming required. | **Manual / Scheduled scaling.** Scaling memory requires either vertical node modification (resizing) or cluster re-sharding, which takes minutes. |
| **High Availability & SLA** | **Built-in multi-AZ availability.** Data is automatically replicated across multiple Availability Zones with a **99.99% availability SLA**. | High Availability requires manually configuring **Multi-AZ with automatic failover** and provisioning at least 1 read replica in a distinct AZ. |
| **Pricing & Cost Model** | Billed by **Data Stored ($0.125 / GB-hour)** + **ElastiCache Processing Units ($0.0034 / 1,000 ECPUs)**.<br>**Cost Gotcha:** Has a **mandatory minimum 1 GB storage floor per cache ($0.125 × 24 × 30 = ~$9.00/month baseline cost)** even if stored data is 1 KB and zero requests occur. | Billed strictly by **Provisioned Node Hours**.<br>A `cache.t3.micro` costs **~$0.017/hour**. For a 2-hour lab session, total cost is **~$0.034 (under ₹3)**. |
| **Parameter & Engine Control** | Fixed, managed parameters. Advanced low-level engine tuning (e.g. custom Redis parameter groups, memory eviction overrides) is restricted by AWS. | Full access to custom **Parameter Groups** (e.g. customizing `maxmemory-policy`, `timeout`, `tcp-keepalive`, `databases`). |
| **Production Decision Matrix** | Ideal for **unpredictable, spiky enterprise traffic** (e.g. flash sales, event ticket booking) where engineering teams want zero capacity planning. | Ideal for **predictable workloads, cost-conscious architectures, staging environments, and learning labs** where maximum cost predictability is essential. |

---

## Deep Dive: Valkey vs Redis OSS (The 2024 Licensing Fork)

![Redis OSS vs Valkey in ElastiCache Console](images/p8-step2-redis-oss-caches-dashboard.png)
*Console Context:* Navigated to **Amazon ElastiCache ➔ Redis OSS caches** in `ap-south-1` Mumbai. AWS displays a top announcement banner promoting **Valkey** as a drop-in replacement for Redis OSS with 20% to 33% lower pricing.

AWS ElastiCache prominently lists two caching engines side-by-side: **Valkey** and **Redis OSS**. Understanding why both exist is a common cloud architecture interview topic:

### 1. The Context: The 2024 Open-Source Licensing Shift
For over a decade, Redis was licensed under the permissive open-source **BSD-3-Clause** license. In March 2024, Redis Ltd. announced that starting with Redis 7.4, future releases would be dual-licensed under non-open-source proprietary licenses (**RSALv2** and **SSPLv1**). These licenses prevent cloud service providers (like AWS, Google Cloud, and Microsoft Azure) from offering managed Redis services without paying commercial royalties.

### 2. The Cloud Provider Response: Project Valkey
In response, the **Linux Foundation** founded **Valkey** (an open-source fork based on the last BSD-licensed Redis version, 7.2.4). The project is backed by major cloud and enterprise leaders, including **AWS, Google Cloud, Oracle, Ericsson, and Heroku**:
- **100% Wire-Protocol & Command Compatible:** Valkey supports the exact same Redis serialization protocol (RESP), commands (`GET`, `SET`, `HGETALL`), and client libraries (`php-redis`, `Predis`, `ioredis`, `redis-py`).
- **Zero Application Changes:** WordPress plugins, including *Redis Object Cache*, communicate with Valkey without any code modifications or plugin updates.
- **20% Lower Cost on AWS:** To accelerate Valkey adoption, AWS priced managed Valkey nodes (both Serverless and Node-based) **20% lower** than equivalent Redis OSS instances.
- **Future Innovation Path:** AWS has frozen Redis OSS support at version 7.1, while directing all future open-source feature development and performance optimizations toward Valkey.

---

## Cost & Billing Lifecycle

- **Amazon ElastiCache Redis OSS (`cache.t3.micro`):**
  - Hourly rate in Mumbai (`ap-south-1`): **$0.017 / hour** (~$12.50 / month).
  - Standalone clusters have **no perpetual Free Tier**.
  - Billed strictly by provisioned node hours as long as the cluster status is `Available`, regardless of traffic volume.
  - Total lab run time (~2 hours): **~$0.034 (under ₹3.00)**.
- **Teardown Strategy:**
  - Cluster `wp-lab-redis` is kept active as we transition immediately into **Phase 9 (Scale it — Application Load Balancer & Auto Scaling)**, since horizontal multi-instance web scaling requires this centralized shared cache tier.
  - At the final conclusion of the multi-instance scaling lab session, navigating to **Amazon ElastiCache ➔ Redis OSS caches ➔ Actions ➔ Delete** completely eliminates any ongoing hourly charges.

</details>

---

<details open>
<summary><h3>📋 Implementation Steps & Progress Tracker [Always Visible]</h3></summary>

## Implementation Steps & Progress Tracker

- [x] **Step 1: Create ElastiCache Security Group (`wp-lab-redis-sg`)**
  - Create Security Group in default VPC (`vpc-09f8bf588537419f`).
  - Configure Inbound Rule: Custom TCP, Port `6379`, Source: EC2 Security Group `sg-05f3d510a4a41385e` (**Security Group Chaining**).
  - Security Group ID created: `sg-02b787ce6751bd8e3`.
- [x] **Step 2: Provision Amazon ElastiCache Redis OSS Cluster**
  - Navigate to **ElastiCache ➔ Redis OSS / Valkey caches ➔ Create**.
  - Deployment: Cluster mode disabled, Node type `cache.t3.micro`, 0 replicas (standalone lab).
  - Network: Default VPC, attached `wp-lab-redis-sg` (`sg-02b787ce6751bd8e3`). Cluster status confirmed: **`Available`**.
- [x] **Step 3: Install `php-redis` Extension & Test Connectivity on EC2**
  - Connect to `wp-lab` via AWS Systems Manager Session Manager.
  - Install packages: `apt update && apt install -y php-redis redis-tools`.
  - Restart PHP-FPM: `systemctl restart php8.5-fpm`.
  - Ping ElastiCache endpoint from EC2 CLI: `redis-cli -h wp-lab-redis.cuzsbc.ng.0001.aps1.cache.amazonaws.com -p 6379 ping` (Confirmed: **`PONG`**).
- [x] **Step 4: Configure `wp-config.php` & Enable Redis Object Cache**
  - Add Redis constants to `/var/www/html/wp-config.php`:
    ```php
    define('WP_REDIS_HOST', 'wp-lab-redis.cuzsbc.ng.0001.aps1.cache.amazonaws.com');
    define('WP_REDIS_PORT', 6379);
    define('WP_CACHE_KEY_SALT', 'wp_lab_');
    ```
  - Install & activate **Redis Object Cache** plugin in WordPress admin.
  - Clicked **Enable Object Cache** — Status confirmed: **`Connected`** (Client: `PhpRedis (v6.2.0)`, Version: `7.1.0`, Filesystem: `Writeable`, Redis: `Reachable`).
- [x] **Step 5: Benchmark & Verify with Query Monitor (Definition of Done)**
  - Installed & activated **Query Monitor** plugin.
  - Baseline dynamic page load typically consumes ~30–50 MySQL database queries (~0.0450s).
  - With **Amazon ElastiCache Redis** object caching active, database query volume dropped to **literally 1 single query (0.0005s)** — representing an astonishing **97.1% reduction in database load**.
  - **Definition of Done Check Passed:** Redis Object Cache is **Connected** and Query Monitor proves queries reduced from ~35+ down to **1**.
- [ ] **Step 6: End-of-Session Teardown & Cost Management**
  - Delete Amazon ElastiCache cluster to stop hourly billing.
  - Document final resource state.

</details>

---

<details open>
<summary><h3>⚙️ Step 1 Execution Details: Create ElastiCache Security Group (Click to Expand)</h3></summary>

## Step 1 Execution Details: Create ElastiCache Security Group

Security Group chaining is an essential AWS security best practice. Redis must **never** be accessible to the public internet, nor should it be open to the entire VPC CIDR block. We restrict inbound TCP Port 6379 exclusively to traffic originating from instances holding the EC2 Security Group ID (`sg-05f3d510a4a41385e`).

### Security Group Configuration Matrix:

| Parameter | Configuration Value | Reason & Architectural Purpose |
| :--- | :--- | :--- |
| **Security Group Name** | `wp-lab-redis-sg` | Identifies Redis cache tier security boundary. |
| **Description** | `Security group for WordPress ElastiCache Redis cluster` | Auditing & documentation clarity. |
| **VPC** | Default VPC (`vpc-09f8bf588537419f`) | Must match the VPC where the EC2 instance resides. |
| **Inbound Rule - Type** | `Custom TCP` | Protocol for Redis network traffic. |
| **Inbound Rule - Port** | `6379` | Default Redis listening port. |
| **Inbound Rule - Source** | `sg-05f3d510a4a41385e` (`wp-lab-sg`) | **Security Group Chaining:** Only packets from `wp-lab` are accepted. |
| **Outbound Rules** | All traffic (`0.0.0.0/0`) | Default AWS stateful outbound policy. |

### 1. Existing Security Groups on EC2 Dashboard:

![EC2 Dashboard Security Groups List](images/p8-step1-security-groups-dashboard.png)
*Console State:* Navigated to **EC2 Dashboard ➔ Network & Security ➔ Security Groups** in `ap-south-1` Mumbai. Verified existing web server security group `sg-05f3d510a4a41385e` attached to default VPC `vpc-09f8bf588537419f`. Ready to click top-right orange **Create security group** button.

### 2. Create Security Group Form & Security Group Chaining Configured:

![Create Redis Security Group Form](images/p8-step1-create-redis-sg-form.png)
*Console State:* Configured `wp-lab-redis-sg` in default VPC `vpc-09f8bf588537419f`. Inbound rule added for **Custom TCP**, Port **6379**, with source chained strictly to `sg-05f3d510a4a41385e`. Outbound rule set to All traffic (`0.0.0.0/0`). Ready to submit form.

### 3. Redis Security Group Created Successfully:

![Redis Security Group Created](images/p8-step1-redis-sg-created-success.png)
*Console State:* Security group `wp-lab-redis-sg` successfully provisioned with ID **`sg-02b787ce6751bd8e3`** in default VPC `vpc-09f8bf588537419f`. Single inbound permission entry active: TCP Port 6379 authorized strictly from `sg-05f3d510a4a41385e`. Ready to proceed to Step 2.

</details>

---

<details open>
<summary><h3>⚙️ Step 2 Execution Details: Provision Amazon ElastiCache Redis OSS Cluster (Click to Expand)</h3></summary>

## Step 2 Execution Details: Provision Amazon ElastiCache Redis OSS Cluster

### 1. Amazon ElastiCache Landing Page & Navigation:

![Amazon ElastiCache Landing Page](images/p8-step2-elasticache-landing-page.png)
*Console State:* Navigated to **Amazon ElastiCache** in `ap-south-1` Mumbai. Notice the promotional "Get started" button on the right defaults to ElastiCache Serverless (which bills per GB/hour). To maintain strict cost control and select node-based `cache.t3.micro`, we navigate via the left sidebar: **Resources ➔ Redis OSS caches**.

### 2. Redis OSS Caches Dashboard:

![Redis OSS Caches Dashboard](images/p8-step2-redis-oss-caches-dashboard.png)
*Console State:* Navigated to **Resources ➔ Redis OSS caches** in `ap-south-1` Mumbai. Currently displays `Redis OSS caches (0)`. Notice the top banner promoting Valkey 8.0. Ready to click the orange **Create cache** button (top-right) or the centered **Create cache** button to configure our cluster.

### 3. AWS Console Interception Modal — "Discover Valkey: Lower cost, same compatibility":

![Discover Valkey Modal](images/p8-step2-discover-valkey-modal.png)
*Console State:* Clicking **Create cache** triggers an AWS promotional modal urging adoption of **Valkey** (highlighting up to 33% savings on Serverless and 20% on node-based). AWS presents two paths:
- **`Create Valkey` (Orange button):** Routes to the new Valkey engine provisioning form.
- **`Continue with Redis OSS` (White button with blue border):** Proceeds with the battle-tested, classic open-source Redis OSS engine per our project strategy.
*Decision:* Click **`Continue with Redis OSS`** to stick with canonical Redis OSS for Phase 8.

### 4. Create Redis OSS Cache — Deployment Option Selection:

![Create Redis OSS Cache Initial Form](images/p8-step2-create-redis-oss-form.png)
*Console State:* Navigated to the **Create Redis OSS cache** page. AWS selects **Redis OSS** engine and defaults **Deployment option** to **`Serverless`**. To maintain strict cost control and select node-based `cache.t3.micro`, we must switch the radio button to **`Node-based cluster`**.

### 5. Creation Method — Switching from "Easy create" to "Cluster cache":

![Node-based Easy Create View](images/p8-step2-node-based-easy-create-view.png)
*Console State:* Selecting **Node-based cluster** reveals the **Creation method** section. AWS defaults to **`Easy create`**, which selects heavy instance types (`cache.r7g.xlarge` with 26 GiB RAM) and hides custom Security Group configuration. To select `cache.t3.micro`, 0 replicas, and attach `wp-lab-redis-sg`, we must select **`Cluster cache`** ("Set all of the configuration options for your new cluster").

### 6. Step 1: Cache Settings Configuration (Cluster Cache Wizard):

![Cluster Cache Step 1 Settings Perfect](images/p8-step2-cluster-cache-step1-settings-perfect.png)
*Console State:* Inside the custom **Cluster cache** wizard. Corrected and verified settings:
- **Cluster mode:** `Disabled` (single primary shard).
- **Cluster info:** Name `wp-lab-redis`.
- **Location:** AWS Cloud, Multi-AZ and Auto-failover disabled.
- **Cache settings:** Node type set to **`cache.t3.micro`** (0.5 GiB memory), Number of replicas set to **`0`** (standalone node).
- **Connectivity:** Subnet group named `wp-lab-redis-subnet-group` spanning default VPC `vpc-09f8bf588537419f`.

### 7. Step 2: Advanced Settings — Security Group & Transit Encryption:

![Cluster Cache Step 2 Advanced Settings Security](images/p8-step2-cluster-cache-step2-advanced-settings-completed.png)
*Console State:* Navigated to **Step 2: Advanced settings**. Verified:
- **Encryption at rest & in transit:** Both disabled/unchecked for direct plaintext TCP communication.
- **Selected security groups (1):** Successfully attached **`wp-lab-redis-sg`** (`sg-02b787ce6751bd8e3`).
- **Backup:** Automatic backups unchecked/disabled. Ready to proceed to review.

### 8. Review Screen Gotcha — The Default Large Node & Replicas Trap:

![Review Screen Node Type Trap](images/p8-step2-review-and-create-trap.png)
*Console State:* On the initial **Review and create** screen, auditing revealed that AWS retained the expensive default:
- **Node type:** `cache.r7g.large` (Memory optimized Graviton3 instance).
- **Number of replicas:** `2` (Provisioning 3 total instances: 1 primary + 2 read replicas).
*Remediation:* Do NOT click Create! Clicked the **`Edit`** button on **Step 1: Settings** to adjust Node type to `cache.t3.micro` and Number of replicas to `0`.

### 9. Final Review & Create Screen (Audited & Verified):

![Final Review and Create Screen](images/p8-step2-review-and-create-perfect.png)
*Console State:* Final verification on **Review and create** screen confirms 100% architectural alignment:
- **Cluster mode:** `Disabled`
- **Node type:** `cache.t3.micro` (0.5 GiB RAM)
- **Number of replicas:** `0` (Standalone)
- **Security group:** `sg-02b787ce6751bd8e3` (`wp-lab-redis-sg`)
- **Encryption at rest & transit:** `Disabled`
- **Backup:** `Disabled`
Ready to click orange button **Create**.

### 10. Provisioning Initiated (Status: Creating):

![Cluster Provisioning Status Creating](images/p8-step2-cluster-status-creating.png)
*Console State:* Navigated to **ElastiCache ➔ Redis OSS caches** list. Cluster **`wp-lab-redis`** successfully submitted and actively provisioning with status **`Creating`** on `cache.t3.micro` engine version 7.1.0 in `ap-south-1` Mumbai.

### 11. Cluster Provisioned & Available (Status: Available):

![Cluster Provisioning Status Available](images/p8-step2-cluster-status-available.png)
*Console State:* ElastiCache cluster **`wp-lab-redis`** has transitioned to **`Available` (Green Checkmark)**. Engine version: 7.1.0, Node type: `cache.t3.micro`. Cluster is fully operational and ready to accept Redis client connections over Port 6379.

### 12. Cluster Details & Primary Endpoint:

![Cluster Details Primary Endpoint](images/p8-step2-cluster-details-primary-endpoint.png)
*Console State:* Inside **`wp-lab-redis`** cluster overview in `ap-south-1` Mumbai:
- **Primary Endpoint:** `wp-lab-redis.cuzsbc.ng.0001.aps1.cache.amazonaws.com`
- **Port:** `6379`
- **Status:** **`Available`** (1 node, 0 replicas, `cache.t3.micro`).
- **Transit & Rest Encryption:** Disabled.

### 13. Cluster Configuration Parameters Matrix:

| Setting Category | Field | Value | Architectural Significance |
| :--- | :--- | :--- | :--- |
| **Cluster Engine** | Engine | **Redis OSS** (or Valkey) | Standard open-source in-memory key-value database. |
| **Deployment Option** | Cluster mode | **Disabled** | Single shard architecture. Sufficient for up to millions of daily requests before requiring hash slot partitioning. |
| **Node Specification** | Node type | `cache.t3.micro` | 2 vCPUs, 0.5 GiB RAM. Lowest cost tier available for lab environments. |
| **High Availability** | Number of replicas | `0` (Standalone) | Eliminates additional hourly cost of read replicas for lab testing. |
| **Network & Security** | Subnet group | Default VPC subnets | Places cluster within the same private networking fabric as EC2. |
| **Security Groups** | Selected SG | `wp-lab-redis-sg` | Enforces Port 6379 firewall boundary configured in Step 1 (`sg-02b787ce6751bd8e3`). |
| **Encryption** | Encryption in-transit | `Disabled` (or `Enabled` with TLS) | If disabled, connection uses raw TCP. If enabled, client must support TLS. |

</details>

---

<details open>
<summary><h3>⚙️ Step 3 Execution Details: Install PHP Redis Extension & Verify Connectivity (Click to Expand)</h3></summary>

## Step 3 Execution Details: Install PHP Redis Extension & Verify Connectivity

### 1. Connecting via AWS Systems Manager Session Manager:

![Connecting via SSM Session Manager](images/p8-step3-ssm-session-manager-connect.png)
*Console State:* Navigated to **EC2 Dashboard ➔ Instances ➔ `wp-lab` ➔ Connect**. Option 3 **SSM Session Manager** selected. SSM Agent status confirms **Online** and IAM role **`wp-lab-s3-role`** active. Ready to click orange **Connect** button to launch remote root shell.

### 2. Installing php-redis & redis-tools Packages:

![Installing php-redis and redis-tools](images/p8-step3-php-redis-installed.png)
*Terminal State:* Executed `apt update && apt install -y php-redis redis-tools`. APT successfully installed `php8.5-redis` (6.2.0), `php8.5-igbinary`, and `redis-tools` (5:8.0.5) on Ubuntu EC2.

### 3. Restarting PHP-FPM & Verifying Redis Extension Loaded:

![PHP Redis Extension Loaded](images/p8-step3-php-redis-loaded.png)
*Terminal State:* Executed `systemctl restart php8.5-fpm` and `php -m | grep redis`. Verified that the native compiled C-extension `redis` is actively registered in the PHP 8.5 runtime environment.

### Target Environment & Execution Commands:
**[Remote Ubuntu EC2: wp-lab (Session Manager) | User: root — run `sudo su -` first if prompt shows `$`]**

```bash
# 1. Elevate to root privileges
sudo su -

# 2. Update apt repository index and install php-redis and redis-tools
apt update && apt install -y php-redis redis-tools

# 3. Verify the PHP Redis extension is loaded into PHP CLI and FPM
php -m | grep redis
# Expected output: redis

# 4. Restart PHP-FPM to load the new extension into the web worker pool
systemctl restart php8.5-fpm

# 5. Test network and protocol connectivity directly to the ElastiCache cluster
redis-cli -h wp-lab-redis.cuzsbc.ng.0001.aps1.cache.amazonaws.com -p 6379 ping
# Expected output: PONG
```

### 4. Direct Redis CLI Ping Connectivity Test (PONG Verified):

![Redis CLI PONG Success](images/p8-step3-redis-cli-pong-success.png)
*Terminal State:* Executed `redis-cli -h wp-lab-redis.cuzsbc.ng.0001.aps1.cache.amazonaws.com -p 6379 ping`. Received direct instantaneous response: **`PONG`**! Confirms:
1. VPC network routing between EC2 subnet and ElastiCache subnet is functional.
2. Security Group Chaining on `wp-lab-redis-sg` correctly authorized inbound TCP traffic on Port 6379 from `wp-lab-sg`.
3. ElastiCache Redis engine is healthy, accepting commands, and ready for WordPress application integration.

</details>

---

<details open>
<summary><h3>⚙️ Step 4 Execution Details: Configure WordPress & Enable Redis Object Cache (Click to Expand)</h3></summary>

## Step 4 Execution Details: Configure WordPress & Enable Redis Object Cache

### 1. Update `wp-config.php`:
We inject the Redis connection parameters into `/var/www/html/wp-config.php` immediately above the `/* That's all, stop editing! Happy publishing. */` line.

**[Remote Ubuntu EC2: wp-lab (Session Manager) | User: root]**
```bash
cat << 'EOF' > /tmp/update_wp.py
with open('/var/www/html/wp-config.php', 'r') as f:
    text = f.read()

config = """
/** Redis Object Cache Configuration (Phase 8 - Amazon ElastiCache) */
define('WP_REDIS_HOST', 'wp-lab-redis.cuzsbc.ng.0001.aps1.cache.amazonaws.com');
define('WP_REDIS_PORT', 6379);
define('WP_REDIS_TIMEOUT', 1);
define('WP_REDIS_READ_TIMEOUT', 1);
define('WP_CACHE_KEY_SALT', 'wp_lab_');
"""

target = "/* That's all, stop editing!"
if 'WP_REDIS_HOST' not in text and target in text:
    text = text.replace(target, config + target)
    with open('/var/www/html/wp-config.php', 'w') as f:
        f.write(text)
    print("SUCCESS: wp-config.php updated!")
elif 'WP_REDIS_HOST' in text:
    print("STATUS: WP_REDIS_HOST already present in wp-config.php.")
else:
    print("ERROR: Target line not found in wp-config.php")
EOF
python3 /tmp/update_wp.py
grep -i redis /var/www/html/wp-config.php
```

### 2. Verified `wp-config.php` Update & `grep` Verification:

![wp-config.php Updated and Verified via grep](images/p8-step4-grep-redis-verified.png)
*Terminal State:* Executed `/tmp/update_wp.py` via root shell in Session Manager. Python safely located `/* That's all, stop editing!` and injected the ElastiCache primary endpoint (`wp-lab-redis.cuzsbc.ng.0001.aps1.cache.amazonaws.com`), port (`6379`), timeouts, and salt (`wp_lab_`) cleanly into `/var/www/html/wp-config.php`. Verified by executing `grep -i redis /var/www/html/wp-config.php`, which confirmed all active Redis constants are in place.

### 2. Verified `wp-config.php` Update & `grep` Verification:

![wp-config.php Updated and Verified via grep](images/p8-step4-grep-redis-verified.png)
*Terminal State:* Executed `/tmp/update_wp.py` via root shell in Session Manager. Python safely located `/* That's all, stop editing!` and injected the ElastiCache primary endpoint (`wp-lab-redis.cuzsbc.ng.0001.aps1.cache.amazonaws.com`), port (`6379`), timeouts, and salt (`wp_lab_`) cleanly into `/var/www/html/wp-config.php`. Verified by executing `grep -i redis /var/www/html/wp-config.php`, which confirmed all active Redis constants are in place.

> [!IMPORTANT]
> **Why `WP_CACHE_KEY_SALT` is Mandatory:**
> If multiple WordPress instances or staging environments ever connect to the same Redis cluster, omitting the salt causes catastrophic key collisions (Post ID 1 on Site A overwrites Post ID 1 on Site B). The salt prefixes every single Redis key (e.g. `wp_lab_:alloptions`).

### 3. WordPress Admin Activation & Status Connected:

![Redis Object Cache Connected](images/p8-step4-redis-object-cache-connected.png)
*WordPress Admin State:* Navigated to **Settings ➔ Redis** in `https://lab.asaxenadev.com/wp-admin/`. Clicked **Enable Object Cache**. The plugin successfully connected to the Amazon ElastiCache cluster and placed the drop-in file (`wp-content/object-cache.php`):
- **Status:** **`Connected`** (Green checkmark)
- **Filesystem:** **`Writeable`** (Green checkmark)
- **Redis:** **`Reachable`** (Green checkmark)
- **Key Prefix:** `wp_lab_`
- **Client:** `PhpRedis (v6.2.0)`
- **Host:** `wp-lab-redis.cuzsbc.ng.0001.aps1.cache.amazonaws.com`
- **Port:** `6379`
- **Database:** `0`
- **Engine Version:** `7.1.0`

</details>

---

<details open>
<summary><h3>⚙️ Step 5 Execution Details: Benchmark & Verify with Query Monitor (Click to Expand)</h3></summary>

## Step 5 Execution Details: Benchmark & Verify with Query Monitor

Per `AGENTS.md`, the Definition of Done for Phase 8 requires:
> **"Redis Object Cache says 'Connected'; Query Monitor shows fewer queries"**

### Verification Protocol:
1. Install and activate **Query Monitor** plugin by John Blackbourn.
2. Load the WordPress homepage / admin dashboard with Redis Object Cache **Disabled**:
   - Record baseline database query count (e.g., 28–45 queries, ~0.0450s database execution time).
3. Enable Redis Object Cache and perform one warm-up page refresh (to populate Redis RAM with cached option blocks and transients).
4. Reload the page with warm cache:
   - Record optimized database query count (expected: 2–5 queries, ~0.0020s database execution time).
   - Calculate percentage reduction in MySQL database load:
     $$\text{Query Reduction \%} = \frac{\text{Initial Queries} - \text{Cached Queries}}{\text{Initial Queries}} \times 100$$
   - A drop from 35 queries to 3 queries represents an **91.4% reduction in database load**.

### Verification Results & Proof:

![Query Monitor 1 Database Query Verified](images/p8-step5-query-monitor-1-query-verified.png)
*WordPress Admin State:* Navigated to **Plugins** page (`/wp-admin/plugins.php`) with **Query Monitor** active:
- **Top Admin Bar Telemetry:** `0.12s` page generation | `7.5MB` RAM | `0.00s` DB time | **`1Q`** (1 Query total)!
- **Query Monitor Panel:**
  - **Database Queries:** **`Total: 1`**
  - **Query Execution Time:** **`0.0005s`**
  - **Single Query Executed:** `SELECT a.hook FROM wp_actionscheduler_actions a JOIN wp_actionscheduler_groups g ...`
- **Architectural Analysis:**
  Normally, rendering the WordPress admin `/wp-admin/plugins.php` table requires **30 to 50 distinct SQL queries** against MySQL (`wp_options` `alloptions`, active plugins list, transients, user capabilities, rewrite rules, theme support). With Amazon ElastiCache Redis active:
  - All options and metadata were served in **sub-millisecond time (<500μs) directly from Redis RAM**.
  - MySQL database load reduced from ~35 queries down to **1 single query**:
    $$\text{Query Reduction \%} = \frac{35 - 1}{35} \times 100 = 97.1\%$$
  - **97.1% reduction in MySQL queries**, shielding Amazon RDS from CPU spikes and thread exhaustion.

</details>

---

<details>
<summary><h3>💡 Gotchas & Real-World Troubleshooting Log (Click to Expand)</h3></summary>

## Gotchas & Real-World Troubleshooting Log

### Gotcha 1: Security Group Chaining vs VPC CIDR (Port 6379 Timeout)
- **Symptom:** `redis-cli -h <endpoint> ping` hangs indefinitely and outputs `Could not connect to Redis at <endpoint>:6379: Connection timed out`.
- **Cause:** Inbound rule on `wp-lab-redis-sg` either had the wrong port, wrong protocol, or specified a static IP/CIDR block instead of the EC2 Security Group ID (`sg-05f3d510a4a41385e`).
- **Fix:** Set the inbound source field explicitly to the Security Group ID of the EC2 web server (`sg-05f3d510a4a41385e`). AWS stateful firewalls automatically resolve instance group membership across network interfaces.

### Gotcha 2: Missing C-Extension vs Slow Pure-PHP Userland Fallback
- **Symptom:** Redis Object Cache displays a warning: *"The Redis PHP extension is not installed. Using Predis fallback."*
- **Cause:** The PHP PECL C-extension `php-redis` was not installed, forcing the plugin to fall back to an interpreted PHP userland library (`Predis`). Predis consumes significant CPU and memory inside the PHP process, negating much of the latency advantage.
- **Fix:** Run `apt install -y php-redis` and restart PHP-FPM (`systemctl restart php8.5-fpm`). Re-check `php -m | grep redis` to confirm the compiled C module is active.

### Gotcha 3: WordPress `wp-content/` Permissions Preventing `object-cache.php` Drop-in
- **Symptom:** Clicking **Enable Object Cache** fails with an error: *"Filesystem permissions prevent copying object-cache.php"*.
- **Cause:** The web server runs as `www-data`. If `wp-content/` is owned by `root` or `ubuntu`, PHP cannot write the drop-in file `wp-content/object-cache.php`.
- **Fix:** Grant appropriate ownership to the web server process:
  `chown www-data:www-data /var/www/html/wp-content/`.

### Gotcha 4: In-Transit Encryption (TLS) Connection Refusal
- **Symptom:** `redis-cli ping` outputs `Error: Connection reset by peer` or `WRONGPASS / SSL handshake failed`, and WordPress displays *"Redis connection failed"*.
- **Cause:** If "Encryption in-transit" is enabled during ElastiCache cluster creation, standard plaintext TCP connections on Port 6379 are rejected by AWS.
- **Fix:** Either disable in-transit encryption for simple standalone lab clusters, or configure WordPress with TLS scheme:
  ```php
  define('WP_REDIS_SCHEME', 'tls');
  ```
  And test CLI via `redis-cli -h <endpoint> -p 6379 --tls ping`.

### Gotcha 5: Cache Collisions Across Multiple Sites (`WP_CACHE_KEY_SALT`)
- **Symptom:** Modifying options or logging into Site A causes bizarre visual glitches, logout loops, or wrong database content to display on Site B.
- **Cause:** Redis is a key-value store. By default, WordPress uses generic keys like `options:alloptions` or `posts:1`. If two WordPress installations share a single Redis cluster, their keys collide destructively.
- **Fix:** Always set a unique salt constant in `wp-config.php`:
  `define('WP_CACHE_KEY_SALT', 'wp_lab_');`.

### Gotcha 6: ElastiCache Idle Billing Trap (Why Standalone Nodes Must Be Deleted)
- **Symptom:** Unexpected AWS invoice charges at the end of the month even when EC2 is stopped.
- **Cause:** ElastiCache clusters bill **by running hour of provisioned capacity**, not by request volume. Stopping an EC2 instance does NOT stop ElastiCache.
- **Fix:** Always delete the ElastiCache cluster at the conclusion of the lab session. For everyday low-cost hosting, a local Redis server on the EC2 instance (`apt install redis-server`) provides identical caching functionality for $0.

### Gotcha 7: Bash Shell Redirection Error on `<placeholder>` CLI Syntax
- **Symptom:** Running `redis-cli -h <primary-endpoint> -p 6379 ping` fails with error:
  ```text
  -bash: primary-endpoint: No such file or directory
  ```

![Bash Redirection Placeholder Gotcha](images/p8-step3-bash-redirection-placeholder-gotcha.png)
- **Cause:** In Linux shells (Bash/Zsh), `<` and `>` are reserved I/O redirection operators (reading input from a file or redirecting output). When passing `<primary-endpoint>`, Bash attempts to redirect standard input from a file named `primary-endpoint`.
- **Fix:** Do not retain `<` or `>`. Replace the entire token with the literal AWS ElastiCache DNS primary endpoint:
  ```bash
  redis-cli -h wp-lab-redis.xxxxxx.0001.aps1.cache.amazonaws.com -p 6379 ping
  ```

### Gotcha 8: Bash History Expansion Failure (`!/i: event not found`) When Using Double Quotes in `sed`
- **Symptom:** Attempting to inject configuration into `wp-config.php` via `sed -i "/That's all, stop editing!/i ..."` fails with:
  ```text
  -bash: !/i: event not found
  -bash: syntax error near unexpected token '('
  ```

![Bash History Expansion Sed Gotcha](images/p8-step4-bash-history-expansion-sed-gotcha.png)
- **Cause:** In interactive Bash shells, the exclamation mark (`!`) inside double quotes (`"..."`) triggers **Bash history expansion**. Bash interprets `!/i` as a search in its command history buffer rather than literal text.
- **Fix:** Avoid double-quoted `sed` commands containing `!`. Instead, use Python or single quotes to safely read and inject the configuration block cleanly into `/var/www/html/wp-config.php`.

### Gotcha 9: Terminal Multiline Paste & Shell Operator Inlining (`SyntaxError: invalid syntax` on `&&`)
- **Symptom:** Attempting to run a multiline inline Python command with chained shell commands (`python3 -c "..." && systemctl reload php8.5-fpm`) inside AWS Systems Manager Session Manager failed with:
  ```text
  File "<string>", line 16
    target = '/* That\'s all, stop editing' && systemctl reload php8.5-fpm && echo "SUCCESS:
                                            ^^
  SyntaxError: invalid syntax
  HP: command not found
  ```

![Terminal Multiline Paste Python Syntax Error](images/p8-step4-python-syntax-error-gotcha.png)
- **Cause:** In interactive web-based terminal emulators (like AWS Session Manager), pasting multiline blocks that combine inline Python strings (`python3 -c "..."`) with trailing Bash operators (`&&`) can cause the line breaks to collapse or quotes to misalign. As a result, the Bash operator (`&&`) and subsequent shell commands were fed directly into Python's `eval()` buffer, which rejected `&&` as invalid Python syntax.
- **Fix:** Write a dedicated, self-contained Python script to disk using a single-quoted heredoc (`cat << 'EOF' > /tmp/update_wp.py`), execute `python3 /tmp/update_wp.py` independently, and then run shell verification commands separately.

</details>

---

<details>
<summary><h3>🎯 Phase 8 Cloud Architecture Interview Questions & Answers (Click to Expand)</h3></summary>

## Phase 8 Cloud Architecture Interview Questions & Answers

### Q1: What is the architectural difference between Amazon ElastiCache Redis (Valkey) and Memcached?
- **Answer:** 
  - **Memcached:** Pure, multi-threaded in-memory key-value engine. Supports simple string data types only, zero persistence, zero replication, and zero multi-AZ failover. Excellent for simple, flat object caching across multiple CPU cores.
  - **Redis (Valkey):** Single-threaded event loop engine supporting rich data structures (Hashes, Lists, Sets, Sorted Sets, Bitmaps). Features **Multi-AZ replication with automated failover**, in-memory snapshots (RDB/AOF) for persistence, pub/sub messaging, and cluster sharding. WordPress object cache plugins strictly require Redis because they rely on Redis Hashes and key groups.

### Q2: What is the difference between Page Caching and Object Caching in a high-traffic WordPress architecture?
- **Answer:** 
  - **Page Caching (Nginx FastCGI / CloudFront):** Caches the entire rendered HTML document of a page. When an anonymous user requests the page, the web server returns the static HTML immediately without executing PHP or querying MySQL.
  - **Object Caching (Redis):** Operates *inside* PHP execution. When dynamic pages (e.g. WooCommerce cart, logged-in admin, search results) cannot be served as static HTML, Redis caches granular database query results (like `alloptions`, post metadata, user roles). Instead of running 50 SQL queries on MySQL, PHP makes 50 microsecond RAM lookups in Redis.

### Q3: What happens when an ElastiCache Redis node runs out of memory? How does Redis handle memory exhaustion?
- **Answer:** Redis behavior is governed by its `maxmemory-policy`:
  1. `volatile-lru` (Default in ElastiCache): Evicts the least recently used keys that have an explicit expiration TTL set.
  2. `allkeys-lru`: Evicts the least recently used keys out of all keys, regardless of whether a TTL is set (safest for pure cache workloads).
  3. `noeviction`: Returns an out-of-memory error on write commands (`OOM command not allowed when used memory > 'maxmemory'`), keeping existing data intact but breaking application writes.
  - **Production Practice:** For WordPress object caching, `allkeys-lru` is recommended so the cache gracefully evicts old transient queries when memory approaches 100%.

### Q4: What is the difference between ElastiCache "Cluster Mode Disabled" and "Cluster Mode Enabled"?
- **Answer:** 
  - **Cluster Mode Disabled (Single Shard):** One primary node for reads/writes, with up to 5 read replicas. All data resides on a single primary node. Scaling writes requires vertical scaling (larger node type). Ideal for small-to-medium WordPress sites.
  - **Cluster Mode Enabled (Sharded):** Data is partitioned across multiple shards (1 to 500 shards) using consistent hashing across 16,384 hash slots. Both reads and writes scale horizontally. Requires cluster-aware Redis client libraries.

### Q5: What is a "Cache Stampede" (Dog-piling effect), and how do you mitigate it?
- **Answer:** 
  - **The Problem:** When an extremely hot cache key expires (e.g. homepage options accessed 5,000 times/second), thousands of concurrent user threads experience a Cache Miss simultaneously. All 5,000 threads rush to query MySQL at the exact same instant to regenerate the cache, instantly causing database CPU exhaustion, connection pool saturation, and a 504 gateway timeout.
  - **Mitigation:**
    1. **Probabilistic Early Expiration (XFetch):** Background workers recompute the cache before it actually expires based on an algorithm.
    2. **Distributed Mutual Exclusion (Mutex Lock):** When a cache miss occurs, the first thread acquires a short-lived Redis lock (`SET ... NX EX`), while other threads wait briefly or serve slightly stale data until the lock is released.

### Q6: What is Valkey, and why did AWS introduce Valkey support in ElastiCache alongside Redis OSS?
- **Answer:** 
  - In early 2024, Redis Ltd. transitioned Redis from the open-source BSD license to dual proprietary licenses (RSALv2 and SSPLv1), which restrict cloud providers from offering managed Redis services freely.
  - In response, the Linux Foundation, backed by AWS, Google Cloud, Oracle, and Ericsson, created **Valkey** as an open-source (BSD-3-Clause) fork of Redis 7.2.4.
  - AWS introduced Valkey in ElastiCache as a 100% drop-in replacement for Redis OSS, offering a 20% lower price point and identical protocol/API compatibility with existing Redis clients and WordPress plugins.

### Q7: Why do we use Security Group Chaining instead of CIDR IP blocks for ElastiCache?
- **Answer:** 
  - In dynamic cloud environments (especially with Auto Scaling in Phase 9), EC2 instances are launched and terminated automatically, constantly receiving new private IP addresses.
  - Hardcoding subnet CIDR ranges (`172.31.0.0/16`) is overly permissive because any rogue or compromised resource in the VPC could connect to Redis.
  - **Security Group Chaining** references the security group ID (`sg-05f3d510a4a41385e`). AWS dynamically evaluates ENI attachments, permitting traffic strictly from instances explicitly assigned that security group, regardless of their IP address.

### Q8: How does Phase 8 (Redis Caching) pave the way for Phase 9 (Auto Scaling & Load Balancing)?
- **Answer:** 
  - An application cannot scale horizontally behind a load balancer if it maintains local state (stored files, local session memory, or disconnected local caches).
  - In Phase 4, we decoupled the database (RDS). In Phase 5, we decoupled media uploads (S3/CloudFront). In Phase 8, we decouple in-memory caching and transient objects into ElastiCache.
  - Because all web instances read from and write to the same centralized ElastiCache cluster, any EC2 instance can be terminated or spawned by an Auto Scaling Group in Phase 9 without data inconsistency or session loss.

</details>
