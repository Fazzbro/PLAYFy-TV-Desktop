from elftools.elf.elffile import ELFFile
import capstone

with open(r'apk_extracted\lib\x86_64\libnative-lib.so', 'rb') as f:
    elf = ELFFile(f)
    for sec in elf.iter_sections():
        if sec['sh_addr'] <= 0x6b4c0 < sec['sh_addr'] + sec['sh_size']:
            sec_addr = sec['sh_addr']
            sec_data = sec.data()
            print(f"Section {sec.name}: addr 0x{sec_addr:x}, size {sec['sh_size']}")
            off = 0x6b4c0 - sec_addr
            chunk = sec_data[off:off+2048]
            md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
            for ins in md.disasm(chunk, 0x6b4c0):
                if any(k in ins.mnemonic for k in ['call', 'lea', 'xor']):
                    print(f"  0x{ins.address:x}: {ins.mnemonic}\t{ins.op_str}")
