import requests
BASE_URL = "http://localhost:8000"
import logging
logger = logging.getLogger(__name__)

def _extract_error(e,r=None):
    if r is not None:
        try:
            detail = r.json().get("detail")
            if detail:
                return detail
        except Exception:
            pass
    return str(e)

def api_get(path):
    
    try:
        r = requests.get(BASE_URL + path, timeout=10)
        r.raise_for_status()
        return r.json(), None
    except requests.HTTPError as e:
        msg = _extract_error(e,r)
        logger.error(f"api_get Error {msg}")
        return None,msg
    except Exception as e:
        logger.error(f"api_get Error {str(e)}")
        return None, str(e)

def api_post(path, body=None, params=None):
    try:
        r = requests.post(BASE_URL + path, json=body, params=params, timeout=120)
        r.raise_for_status()
        return r.json(), None
    
    except requests.HTTPError as e:
        msg = _extract_error(e,r)
        logger.error(f"api_get Error {msg}")
        return None,msg
    
    except Exception as e:
        logger.error(f"api_post Error {str(e)}")
        return None, str(e)

def api_delete(path):
    try:
        r = requests.delete(BASE_URL + path, timeout=10)
        r.raise_for_status()
        return r.json(), None
    
    except requests.HTTPError as e:
        msg = _extract_error(e,r)
        logger.error(f"api_get Error {msg}")
        return None,msg
    
    except Exception as e:
        logger.error(f"api_delete Error {str(e)}")
        return None, str(e)

def format_large(n):
    if not n: return "—"
    if n >= 1e12:return f"{n/1e12:.1f}T"
    if n >= 1e9:return f"{n/1e9:.1f}B"
    if n >= 1e6:return f"{n/1e6:.1f}M"
    return f"{n:,.0f}"