import capstone

with open(r'apk_extracted\lib\x86_64\libumairi-lib.so', 'rb') as f:
    data = f.read()

md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)

for addr in [0x65670, 0x69ce0]:
    print(f"\nDisassembly at 0x{addr:x}:")
    chunk = data[addr:addr+256]
    for ins in md.disasm(chunk, addr):
        print(f"  0x{ins.address:x}: {ins.mnemonic}\t{ins.op_str}")
