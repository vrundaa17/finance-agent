import requests
BASE_URL = "http://localhost:8000"

def api_get(path):
    try:
        r = requests.get(BASE_URL + path, timeout=10)
        r.raise_for_status()
        return r.json(), None
    except Exception as e:
        return None, str(e)

def api_post(path, body=None, params=None):
    try:
        r = requests.post(BASE_URL + path, json=body, params=params, timeout=120)
        r.raise_for_status()
        return r.json(), None
    except Exception as e:
        return None, str(e)

def api_delete(path):
    try:
        r = requests.delete(BASE_URL + path, timeout=10)
        r.raise_for_status()
        return r.json(), None
    except Exception as e:
        return None, str(e)

def format_large(n):
    if not n: return "—"
    if n >= 1e12:return f"{n/1e12:.1f}T"
    if n >= 1e9:return f"{n/1e9:.1f}B"
    if n >= 1e6:return f"{n/1e6:.1f}M"
    return f"{n:,.0f}"