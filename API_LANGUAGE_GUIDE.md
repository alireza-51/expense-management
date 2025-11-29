# API Language Support Guide

This guide explains how to use language parameters in the Expense Management API.

## Supported Languages

- **English (en)** - Default language
- **Persian/Farsi (fa)** - فارسی

## How to Send Language Parameter

You can specify the language for API responses in three ways:

### 1. Query Parameter (Recommended for API calls)

Add `lang` or `language` as a query parameter to your API request:

```bash
# English
GET /api/v1/dashboard/overview/?lang=en&calendar=gregorian&month=2024-10

# Persian
GET /api/v1/dashboard/overview/?lang=fa&calendar=jalali&month=1403-07
```

### 2. Accept-Language Header (Standard HTTP method)

Send the language preference via the `Accept-Language` HTTP header:

```bash
# English
curl -H "Accept-Language: en" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     https://api.example.com/api/v1/dashboard/overview/

# Persian
curl -H "Accept-Language: fa" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     https://api.example.com/api/v1/dashboard/overview/

# Persian with locale (also works)
curl -H "Accept-Language: fa-IR,fa;q=0.9" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     https://api.example.com/api/v1/dashboard/overview/
```

### 3. Session (For web applications)

If you're using the web interface, the language is stored in the session and will be used automatically.

## Language Priority

The API checks for language in the following order:

1. **Query parameter** (`lang` or `language`) - Highest priority for API requests
2. **Accept-Language header** - Standard HTTP method
3. **Session** - For web applications

## Example API Calls

### JavaScript/Fetch

```javascript
// English
const response = await fetch('/api/v1/dashboard/overview/?lang=en', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});

// Persian
const response = await fetch('/api/v1/dashboard/overview/?lang=fa', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});
```

### Python/Requests

```python
import requests

# English
response = requests.get(
    'https://api.example.com/api/v1/dashboard/overview/',
    params={'lang': 'en', 'calendar': 'gregorian'},
    headers={'Authorization': f'Bearer {token}'}
)

# Persian
response = requests.get(
    'https://api.example.com/api/v1/dashboard/overview/',
    params={'lang': 'fa', 'calendar': 'jalali'},
    headers={'Authorization': f'Bearer {token}'}
)
```

### cURL

```bash
# English
curl -X GET "https://api.example.com/api/v1/dashboard/overview/?lang=en" \
     -H "Authorization: Bearer YOUR_TOKEN"

# Persian
curl -X GET "https://api.example.com/api/v1/dashboard/overview/?lang=fa" \
     -H "Authorization: Bearer YOUR_TOKEN"
```

## Translated Content

The following content is automatically translated based on the language parameter:

- Error messages
- Recommendation titles and messages
- Day names (Monday, Tuesday, etc.)
- Financial insights and summaries
- Category trend messages
- Savings rate messages
- Month-over-month comparison messages

## Default Language

If no language parameter is provided, the API defaults to **English (en)**.

## Notes

- Language parameter works with all calendar types (Jalali and Gregorian)
- Language affects text content only, not numeric data or dates
- Invalid language codes will default to English
- Language is case-insensitive (`en`, `EN`, `En` all work)

