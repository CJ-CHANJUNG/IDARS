import itertools
arr = [1455513552, 307959794, 940722710, 644608661, 269881457, 189487456, 1810892266, 1781029786, 1378039074, 1777286554, 666995355, 336871409, 259447296, 690062917, 260452832, 1044013724, 1716815137, 289965901, 224634009, 350529316, 298978604, 305770955, 271407113]
target = 12311720258
found = False
for r in range(1, len(arr) + 1):
    for subset in itertools.combinations(arr, r):
        if sum(subset) == target:
            print(f"Target: {target}")
            print(f"Sum: {sum(subset)}")
            print(f"Subset: {subset}")
            found = True
            break
    if found: break
if not found:
    print("No subset found")
