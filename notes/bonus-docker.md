# Bonus Phase — Docker Containerization for Stateless WordPress (AWS ECR & ECS Fargate)

> **Definition of Done:** Stateless WordPress packaged into a lean, immutable Docker container image, pushed to Amazon Elastic Container Registry (ECR), and running serverlessly on AWS ECS (Fargate) behind an Application Load Balancer.

---

<details>
<summary><h3>🧠 Conceptual Foundations, Architecture & Trade-offs (Click to Expand)</h3></summary>

## What it does

Replaces traditional VM-based EC2 server configuration with **immutable Docker containerization**:
1. Packages Nginx, PHP 8.3-FPM, and WordPress core into a single, standardized, versioned Docker image.
2. Pushes the container image to **Amazon ECR (Elastic Container Registry)**.
3. Deploys the container to **AWS ECS (Elastic Container Service)** using the **AWS Fargate** serverless launch type (zero EC2 instances to patch, manage, or maintain).
4. Connects seamlessly to our decoupled cloud persistence layer: Amazon RDS (MySQL), Amazon S3 (Media), and Amazon ElastiCache (Redis).

---

## Why choose it (Over EC2 Virtual Machines)

- **The Prerequisite: Why Docker Comes AFTER Phases 4, 5, and 8:**
  - A container filesystem is **ephemeral** (anything written inside the container is permanently lost when the container stops or restarts).
  - In a naive WordPress Docker setup, developers struggle with mounting complex shared NFS/EFS volumes for `/wp-content/uploads/` and local MySQL databases.
  - Because we already decoupled the database to **RDS (Phase 4)**, media to **S3 (Phase 5)**, and cache to **Redis (Phase 8)**, our WordPress container is **100% stateless**. It can spin up or terminate in 5 seconds with zero data loss!
- **Zero OS / VM Patching (AWS Fargate):**
  - With EC2, you are responsible for Ubuntu kernel updates, security patches, SSH keys, and EBS volume sizing.
  - AWS Fargate is **serverless compute for containers**: AWS manages the underlying operating system and virtualization; you pay purely for the vCPU and memory allocated while the container runs.
- **Instant Deployment Speed & Consistency:**
  - Traditional EC2 Auto Scaling takes 3–5 minutes to boot a VM, run User Data scripts, and configure Nginx.
  - A container starts in seconds, guaranteeing that local dev, staging, and production environments are 100% identical ("Works on my machine" eliminated).

---

## Trade-offs

- **Container Image Size & Build Caching:**
  WordPress bundled with PHP-FPM and Nginx can easily exceed 500 MB if unoptimized, slowing down image pull times during auto-scaling events. **Mitigation:** Use multi-stage Docker builds or lean Alpine/Debian-slim base images.
- **Log Routing & Observability:**
  Containers do not have persistent local `/var/log/nginx/` files. All logs must be forwarded to `stdout`/`stderr` and shipped to **Amazon CloudWatch Logs** via the `awslogs` log driver.
- **Cold Start & Networking Overhead:**
  Provisioning new AWS Fargate tasks requires attaching an AWS Elastic Network Interface (ENI) to the container, which takes ~30–45 seconds.

---

## Architecture Diagram (Serverless WordPress on AWS ECS Fargate)

```text
                                [Global Web Visitors]
                                          │
                                          │ HTTPS (lab.asaxenadev.com)
                                          ▼
                       [Application Load Balancer (ALB)]
                                          │
                                          │ Target Group (Port 80 HTTP)
                                          ▼
              ┌───────────────────────────────────────────────────────┐
              │             AWS ECS Cluster (Fargate Serverless)      │
              │                                                       │
              │   ┌────────────────────────┐ ┌────────────────────┐   │
              │   │ Fargate Task 1         │ │ Fargate Task 2     │   │
              │   │ ┌────────────────────┐ │ │ ┌────────────────┐ │   │
              │   │ │ Stateless WordPress│ │ │ │Stateless WP    │ │   │
              │   │ │ (Nginx + PHP-FPM)  │ │ │ │(Nginx + PHP-FPM│ │   │
              │   │ └─────────┬──────────┘ │ │ └────────┬───────┘ │   │
              │   └───────────┼────────────┘ └──────────┼─────────┘   │
              └───────────────┼─────────────────────────┼─────────────┘
                              │                         │
               ┌──────────────┴─────────────────────────┴──────────────┐
               │                                                       │
               ▼                                                       ▼
  [Amazon RDS MySQL (Phase 4)]                           [Amazon S3 Media (Phase 5)]
  (Decoupled DB state)                                   (Decoupled Media uploads)
```

</details>

---

<details>
<summary><h3>🚀 Production Multi-Service Dockerfile (Nginx + PHP 8.3-FPM + Supervisord) (Click to Expand)</h3></summary>

## Production Multi-Service Dockerfile (Nginx + PHP 8.3-FPM + Supervisord)

Because WordPress requires both a web server (Nginx) and a FastCGI process manager (PHP-FPM), in production container architectures we orchestrate them cleanly using **Supervisord**:

```dockerfile
# syntax=docker/dockerfile:1
FROM php:8.3-fpm-alpine

# 1. Install production dependencies, Nginx, and Supervisor
RUN apk add --no-cache \
    nginx \
    supervisor \
    curl \
    libpng-dev \
    libwebp-dev \
    libjpeg-turbo-dev \
    freetype-dev \
    libzip-dev \
    $PHPIZE_DEPS \
    && docker-php-ext-configure gd --with-freetype --with-jpeg --with-webp \
    && docker-php-ext-install -j$(nproc) gd mysqli pdo_mysql opcache zip \
    && pecl install redis \
    && docker-php-ext-enable redis \
    && apk del $PHPIZE_DEPS

# 2. Configure Nginx and PHP-FPM
COPY docker/nginx.conf /etc/nginx/nginx.conf
COPY docker/supervisord.conf /etc/supervisord.conf
COPY docker/php.ini /usr/local/etc/php/conf.d/custom.ini

# 3. Set Working Directory and Copy Stateless WordPress Core
WORKDIR /var/www/html
COPY --chown=www-data:www-data wordpress/ /var/www/html/

# Decoupled Uploads: Ensure local uploads directory is empty and writable
RUN mkdir -p /var/www/html/wp-content/uploads && chown -R www-data:www-data /var/www/html/wp-content/uploads

# 4. Expose HTTP Port
EXPOSE 80

# 5. Start Supervisor to manage both Nginx and PHP-FPM daemons
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisord.conf"]
```

</details>

---

<details>
<summary><h3>🚀 Local Simulation via `docker-compose.yml` (Click to Expand)</h3></summary>

## Local Simulation via `docker-compose.yml`

Before pushing to AWS ECR, test the decoupled container stack locally:

```yaml
version: '3.8'

services:
  wordpress:
    build: .
    ports:
      - "8080:80"
    environment:
      DB_HOST: db:3306
      DB_NAME: wordpress
      DB_USER: wpuser
      DB_PASSWORD: localpassword123
      WP_REDIS_HOST: redis
    depends_on:
      - db
      - redis

  db:
    image: mysql:8.0
    environment:
      MYSQL_DATABASE: wordpress
      MYSQL_USER: wpuser
      MYSQL_PASSWORD: localpassword123
      MYSQL_ROOT_PASSWORD: rootsecret123
    volumes:
      - db_data:/var/lib/mysql

  redis:
    image: redis:alpine
    ports:
      - "6379:6379"

volumes:
  db_data:
```

</details>

---

<details>
<summary><h3>🚀 AWS ECR & ECS Fargate Deployment Playbook (Click to Expand)</h3></summary>

## AWS ECR & ECS Fargate Deployment Playbook

### 1. Build and Push Image to Amazon ECR
```bash
# 1. Authenticate Docker with Amazon ECR
aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin 538820337781.dkr.ecr.ap-south-1.amazonaws.com

# 2. Create ECR Private Repository
aws ecr create-repository --repository-name wp-lab-app --region ap-south-1

# 3. Build & Tag Docker Image
docker build -t wp-lab-app:v1.0 .
docker tag wp-lab-app:v1.0 538820337781.dkr.ecr.ap-south-1.amazonaws.com/wp-lab-app:v1.0

# 4. Push to ECR
docker push 538820337781.dkr.ecr.ap-south-1.amazonaws.com/wp-lab-app:v1.0
```

### 2. Configure ECS Task Definition & Fargate Service
1. **ECS Task Execution IAM Role (`ecsTaskExecutionRole`):**
   - Grants ECS permission to pull image from ECR and stream logs to CloudWatch.
   - Attach policy: `AmazonECSTaskExecutionRolePolicy`.
2. **Task Definition:**
   - Launch type: `FARGATE`.
   - CPU: `0.5 vCPU` (512 units), Memory: `1 GB`.
   - Container Image: `538820337781.dkr.ecr.ap-south-1.amazonaws.com/wp-lab-app:v1.0`.
   - Environment Variables injected dynamically from AWS SSM Parameter Store / Secrets Manager.
3. **ECS Service:**
   - Desired Tasks: 2 (Multi-AZ across `ap-south-1a` and `ap-south-1b`).
   - Load Balancer: Attach to Application Load Balancer target group.

</details>

---

<details>
<summary><h3>💡 Gotchas & Real-World Troubleshooting Log (Click to Expand)</h3></summary>

## Gotchas & Real-World Troubleshooting Log

### 💡 Gotcha 1: The Ephemeral Filesystem Trap (Why naive WordPress Docker fails)
- **Problem:** If a user uploads an image or installs a plugin via WordPress Admin inside a vanilla Docker container, the moment the container restarts or ECS auto-scales, all uploaded media disappears!
- **Solution:** True containerization requires our Phase 4 (RDS for DB), Phase 5 (S3 for media), and Phase 8 (Redis for cache). Plugins must be pre-baked into the Docker image, never installed on runtime containers.

### 💡 Gotcha 2: Forwarding Logs to stdout / stderr for CloudWatch
- **Problem:** Nginx and PHP-FPM default to writing logs to local files (`/var/log/nginx/access.log`), which are invisible in Amazon CloudWatch.
- **Solution:** Symlink logs to stdout/stderr in Dockerfile:
  ```dockerfile
  RUN ln -sf /dev/stdout /var/log/nginx/access.log && ln -sf /dev/stderr /var/log/nginx/error.log
  ```

</details>

---

<details>
<summary><h3>🎯 Docker & ECS Cloud Architecture Interview Questions & Answers (Click to Expand)</h3></summary>

## Docker & ECS Cloud Architecture Interview Questions & Answers

### Q1: Why is a stateless web tier mandatory before moving WordPress to Docker / ECS?
- **Answer:** Docker containers are designed to be ephemeral, immutable, and disposable. If an application stores state on its local filesystem (like uploads in `/wp-content/uploads/` or a local database in `/var/lib/mysql`), any container replacement, rolling deployment, or auto-scaling event destroys that state or causes data divergence. By offloading media to S3, database to RDS, and sessions to Redis, the container contains only executable code, allowing instant horizontal scaling.

### Q2: What is the difference between AWS ECS on EC2 vs AWS ECS on AWS Fargate?
- **Answer:**
  - **ECS on EC2:** You provision, manage, patch, and pay for the underlying EC2 instances running the Docker daemon. You have full OS access, but must manage cluster capacity and patching.
  - **ECS on Fargate:** Serverless container compute. You define CPU and Memory requirements at the task level, and AWS dynamically provisions the underlying compute environment. Zero OS patching, zero instance management, and you pay strictly per-second for CPU/memory allocated.

### Q3: How do you handle secrets (DB passwords) in an ECS Task Definition securely?
- **Answer:** Hardcoding credentials in Dockerfiles or plain text environment variables is an anti-pattern. AWS ECS natively integrates with **AWS Secrets Manager** and **AWS SSM Parameter Store** via the `secrets` attribute in the Task Definition:
  ```json
  "secrets": [
    {
      "name": "DB_PASSWORD",
      "valueFrom": "arn:aws:ssm:ap-south-1:538820337781:parameter/wp-lab/db_password"
    }
  ]
  ```
  The ECS Agent fetches the secret at container startup using the Task Execution Role and injects it as an in-memory environment variable without exposing it in the task definition JSON.

</details>
