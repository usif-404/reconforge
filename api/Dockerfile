FROM python:3.12-slim

WORKDIR /app

# Recon tool dependencies. Go-based ProjectDiscovery tools are installed
# separately below since apt doesn't carry them.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl git wget whois dnsutils jq build-essential \
    && rm -rf /var/lib/apt/lists/*

# Go toolchain, for building subfinder/httpx/katana/dnsx/naabu/puredns/etc.
RUN curl -fsSL https://go.dev/dl/go1.23.4.linux-amd64.tar.gz -o /tmp/go.tar.gz \
    && tar -C /usr/local -xzf /tmp/go.tar.gz && rm /tmp/go.tar.gz
ENV PATH="/usr/local/go/bin:/root/go/bin:${PATH}"

# ProjectDiscovery + adjacent recon tools referenced throughout the pipeline
# stages. Pin versions in production; @latest here for scaffold simplicity.
RUN go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest && \
    go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest && \
    go install -v github.com/projectdiscovery/dnsx/cmd/dnsx@latest && \
    go install -v github.com/projectdiscovery/naabu/v2/cmd/naabu@latest && \
    go install -v github.com/projectdiscovery/katana/cmd/katana@latest && \
    go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest && \
    go install -v github.com/tomnomnom/waybackurls@latest && \
    go install -v github.com/lc/gau/v2/cmd/gau@latest && \
    go install -v github.com/hakluke/hakrawler@latest && \
    go install -v github.com/hakluke/hakrevdns@latest && \
    go install -v github.com/tomnomnom/assetfinder@latest && \
    go install -v github.com/ffuf/ffuf/v2@latest && \
    go install -v github.com/d3mondev/puredns/v2@latest && \
    go install -v github.com/lc/subjs@latest

# Python recon tools
RUN pip install --no-cache-dir arjun trufflehog3

COPY requirements.txt .
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

COPY app ./app

ENV PYTHONPATH=/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
