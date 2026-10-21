with open(r'apk_extracted\lib\x86_64\libumairi-lib.so', 'rb') as f:
    data = f.read()

import capstone
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)

chunk = data[0x69dd0:0x69dd0+512]
for ins in md.disasm(chunk, 0x69dd0):
    print(f"  0x{ins.address:x}: {ins.mnemonic}\t{ins.op_str}")
