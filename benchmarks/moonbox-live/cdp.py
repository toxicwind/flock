#!/usr/bin/env python3
import asyncio, json, sys, websockets, argparse, urllib.request, base64

CDP = 'http://127.0.0.1:9222'

async def ws_send(ws, method, params=None, msg_id=None):
    payload = {'id': msg_id or 1, 'method': method, 'params': params or {}}
    await ws.send(json.dumps(payload))
    return json.loads(await ws.recv())

async def main():
    p = argparse.ArgumentParser(description='CDP argv forwarder')
    p.add_argument('--target', '-t', default=None)
    p.add_argument('--navigate', '-n', default=None)
    p.add_argument('--eval', '-e', default=None)
    p.add_argument('--screenshot', '-s', action='store_true')
    p.add_argument('--wait', '-w', type=float, default=2)
    p.add_argument('--dump-dom', '-d', action='store_true')
    p.add_argument('--list', '-l', action='store_true')
    p.add_argument('--close', action='store_true')
    p.add_argument('--ua', default=None)
    args = p.parse_args()

    if args.list:
        with urllib.request.urlopen(f'{CDP}/json') as r:
            for t in json.loads(r.read()):
                if t.get('type') == 'page':
                    print(f"{t['id']} | {t.get('title','')[:70]} | {t.get('url','')[:90]}")
        return

    target_id = args.target
    if not target_id:
        with urllib.request.urlopen(f'{CDP}/json') as r:
            pages = [x for x in json.loads(r.read()) if x.get('type')=='page']
            if not pages: print('No page targets'); return
            target_id = pages[0]['id']

    ws_url = f'ws://127.0.0.1:9222/devtools/page/{target_id}'
    async with websockets.connect(ws_url) as ws:
        for domain in ['Page','Runtime','DOM','Network']:
            await ws_send(ws, f'{domain}.enable')
        if args.ua:
            await ws_send(ws, 'Network.setUserAgentOverride', {'userAgent': args.ua})
        if args.navigate:
            await ws_send(ws, 'Page.navigate', {'url': args.navigate})
            await asyncio.sleep(args.wait)
        if args.eval:
            res = await ws_send(ws, 'Runtime.evaluate', {'expression': args.eval, 'returnByValue': True})
            print(res.get('result',{}).get('result',{}).get('value',''))
        if args.dump_dom:
            res = await ws_send(ws, 'Runtime.evaluate', {'expression': 'document.body.innerText', 'returnByValue': True})
            val = res.get('result',{}).get('result',{}).get('value','')
            print(val)
        if args.screenshot:
            res = await ws_send(ws, 'Page.captureScreenshot', {'format': 'png'})
            data = res.get('result',{}).get('data','')
            if data:
                open('/mnt/agents/output/screenshot.png','wb').write(base64.b64decode(data))
                print('Saved screenshot.png')
            else:
                print('Screenshot failed:', res)
        if args.close:
            await ws_send(ws, 'Target.closeTarget', {'targetId': target_id})

if __name__ == '__main__':
    asyncio.run(main())
