# ── Stage 1: Base image ───────────────────────────────────────────────────────
FROM python:3.11-slim

# Set working directory inside container
WORKDIR /app

# Prevents Python from writing .pyc files (keeps image clean)
ENV PYTHONDONTWRITEBYTECODE=1

# Prevents Python from buffering stdout/stderr
# Critical for seeing logs in real time on Railway/Render
ENV PYTHONUNBUFFERED=1

# ── Stage 2: Install dependencies ─────────────────────────────────────────────
# Copy only requirements first — Docker layer caching means
# this layer is only rebuilt when requirements.txt changes,
# not on every code change. Big time saver.
COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ── Stage 3: Copy application code ────────────────────────────────────────────
COPY . .

# ── Stage 4: Create directory for SQLite database ─────────────────────────────
# In production we persist this via a volume mount
RUN mkdir -p /app/data

# ── Stage 5: Expose port and run ──────────────────────────────────────────────
EXPOSE 8000

# Use 2 workers for production
# --no-access-log keeps logs clean (Railway/Render add their own)
CMD ["uvicorn", "app.main:app", \
    "--host", "0.0.0.0", \
    "--port", "8000", \
    "--workers", "2", \
    "--no-access-log"]