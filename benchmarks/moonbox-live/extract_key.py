import os, re, math

with open("/usr/local/bin/portal", "rb") as f:
    data = f.read()

result = []

def entropy(bytes_data):
    if not bytes_data: return 0
    e = 0.0
    for x in range(256):
        p_x = float(bytes_data.count(x)) / len(bytes_data)
        if p_x > 0:
            e += -p_x * math.log(p_x, 2)
    return e

# Approach 1: Raw 64-byte sequences with entropy > 4.5
result.append("=== RAW 64-BYTE SEQUENCES ===")
candidates = []
for i in range(0, min(len(data)-64, 10000000), 100):
    seq = data[i:i+64]
    e = entropy(seq)
    if e > 4.5 and len(set(seq)) > 20:
        hex_repr = seq.hex()[:80]
        ascii_repr = seq.decode("ascii", errors="replace")[:40]
        candidates.append((i, e, hex_repr, ascii_repr))

candidates.sort(key=lambda x: x[1], reverse=True)
result.append(f"Found {len(candidates)} candidates")
for offset, e, hex_r, ascii_r in candidates[:30]:
    result.append(f"0x{offset:08x} e={e:.2f} hex={hex_r} ascii={ascii_r}")

# Approach 2: Go string prefix 0x40 + 64 bytes
result.append("\n=== GO STRING PREFIX 0x40 ===")
candidates2 = []
for i in range(min(len(data) - 65, 10000000)):
    if data[i] == 0x40:
        seq = data[i+1:i+65]
        e = entropy(seq)
        if e > 4.0 and len(set(seq)) > 20:
            hex_repr = seq.hex()[:80]
            ascii_repr = seq.decode("ascii", errors="replace")[:40]
            candidates2.append((i, e, hex_repr, ascii_repr))

result.append(f"Found {len(candidates2)} candidates")
for offset, e, hex_r, ascii_r in candidates2[:30]:
    result.append(f"0x{offset:08x} e={e:.2f} hex={hex_r} ascii={ascii_r}")

# Approach 3: Search near JWT-related strings
result.append("\n=== CONTEXT SEARCH ===")
jwt_offsets = []
for m in re.finditer(b"jwt|JWT|hmac|HMAC|sign|SIGN|token|TOKEN", data):
    jwt_offsets.append(m.start())

result.append(f"Found {len(jwt_offsets)} crypto-related offsets")
for offset in jwt_offsets[:20]:
    context = data[max(0,offset-100):offset+200]
    # Look for 64-byte high-entropy sequences in context
    for j in range(len(context) - 64):
        seq = context[j:j+64]
        e = entropy(seq)
        if e > 4.5 and len(set(seq)) > 20:
            hex_repr = seq.hex()[:80]
            result.append(f"Near 0x{offset:08x} (+{j}): {hex_repr}")

with open("/mnt/agents/output/hs512_candidates_v2.txt", "w") as f:
    f.write("\n".join(result))
print("DONE")
