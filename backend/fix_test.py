"""Patch test_recovery.py to fix test_shortest_hop_selection."""
path = r"tests\test_recovery.py"
with open(path, encoding="utf-8") as f:
    content = f.read()

# Find marker lines and replace them
old_block = (
    "    lAX = lnk(nA, nX)\n"
    "    lXD = lnk(nX, nD)   # will be failed \u2192 forces recovery\n"
    "    lAE = lnk(nA, nE)\n"
    "    lED = lnk(nE, nD)   # 2-hop path A-E-D\n"
    "    lAB = lnk(nA, nB)\n"
    "    lBC = lnk(nB, nC)\n"
    "    lCD = lnk(nC, nD)   # 3-hop path A-B-C-D\n"
    "\n"
    "    sim = run_sim(client, network_id, nA, nD)\n"
    "    sim_id = sim[\"simulation_id\"]\n"
    "    assert sim[\"status\"] == \"completed\"\n"
    "\n"
    "    # Fail the link on the original route so recovery is triggered\n"
)

new_block = (
    "    # Give A-X-D very low latency so the traffic sim deterministically picks it\n"
    "    lAX = lnk(nA, nX, lat=1)\n"
    "    lXD = lnk(nX, nD, lat=1)   # will be failed \u2192 forces recovery\n"
    "    lAE = lnk(nA, nE, lat=10)\n"
    "    lED = lnk(nE, nD, lat=10)  # 2-hop path A-E-D\n"
    "    lAB = lnk(nA, nB, lat=10)\n"
    "    lBC = lnk(nB, nC, lat=10)\n"
    "    lCD = lnk(nC, nD, lat=10)  # 3-hop path A-B-C-D\n"
    "\n"
    "    sim = run_sim(client, network_id, nA, nD)\n"
    "    sim_id = sim[\"simulation_id\"]\n"
    "    assert sim[\"status\"] == \"completed\"\n"
    "    # Ensure original route uses X (lowest latency forces A-X-D)\n"
    "    assert nX in sim[\"route\"], f\"Expected original route to use X; got {sim['route']}\"\n"
    "\n"
    "    # Fail the link on the original route so recovery is triggered\n"
)

if old_block in content:
    content = content.replace(old_block, new_block, 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("SUCCESS: fixed test_shortest_hop_selection")
else:
    print("ERROR: old block not found in file. Dumping snippet around 'lAX':")
    idx = content.find("lAX = lnk")
    if idx >= 0:
        print(repr(content[idx - 5 : idx + 400]))
    else:
        print("'lAX = lnk' not found at all")
