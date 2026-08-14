# US211 API Agent Guidelines

## API Architecture
- US211 API provides RESTful endpoints for AI agent management and coordination
- The API follows REST principles with JSON request/response bodies
- All endpoints are versioned using URL path versioning (/api/v1/)

## Endpoint Design Principles
- All endpoints must return appropriate HTTP status codes
- Request bodies must be validated against JSON schemas
- Responses must include timestamps and request IDs for tracing
- Error responses must follow RFC 7807 problem details format

## Authentication & Authorization
- API keys are required for all endpoints (except health checks)
- Implement rate limiting to prevent abuse (100 requests/minute/default)
- Support OAuth 2.0 for third-party integrations
- All authentication tokens must be stored securely and rotated regularly

## Data Handling Standards
- All data must be encrypted at rest using AES-256-GCM
- Data in transit must use TLS 1.3 or higher
- Personal data must be pseudonymized where possible
- Implement data retention policies with automatic deletion

## Performance Requirements
- API must respond to health checks within 50ms
- 95% of requests must complete within 200ms under normal load
- Implement caching strategies for frequently accessed data
- Database queries must be optimized and indexed appropriately

## Security Measures
- Input validation to prevent injection attacks (SQL, NoSQL, command)
- Implement CORS policies with strict origin checking
- Security headers must be present on all responses
- Regular security scanning and penetration testing required