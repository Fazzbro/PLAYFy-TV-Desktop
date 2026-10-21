import capstone

with open(r'apk_extracted\lib\x86_64\libnative-lib.so', 'rb') as f:
    data = f.read()

md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)

# Look at 0x6b5c0 to 0x6b900
chunk = data[0x6b5c0:0x6b5c0+1024]
for ins in md.disasm(chunk, 0x6b5c0):
    if ins.mnemonic in ['call', 'lea', 'xor', 'movabs']:
        print(f"  0x{ins.address:x}: {ins.mnemonic}\t{ins.op_str}")
