#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Probe live N.E.K.O config endpoints: providers, core api, page config."""
import json
import urllib.request
import urllib.error

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
MBASE = "http://127.0.0.1:48911"


def get(path):
    try:
        req = urllib.request.Request(MBASE + path, method="GET")
        with OPENER.open(req, timeout=20) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return None, ("%s: %s" % (type(e).__name__, e)).encode()


def show(path, limit=3000):
    st, b = get(path)
    print("=" * 70)
    print("%s -> %s" % (path, st))
    try:
        txt = b.decode("utf-8", "replace")
    except Exception:
        txt = str(b)
    print(txt[:limit])


for p in ("/api/config/api_providers", "/api/config/core_api",
          "/api/config/page_config", "/api/config/conversation-settings",
          "/api/config/preferences"):
    show(p)
