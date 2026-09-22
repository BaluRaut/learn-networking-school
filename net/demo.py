"""The school's post room — networking, with nothing but the standard library. (Lessons 01–12)

Every lesson's idea is a few readable lines here, and each section runs on its own:

    python3 net/demo.py            # all sections
    python3 net/demo.py tcp        # one section: tcp · udp · ports · dns · http · tls · route

Sections that need the internet (dns, http, tls, route) say so and skip politely when offline.
"""
import json, os, random, socket, ssl, struct, sys, threading, time

def say(t): print(f"\n── {t}")

# ── 1 · TCP: the registered post — a handshake, receipts, order guaranteed (lesson 05) ──────
def tcp():
    say("TCP — the registered post: connect (handshake), then bytes arrive complete and in order")
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM); srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 0)); srv.listen(1); port = srv.getsockname()[1]
    def clerk():
        conn, addr = srv.accept()                              # the handshake happened inside accept()/connect()
        with conn:
            got = b""
            while not got.endswith(b"\n"): got += conn.recv(64)  # bytes may arrive in pieces — the STREAM has no message boundaries
            conn.sendall(f"receipt: {len(got)-1} bytes from {addr[0]}:{addr[1]}\n".encode())
    threading.Thread(target=clerk, daemon=True).start()
    c = socket.create_connection(("127.0.0.1", port))          # SYN → SYN-ACK → ACK, then we have a pipe
    print(f"   my socket {c.getsockname()} ↔ the clerk's socket {c.getpeername()}   (ip:port on both ends = one connection)")
    for piece in (b"Dear counter, ", b"please enrol Zoya", b"\n"): c.sendall(piece); time.sleep(0.05)
    print("   sent 3 pieces; the clerk answered:", c.recv(100).decode().strip())
    c.close(); srv.close()
    print("   the shape: a connection first, then a reliable ordered byte stream — you add the message boundaries (newline, length, HTTP)")

# ── 2 · UDP: the loudspeaker — no connection, no receipt, packets may vanish (lesson 05) ─────
def udp():
    say("UDP — the loudspeaker: no connection, one datagram at a time, and some never arrive")
    r = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); r.bind(("127.0.0.1", 0)); r.settimeout(0.3); port = r.getsockname()[1]
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    random.seed(7); sent = 0
    for i in range(10):
        if random.random() < 0.3: continue                     # a lossy corridor: 30% of the shouts are lost
        s.sendto(f"announcement {i}".encode(), ("127.0.0.1", port)); sent += 1
    got = []
    try:
        while True: got.append(r.recvfrom(64)[0].decode())
    except socket.timeout: pass
    print(f"   10 announcements made, {sent} reached the corridor, {len(got)} heard: {got}")
    print("   the shape: cheap and fast, no ordering, no retransmit — DNS, video, games; anything else wants TCP")
    s.close(); r.close()

# ── 3 · ports: room numbers — who is listening where (lesson 03) ──────────────────────────
def ports():
    say("Ports — room numbers: a quick knock on the usual doors of this machine")
    known = {22: "ssh", 80: "http", 443: "https", 5432: "postgres", 6379: "redis", 8080: "the API school's counter", 8082: "the auth demo"}
    for p, name in known.items():
        s = socket.socket(); s.settimeout(0.2)
        state = "open  ← someone is listening" if s.connect_ex(("127.0.0.1", p)) == 0 else "closed"
        s.close(); print(f"   127.0.0.1:{p:<5} {name:<28} {state}")
    print("   the shape: an address says WHICH computer, a port says WHICH program; 0–1023 are the well-known rooms")

# ── 4 · DNS: the school directory — a question in 12 bytes, an answer in an IP (lesson 06) ──
def dns(name="example.com"):
    say(f"DNS — the directory: ask 8.8.8.8 'what is the address of {name}?' — one UDP packet each way")
    tid = random.randint(0, 65535)
    q = struct.pack(">HHHHHH", tid, 0x0100, 1, 0, 0, 0)         # id · flags (recursion desired) · 1 question
    for label in name.split("."): q += bytes([len(label)]) + label.encode()
    q += b"\x00" + struct.pack(">HH", 1, 1)                     # type A, class IN
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.settimeout(2)
    try:
        s.sendto(q, ("8.8.8.8", 53)); data, _ = s.recvfrom(512)
    except OSError as e:
        print(f"   (offline or blocked: {e}) — skipping"); return
    finally: s.close()
    rid, flags, qd, an, ns, ar = struct.unpack(">HHHHHH", data[:12])
    print(f"   sent {len(q)} bytes · got {len(data)} bytes · id matches: {rid == tid} · answers: {an} · flags 0x{flags:04x}")
    i = 12
    while data[i] != 0: i += data[i] + 1                        # skip the echoed question name
    i += 5
    for _ in range(an):
        if data[i] & 0xC0 == 0xC0: i += 2                       # a compressed name pointer
        else:
            while data[i] != 0: i += data[i] + 1
            i += 1
        rtype, rclass, ttl, rdlen = struct.unpack(">HHIH", data[i:i+10]); i += 10
        rdata = data[i:i+rdlen]; i += rdlen
        if rtype == 1: print(f"   A record → {'.'.join(map(str, rdata))}   ttl {ttl}s  (the directory says: cache me this long)")
    print("   the shape: a name → an IP, cached by TTL, asked over UDP port 53; 'is it DNS?' is the first question of every outage")

# ── 5 · HTTP by hand: the API school's slip, written straight onto the socket (lesson 07) ───
def http(host="example.com"):
    say(f"HTTP — the slip in the envelope: a GET to {host}, typed by hand on port 80")
    try:
        c = socket.create_connection((host, 80), timeout=4)
    except OSError as e:
        print(f"   (offline: {e}) — skipping"); return
    c.sendall(f"GET / HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n".encode())
    raw = b""
    while True:
        chunk = c.recv(4096)
        if not chunk: break
        raw += chunk
    c.close()
    head, _, body = raw.partition(b"\r\n\r\n")
    lines = head.decode(errors="replace").split("\r\n")
    print("   →", "GET / HTTP/1.1 · Host: " + host)
    print("   ←", lines[0], "·", "; ".join(l for l in lines[1:] if l.lower().startswith(("content-type", "content-length", "cache-control")))[:110])
    print(f"   ← body: {len(body)} bytes   (HTTP is just text over a TCP stream; the API school lives one layer up)")

# ── 6 · TLS: the sealed envelope — who am I talking to, and can anyone read it? (lesson 08) ──
def tls(host="example.com"):
    say(f"TLS — the sealed envelope: handshake with {host}:443 and read its certificate")
    ctx = ssl.create_default_context()
    try:
        with socket.create_connection((host, 443), timeout=4) as raw, ctx.wrap_socket(raw, server_hostname=host) as s:
            cert = s.getpeercert(); print(f"   protocol {s.version()} · cipher {s.cipher()[0]}")
            subj = dict(x[0] for x in cert["subject"]); iss = dict(x[0] for x in cert["issuer"])
            print(f"   certificate for: {subj.get('commonName')}   issued by: {iss.get('organizationName')}   valid until: {cert['notAfter']}")
            print(f"   also valid for: {[v for k, v in cert.get('subjectAltName', [])][:4]}")
    except (OSError, ssl.SSLError) as e:
        print(f"   (offline or blocked: {e}) — skipping"); return
    print("   the shape: the server proves its name with a certificate a CA signed; then the envelope is sealed — HTTPS, and every 'S'")

# ── 7 · the route: how many corridors to the internet (lesson 09) ─────────────────────────
def route():
    say("Route — which corridor? the address this machine would use to reach the internet, and its default gateway")
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80)); print(f"   my outward-facing address: {s.getsockname()[0]}   (a private address → NAT at the gate turns it into the school's one public address)")
    except OSError as e: print(f"   (offline: {e})")
    finally: s.close()
    print("   run `traceroute 8.8.8.8` (or `tracert`) to see every corridor: your router → your ISP → an exchange → Google; each hop is a router forwarding by prefix")

SECTIONS = {"tcp": tcp, "udp": udp, "ports": ports, "dns": dns, "http": http, "tls": tls, "route": route}
if __name__ == "__main__":
    want = sys.argv[1:] or list(SECTIONS)
    for w in want: SECTIONS[w]()
    print("\n✅ the post room: addresses and rooms (IP:port) · registered post vs loudspeaker (TCP/UDP) · the directory (DNS) · the slip (HTTP) · the seal (TLS) · the corridors (routes)")
