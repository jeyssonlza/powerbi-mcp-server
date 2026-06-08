# ===========================================================================
# Dockerfile - Power BI MCP Server
# ===========================================================================
# Base image: Python 3.10 slim para producción
FROM python:3.10-slim

# Metadata
LABEL maintainer="Jeysson Zerpa <jeyssonzerpa@gmail.com>"
LABEL description="Enterprise-grade MCP Server for Power BI (PBIP/PBIX)"

# Set working directory
WORKDIR /app

# Install system dependencies (minimales para security)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml requirements.txt ./
COPY src/ ./src/

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e .

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import powerbi_mcp; print('OK')" || exit 1

# Expose MCP server port (stdio over HTTP for advanced deployments)
EXPOSE 8000

# Run the MCP server
CMD ["python", "-m", "powerbi_mcp"]
