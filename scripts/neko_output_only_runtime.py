"""Source-host HTML bootstrap for output-only tests; no capture or output initialization."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path

POLICY_HEADERS = {
    'Permissions-Policy': 'microphone=(), camera=(), display-capture=()',
    'X-LiveTutor-Audio-Mode': 'output-only',
}


def protected_html(html: str, library: str) -> str:
    if '</script' in library.lower():
        raise ValueError('capture policy script must not close its HTML container')
    payload = json.dumps(html, ensure_ascii=True).replace('<', '\\u003c').replace('>', '\\u003e')
    # The original app only exists as inert string data until the installer succeeds.
    # Throwing from a separate script before normal app tags would not stop those tags.
    return '''<!doctype html><html><head><meta charset="utf-8"><title>N.E.K.O output-only</title>
<script>''' + library + '''</script><script>
try {
    const receipt = globalThis.NekoCapturePolicy.installOutputOnly({enabled:true});
    if (receipt.status !== 'installed' || receipt.captureBlocked !== true ||
        globalThis.NekoCapturePolicy.getResult() !== receipt ||
        globalThis.__NEKO_OUTPUT_ONLY_CAPTURE_BLOCKED__ !== true) throw new Error('Capture policy unavailable');
    document.open(); document.write(''' + payload + '''); document.close();
    document.documentElement.dataset.nekoCapturePolicy = 'output-only-installed';
} catch (error) {
    document.title = 'N.E.K.O capture protection refused';
    const node = document.createElement('p');
    node.id = 'neko-output-only-refused';
    node.textContent = 'Microphone protection could not be installed. Application startup was refused.';
    const body = document.body || document.createElement('body');
    if (!document.body) document.documentElement.appendChild(body);
    body.appendChild(node);
    document.documentElement.dataset.nekoCapturePolicy = 'failed';
}
</script></head><body></body></html>'''


def install_output_only(app):
    if os.environ.get('NEKO_OUTPUT_ONLY') != '1':
        return
    from starlette.responses import Response
    asset = Path(__file__).resolve().parents[1] / 'static/app/neko-capture-policy.js'
    blob = asset.read_bytes()
    library = blob.decode('utf-8')
    fingerprint = hashlib.sha256(blob).hexdigest()

    @app.middleware('http')
    async def capture_bootstrap(request, call_next):
        response = await call_next(request)
        for key, value in POLICY_HEADERS.items():
            response.headers[key] = value
        if 'text/html' not in response.headers.get('content-type', '').lower():
            return response
        headers = dict(response.headers)
        headers.pop('content-length', None)
        headers['X-LiveTutor-Capture-Policy-SHA256'] = fingerprint
        headers['Cache-Control'] = 'no-store'
        body = bytearray()
        try:
            if response.headers.get('content-encoding', 'identity') != 'identity':
                raise ValueError('encoded HTML is not a verified bootstrap')
            async for chunk in response.body_iterator:
                body.extend(chunk)
                if len(body) > 2_000_000:
                    raise ValueError('HTML exceeds output-only bootstrap bound')
            html = protected_html(body.decode('utf-8'), library)
        except Exception:
            closer = getattr(response.body_iterator, 'aclose', None)
            if callable(closer):
                await closer()
            return Response('Output-only page protection failed; application was not loaded.',
                            status_code=503, media_type='text/plain', headers=POLICY_HEADERS)
        return Response(html, status_code=response.status_code, headers=headers,
                        background=response.background)
