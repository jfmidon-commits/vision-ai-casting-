# Vision AI Casting - API Documentation

## Base URL
- Development: `http://localhost:8000`
- Staging: `https://api-staging.visionaicasting.com`
- Production: `https://api.visionaicasting.com`

## Authentication
All endpoints (except `/health` and auth endpoints) require a Bearer token:
```
Authorization: Bearer <token>
```

## Rate Limiting
| Plan | Requests/minute |
|------|----------------|
| Starter | 100 |
| Professional | 1,000 |
| Enterprise | 10,000 |

## Endpoints

### Health
```
GET /health
```
Returns service health status.

### Authentication
```
POST /api/v1/auth/register
POST /api/v1/auth/login
POST /api/v1/auth/refresh
GET  /api/v1/auth/me
POST /api/v1/auth/invites
```

### Profiles
```
GET    /api/v1/profiles
POST   /api/v1/profiles
GET    /api/v1/profiles/{id}
PUT    /api/v1/profiles/{id}
DELETE /api/v1/profiles/{id}
```

### Photoshoots
```
GET    /api/v1/photoshoots
POST   /api/v1/photoshoots
GET    /api/v1/photoshoots/{id}
```

### Photos
```
GET    /api/v1/photos/{id}
PUT    /api/v1/photos/{id}
DELETE /api/v1/photos/{id}
```

### Analyses
```
GET /api/v1/analyses
GET /api/v1/analyses/{id}
GET /api/v1/analyses/{id}/facial
GET /api/v1/analyses/{id}/visagism
GET /api/v1/analyses/{id}/casting
```

### AI Analysis
```
POST /api/v1/ai/analyze
POST /api/v1/ai/analyze/facial
POST /api/v1/ai/analyze/visagism
POST /api/v1/ai/analyze/casting
```

### Reports
```
GET  /api/v1/reports
POST /api/v1/reports
GET  /api/v1/reports/{id}
POST /api/v1/reports/{id}/generate-pdf
```

### WebSocket
```
ws://localhost:8000/ws/progress/{analysis_id}
ws://localhost:8000/ws/tenant/{tenant_id}
```

## WebSocket Events

### Client -> Server
```json
{"type": "subscribe", "channel": "analysis:123"}
```

### Server -> Client
```json
{
  "type": "analysis_progress",
  "analysis_id": "123",
  "progress": {
    "stage": "facial_analysis",
    "percentage": 45,
    "status": "processing"
  },
  "timestamp": 1699123456
}
```

```json
{
  "type": "analysis_complete",
  "analysis_id": "123",
  "data": {
    "confidence_score": 0.85,
    "results": {...}
  },
  "timestamp": 1699123500
}
```

## Error Codes
| Code | Description |
|------|-------------|
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 429 | Rate Limit Exceeded |
| 500 | Internal Server Error |
| 503 | Service Unavailable |
