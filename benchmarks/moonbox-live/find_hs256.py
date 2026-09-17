import os, re, math, base64

with open("/usr/local/bin/portal", "rb") as f:
    data = f.read()

def entropy(bytes_data):
    if not bytes_data: return 0
    e = 0.0
    for x in range(256):
        p_x = float(bytes_data.count(x)) / len(bytes_data)
        if p_x > 0:
            e += -p_x * math.log(p_x, 2)
    return e

# Search for 32-byte sequences with high entropy
# HS256 key = 32 bytes
candidates = []
for i in range(0, min(len(data)-32, 50000000), 50):
    seq = data[i:i+32]
    e = entropy(seq)
    if e > 4.0 and len(set(seq)) > 15:
        # Check if mostly printable
        printable = sum(1 for b in seq if 32 <= b <= 126)
        if printable >= 28:
            s = seq.decode("ascii", errors="replace")
            if not any(x in s.lower() for x in ["http", "www", ".com", "func", "type", "package"]):
                candidates.append((i, e, s, seq.hex()))

candidates.sort(key=lambda x: x[1], reverse=True)

with open("/mnt/agents/output/hs256_candidates.txt", "w") as f:
    f.write(f"Found {len(candidates)} 32-byte candidates\n\n")
    for offset, e, s, hex_s in candidates[:100]:
        f.write(f"0x{offset:08x} e={e:.2f} ascii={s} hex={hex_s}\n")

print(f"Found {len(candidates)} candidates, saved top 100")
