FROM python:3.13.14-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir -e .
ENV PORT=8000
EXPOSE 8000
CMD ["python", "-m", "src.main"]
