# 🚀 Deployment & Infrastructure


Lumina includes a fully containerized production infrastructure utilizing Docker, Gunicorn, and Nginx.

**Infrastructure Components:**
- **Dockerfile**: Builds a lightweight Python 3.11 image and installs all dependencies.
- **Production Server**: Uses **Gunicorn** with asynchronous **Uvicorn** workers to handle high-concurrency requests and robust application scaling.
- **Reverse Proxy (Nginx)**: The included `nginx/nginx.conf` securely routes traffic to the backend on port 80, explicitly handling WebSocket upgrades required by Gradio.
- **docker-compose.yml**: Orchestrates the Nginx reverse proxy and the Lumina Python backend, automatically mounting persistent volumes for image and audio caches.
- **Environment Separation**:
  - `.env.dev`: Local development environment variables template.
  - `.env.prod`: Production environment variables explicitly loaded by Docker Compose.

**Deployment Steps:**
1. Populate `.env.prod` with your real API keys.
2. Run the following command to build the image and spin up the backend and reverse proxy in the background:

```bash
docker-compose up -d --build
```
3. Access the application on `http://<your-server-ip>/`.

---
Illustrates the production-ready Docker infrastructure, showcasing how traffic hits the reverse proxy before being distributed to Uvicorn workers.

```mermaid
flowchart TD
    subgraph Host[Host OS / Server]
        subgraph Docker[Docker Network]
            Nginx["Nginx Reverse Proxy<br>(Port 80/443)"]
            App["Lumina FastAPI App<br>(Gunicorn / Uvicorn Workers)"]
            Nginx <-->|WebSockets & HTTP| App
        end
        Volumes[("Docker Volumes<br>Caches & History")]
        App <--> Volumes
    end
    
    Internet((🌍 Internet))
    Internet <--> Nginx
    
    subgraph CloudAPIs[External Cloud APIs]
        Groq(Groq Llama 3)
        Google(Google Gemma/Imagen)
        Together(Together FLUX)
        TTS(Microsoft Edge TTS)
    end
    
    App <--> CloudAPIs
```

## 🔄 CI/CD Deployment Pipeline

Lumina AI's release lifecycle is automated through a unified Continuous Integration and Continuous Delivery (CI/CD) pipeline. This guarantees that all code merges undergo rigorous quality checks, dependency vulnerability scans, and regression testing before being hot-deployed to production.

The following flowchart maps the automated deployment journey from developer push to production verification:

```mermaid
flowchart TD
    Developer([💻 Developer Push]) --> Trigger[GitHub Actions Runner]
    
    subgraph CI [1. Continuous Integration Stage]
        Lint["Lint Checks<br>(Flake8 / Black)"]
        Unit["Unit Tests<br>(pytest tests/unit)"]
        Int["Integration Tests<br>(pytest tests/integration)"]
        Security["Security Auditing<br>(Safety / Bandit)"]
        
        Lint --> Unit
        Unit --> Int
        Int --> Security
    end
    
    Trigger --> CI
    
    subgraph CD [2. Continuous Delivery Stage]
        DockerBuild["Build Docker Image<br>(Python 3.11 Base)"]
        DockerPush["Push Image to Registry<br>(GitHub Packages / GCR)"]
        
        DockerBuild --> DockerPush
    end
    
    CI -- Pass --> CD
    
    subgraph Deploy [3. Deployment Stage]
        Pull["Pull New Image"]
        Backup["Backup Chats Cache"]
        Compose["Docker Compose Up<br>(--build -d)"]
        NginxReload["Nginx Hot-Reload"]
        
        Pull --> Backup
        Backup --> Compose
        Compose --> NginxReload
    end
    
    DockerPush -- Webhook/CD Tool --> Deploy
    
    subgraph SRE_Verify [4. Post-Deployment Verification]
        Health["Health Check<br>(/metrics /healthz)"]
    end
    
    NginxReload --> SRE_Verify
```

