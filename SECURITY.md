# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |

## Security Best Practices

### Environment Configuration

**Critical: Never commit `.env` files to version control**

1. Copy `.env.example` to `.env`
2. Configure all sensitive values in `.env`
3. Ensure `.env` is in `.gitignore`

### GitHub Webhook Security

The GitHub webhook endpoint (`/payload`) requires proper configuration:

1. Set a strong `GITHUB_SECRET` in your environment:
   ```bash
   # Generate a secure random secret
   openssl rand -hex 32
   ```

2. Configure the same secret in GitHub repository settings:
   - Go to Settings → Webhooks → Add webhook
   - Set the secret to match your `GITHUB_SECRET`
   - Use HTTPS only in production

### CORS Configuration

**Production Settings:**

Set `ALLOWED_ORIGINS` to specific domains only:
```bash
ALLOWED_ORIGINS=https://train.sportsprime.live,https://app.example.com
```

**Never use `ALLOWED_ORIGINS=*` in production** - this allows any website to make requests with credentials.

### Redis Security

1. **Use authentication:**
   ```bash
   # In redis.conf
   requirepass your_strong_password
   ```

2. **Bind to localhost only** (if Redis is on same server):
   ```bash
   # In redis.conf
   bind 127.0.0.1
   ```

3. **Use Redis ACLs** for fine-grained access control (Redis 6+)

### Input Validation

All user inputs are validated:
- Train IDs: Alphanumeric, dash, underscore only (max 20 chars)
- User IDs: Alphanumeric, dash, underscore only (max 50 chars)
- Position values: 0-150 range
- Timestamps: Valid Unix timestamps

### Rate Limiting

**Recommended:** Use a reverse proxy (nginx/Caddy) with rate limiting:

```nginx
# nginx example
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;

location / {
    limit_req zone=api_limit burst=20 nodelay;
    proxy_pass http://localhost:8000;
}
```

### SSL/TLS

**Always use HTTPS in production:**
- Use Let's Encrypt for free SSL certificates
- Configure your reverse proxy to handle TLS termination
- Redirect HTTP to HTTPS

## Reporting a Vulnerability

**Please DO NOT open a public issue for security vulnerabilities.**

Instead:
1. Email security concerns to the repository maintainers
2. Include detailed information:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if known)

Expected response time:
- Initial acknowledgment: 48 hours
- Status update: 7 days
- Fix deployment: 14-30 days (depending on severity)

## Known Security Considerations

### Bot User Trust Model

- Users with ID starting with "bot" are trusted and can set position bounds
- Regular users are validated against these bounds
- Recommendation: Keep bot credentials secure and rotate regularly

### Position Data Validity

- Position data expires after 10 hours
- Older data is automatically rejected
- Prevents stale data from affecting tracking

### Log Files

Issue reports are logged to `issue_reports.log`:
- Ensure log files are not publicly accessible
- Rotate logs regularly to prevent disk space issues
- Consider storing sensitive logs separately

## Security Checklist for Deployment

- [ ] Set strong `GITHUB_SECRET`
- [ ] Configure specific `ALLOWED_ORIGINS` (no wildcards)
- [ ] Enable Redis authentication
- [ ] Use HTTPS/TLS with valid certificates
- [ ] Set up rate limiting at reverse proxy
- [ ] Configure log rotation
- [ ] Restrict file permissions (600 for .env, 640 for logs)
- [ ] Set up monitoring and alerting
- [ ] Regular security updates for dependencies
- [ ] Backup Redis data regularly

## Dependency Security

Run security audits regularly:

```bash
# Check for vulnerabilities in Python packages
pip install safety
safety check

# Update dependencies (test in staging first)
pip install --upgrade -r requirements.txt
```

## Logging and Monitoring

- All security events are logged at WARNING level
- Failed authentication attempts are logged
- Monitor logs for suspicious patterns
- Set up alerts for repeated failed attempts

## Updates and Patches

Subscribe to security advisories for:
- FastAPI: https://github.com/tiangolo/fastapi/security
- Redis: https://redis.io/topics/security
- Python: https://www.python.org/news/security/
