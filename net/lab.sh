#!/usr/bin/env bash
# The networking toolbox, one command per question. (Lesson 12 — debugging)   usage: bash net/lab.sh [host]
H=${1:-example.com}
say(){ printf '\n── %s\n' "$*"; }
say "Is it DNS?           dig +short $H"            ; dig +short "$H" 2>/dev/null || nslookup "$H" 2>/dev/null | tail -2
say "Can I reach it?      ping -c 2 $H"             ; ping -c 2 "$H" 2>&1 | tail -2
say "Which corridors?     traceroute -m 8 $H"       ; (traceroute -m 8 -w 1 "$H" 2>/dev/null || tracepath -m 8 "$H" 2>/dev/null) | tail -6
say "Is the door open?    nc -zv $H 443"            ; nc -zv -w 3 "$H" 443 2>&1 | tail -1
say "Is it TLS?           openssl s_client"         ; echo | openssl s_client -connect "$H:443" -servername "$H" 2>/dev/null | grep -E 'subject=|issuer=|Verification' | head -3
say "Is it HTTP?          curl -sv https://$H"      ; curl -sv "https://$H" -o /dev/null 2>&1 | grep -E '^(< HTTP|> GET|< content-type|\* Connected)' | head -4
say "Who is listening?    ss -ltn / lsof -iTCP"     ; (ss -ltn 2>/dev/null || lsof -nP -iTCP -sTCP:LISTEN 2>/dev/null) | head -6
say "What is on the wire? tcpdump (needs sudo)"     ; echo "   sudo tcpdump -ni any 'port 53' -c 5     # watch the directory questions go by"
echo; echo "🧭 triage order: DNS → reach (ping) → route (traceroute) → port (nc) → TLS (openssl) → HTTP (curl -v) → the app's own logs"
