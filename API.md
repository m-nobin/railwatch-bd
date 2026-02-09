# API Documentation

## Overview

Bangladesh Railway Train Tracking API provides real-time position updates for BR trains through crowdsourced location data.

**Base URL:** `https://train.sportsprime.live`

**API Version:** 1.0.0

## Authentication

Most endpoints are public and don't require authentication. The GitHub webhook endpoint (`/payload`) requires signature verification.

## Rate Limiting

- **Default:** 10 requests/second per IP
- **Burst:** 20 requests
- Implemented at reverse proxy level

## Response Format

All API responses are in JSON format:

```json
{
  "status": "success",
  "data": { ... }
}
```

Error responses:
```json
{
  "detail": "Error message"
}
```

## Endpoints

### Health & Info

#### GET /
Root endpoint with API information

**Response:**
```json
{
  "name": "Find My BR Train FastAPI Server",
  "version": "1.0.0",
  "framework": "FastAPI",
  "endpoints": { ... },
  "github": "https://github.com/jisangain/find-my-br-train"
}
```

#### GET /health
Server health check

**Response:**
```json
{
  "status": "healthy",
  "timestamp": 1704150000,
  "revision": 143,
  "redis_connected": true,
  "active_trains": 25,
  "trains_with_history": 89
}
```

**Status Values:**
- `healthy`: All systems operational
- `degraded`: Redis disconnected or other issues

---

### Data Endpoints

#### GET /initrevision
Get current data revision number

**Response:**
```json
{
  "revision": 143
}
```

**Usage:** Check if app data needs updating

#### GET /alltrains
Download complete train database

**Response:**
```json
{
  "sid_to_sloc": { "Dhaka": [23.7104, 90.4074], ... },
  "sid_to_sname": { "Dhaka": "Dhaka", ... },
  "train_names": { "101": "Suborno Express", ... },
  "offday": { "101": ["Fri"], ... },
  "tid_to_stations": {
    "101": [
      ["Dhaka", 1, "22:30"],
      ["Chittagong", 1, "05:30"]
    ]
  }
}
```

**Data Structure:**
- `sid_to_sloc`: Station ID to [latitude, longitude]
- `sid_to_sname`: Station ID to station name
- `train_names`: Train ID to train name
- `offday`: Train ID to list of off days
- `tid_to_stations`: Train ID to route
  - Each station: `[station_id, stop_type, time]`
  - Stop types: 1 (stops), 0 (passes), -1 (landmark)

---

### Position Endpoints

#### GET /current/{train_ids}
Get current positions for specified trains

**Parameters:**
- `train_ids` (path, required): Comma-separated train IDs
  - Example: `101,102,103`

**Response:**
```json
{
  "101": {
    "position": 12.5,
    "timestamp": 1704150000,
    "active_user": 5,
    "is_live": true,
    "unconfirmed": {
      "position": 12.5,
      "timestamp": 1704150000
    }
  },
  "102": null
}
```

**Fields:**
- `position`: Float (0 to N-1, where N is number of stations)
- `timestamp`: Unix timestamp (seconds)
- `active_user`: Number of users tracking this train
- `is_live`: True if data from last 10 minutes
- `unconfirmed`: Same position data (for backward compatibility)

**Data Age:**
- Live: < 10 minutes old
- Historical: 10 minutes to 10 hours old
- Null: No data or > 10 hours old

#### GET /bounds/{train_id}
Get position bounds for a train (set by bot users)

**Parameters:**
- `train_id` (path, required): Train ID

**Response:**
```json
{
  "train_id": "101",
  "bounds": {
    "lower": 10.0,
    "upper": 15.5,
    "bot_position": 12.0,
    "timestamp": 1704150000
  }
}
```

#### POST /sendupdate
Submit location update

**Request Body:**
```json
{
  "train_id": "101",
  "user_id": "user123",
  "position": 12.5,
  "time": 1704150000
}
```

**Fields:**
- `train_id` (required): Train ID (alphanumeric, dash, underscore, max 20 chars)
- `user_id` (optional): User ID (default: "unknown")
  - Prefix with "bot" for trusted bot users
- `position` (required): Position value (0-150)
- `time` (required): Unix timestamp in seconds or milliseconds

**Bot Users:**
- User IDs starting with "bot" are trusted
- Can set position bounds for validation
- Regular users validated against bounds

**Response:**
```json
{
  "status": "success",
  "message": "Position updated"
}
```

**Errors:**
- 400: Invalid input or position rejected
- 500: Server error

**Validation:**
- Position must be within bounds (0-150)
- Position can't exceed scheduled position + tolerance
- Position can't be behind bot-reported position

---

### Route Endpoints

#### GET /two-train-routes/{from_station}/{to_station}
Get two-train route options between stations

**Parameters:**
- `from_station` (path, required): Origin station ID
- `to_station` (path, required): Destination station ID

**Response:**
```json
{
  "from_station": "Dhaka",
  "to_station": "Khulna",
  "routes": [
    {
      "train1_id": "101",
      "train1_name": "Suborno Express",
      "train2_id": "205",
      "train2_name": "Sundarban Express",
      "interchange_station_id": "Rajshahi",
      "interchange_station_name": "Rajshahi"
    }
  ]
}
```

**Usage:** Find routes requiring train change

#### GET /two-train-routes-all
Get all precalculated two-train routes

**Response:** Large JSON with all possible two-train combinations

**Warning:** Response can be > 1MB, use with caution

#### POST /nearbyroute
Find alternative routes near user location

**Request Body:**
```json
{
  "from_station": "Dhaka",
  "to_station": "Chittagong",
  "user_lat": 23.8103,
  "user_lng": 90.4125,
  "max_distance_km": 10.0
}
```

**Response:**
```json
{
  "nearby_from_stations": [
    {
      "station_id": "Dhaka",
      "station_name": "Dhaka",
      "distance_km": 2.5,
      "trains_to_destination": ["101", "102"]
    }
  ]
}
```

---

### Report Endpoints

#### POST /fix
Report incorrect information

**Request Body:**
```json
{
  "issue_type": "wrong_position",
  "train_id": "101",
  "train_name": "Suborno Express",
  "user_id": "user123",
  "timestamp": "2024-01-01T10:30:00",
  "description": "Train position is incorrect",
  "blue_train_position": 12.5,
  "gray_train_position": 10.2,
  "is_using_gps": true,
  "latitude": 23.8103,
  "longitude": 90.4125
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Issue report received"
}
```

**All fields optional except issue_type**

#### GET /report
View all issue reports (HTML page)

**Response:** HTML page with all submitted reports

---

### Live Monitoring

#### GET /live
View all live trains (HTML page)

**Response:** HTML page showing:
- Live trains (active in last 10 minutes)
- Historical positions (up to 10 hours)
- Train positions and user counts

---

## WebSocket Support

Currently not supported. All updates via HTTP POST.

## Data Updates

### Automatic Updates (GitHub Webhook)

#### POST /payload
GitHub webhook for automatic deployment

**Headers:**
- `X-Hub-Signature-256`: HMAC signature
- `User-Agent`: Must start with `GitHub-Hookshot/`

**Authentication:** HMAC-SHA256 with configured secret

**Response:**
```json
"Pulled and restarted"
```

**Security:** Verifies GitHub signature before accepting

---

## Error Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad Request (invalid input) |
| 403 | Forbidden (authentication failed) |
| 404 | Not Found |
| 500 | Internal Server Error |

## Common Errors

### Position Rejected
```json
{
  "detail": "Position rejected: Position 15.5 exceeds scheduled position 12.0"
}
```

**Causes:**
- Position ahead of schedule
- Position behind bot bounds
- Invalid position value

**Solutions:**
- Verify position is reasonable
- Check train schedule
- Ensure timestamp is current

### Invalid Input
```json
{
  "detail": "Invalid train_id format"
}
```

**Causes:**
- Invalid characters in train_id/user_id
- Missing required fields
- Position out of range (0-150)

### Redis Unavailable
```json
{
  "status": "degraded",
  "redis_connected": false
}
```

**Cause:** Redis connection failed

**Action:** Position updates will fail, contact admin

---

## Best Practices

### For Mobile Apps

1. **Check revision on startup:**
   ```
   GET /initrevision
   ```
   Compare with cached revision, download new data if changed

2. **Batch position requests:**
   ```
   GET /current/101,102,103
   ```
   Request multiple trains at once instead of separate calls

3. **Update position periodically:**
   - Active tracking: Every 30 seconds
   - Background: Every 2-3 minutes
   - Include accurate timestamp

4. **Handle errors gracefully:**
   - Retry failed requests with exponential backoff
   - Cache last successful response
   - Show user-friendly error messages

### For Bot Users

1. **Use "bot" prefix for user_id:**
   ```json
   {
     "user_id": "bot_accuracy_checker_001",
     "position": 12.0,
     ...
   }
   ```

2. **Provide accurate positions:**
   - Bot positions set bounds for other users
   - Regular users validated against your data

3. **Report regularly:**
   - Update every 1-2 minutes when tracking
   - Helps validate crowd-sourced data

### Rate Limiting

- Respect rate limits (10 req/s)
- Use batch endpoints where possible
- Cache responses when appropriate
- Implement exponential backoff on errors

---

## Examples

### JavaScript/Fetch
```javascript
// Get train positions
async function getTrainPositions(trainIds) {
  const response = await fetch(
    `https://train.sportsprime.live/current/${trainIds.join(',')}`
  );
  return response.json();
}

// Submit position update
async function submitPosition(trainId, position) {
  const response = await fetch(
    'https://train.sportsprime.live/sendupdate',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        train_id: trainId,
        user_id: 'mobile_user_123',
        position: position,
        time: Math.floor(Date.now() / 1000)
      })
    }
  );
  return response.json();
}
```

### Python
```python
import requests

# Get train positions
def get_positions(train_ids):
    url = f"https://train.sportsprime.live/current/{','.join(train_ids)}"
    response = requests.get(url)
    return response.json()

# Submit position update
def submit_position(train_id, position):
    url = "https://train.sportsprime.live/sendupdate"
    data = {
        "train_id": train_id,
        "user_id": "bot_tracker_001",
        "position": position,
        "time": int(time.time())
    }
    response = requests.post(url, json=data)
    return response.json()
```

### cURL
```bash
# Get train positions
curl https://train.sportsprime.live/current/101,102

# Submit position update
curl -X POST https://train.sportsprime.live/sendupdate \
  -H "Content-Type: application/json" \
  -d '{
    "train_id": "101",
    "user_id": "user123",
    "position": 12.5,
    "time": 1704150000
  }'
```

---

## Interactive Documentation

Visit `/docs` for interactive Swagger UI documentation:
```
https://train.sportsprime.live/docs
```

Alternative ReDoc documentation:
```
https://train.sportsprime.live/redoc
```

---

## Support

- **GitHub:** https://github.com/jisangain/find-my-br-train
- **Issues:** Open a GitHub issue for bugs/features
- **Android App:** https://play.google.com/store/apps/details?id=com.mytraintrackerbd.app

---

## Changelog

### Version 1.0.0 (Current)
- Initial API release
- Redis-based position tracking
- Bot user bounds validation
- Scheduled position calculation
- Two-train route precalculation
- Issue reporting system
- GitHub webhook integration
